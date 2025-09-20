import pandas as pd
import requests
import time
import json
from typing import Dict, List, Optional
from .basketball_reference import BasketballReferenceCollector

class NBADataCollector:
    def __init__(self):
        self.season = '2024-25'
        self.current_season_id = '22024'  # 2024-25 season ID (corrected)
        
    def get_all_active_players(self) -> pd.DataFrame:
        """2024-25 시즌 활성 선수 목록을 가져옵니다."""
        try:
            print("NBA API에서 선수 목록을 가져오는 중...")
            
            # 먼저 현재 시즌으로 시도
            all_players = commonallplayers.CommonAllPlayers(
                season=self.season,
                is_only_current_season=1,
                timeout=30
            )
            
            df = all_players.get_data_frames()[0]
            
            if df.empty:
                print("현재 시즌 데이터가 비어있음. 모든 시즌 데이터로 시도...")
                # 현재 시즌이 비어있으면 모든 시즌 데이터 가져오기
                all_players = commonallplayers.CommonAllPlayers(
                    season=self.season,
                    is_only_current_season=0,
                    timeout=30
                )
                df = all_players.get_data_frames()[0]
            
            if df.empty:
                raise Exception("NBA API에서 선수 데이터를 가져올 수 없습니다.")
            
            print(f"API에서 {len(df)}명의 선수 데이터 수신")
            
            # 필요한 컬럼만 선택
            required_cols = ['PERSON_ID', 'DISPLAY_FIRST_LAST', 'TEAM_ABBREVIATION', 
                           'TEAM_ID', 'ROSTERSTATUS', 'FROM_YEAR', 'TO_YEAR']
            
            # 컬럼이 존재하는지 확인
            available_cols = [col for col in required_cols if col in df.columns]
            df = df[available_cols].copy()
            
            # 활성 선수만 필터링 (ROSTERSTATUS가 있는 경우)
            if 'ROSTERSTATUS' in df.columns:
                active_df = df[df['ROSTERSTATUS'] == 1].copy()
                print(f"활성 선수 필터링 후: {len(active_df)}명")
            else:
                active_df = df.copy()
                print(f"ROSTERSTATUS 컬럼 없음. 모든 선수 사용: {len(active_df)}명")
            
            return active_df
            
        except Exception as e:
            print(f"선수 데이터 수집 중 오류 발생: {e}")
            print("대체 방법을 시도합니다...")
            
            # 대체 방법: nba_api.stats.static.players 사용
            try:
                from nba_api.stats.static import players as static_players
                all_players_list = static_players.get_players()
                
                # 활성 선수만 필터링 (is_active가 True인 선수)
                active_players_list = [p for p in all_players_list if p.get('is_active', True)]
                
                df_data = []
                for player in active_players_list:
                    df_data.append({
                        'PERSON_ID': player['id'],
                        'DISPLAY_FIRST_LAST': player['full_name'],
                        'TEAM_ABBREVIATION': 'UNK',  # static API에는 팀 정보가 없음
                        'TEAM_ID': 0,
                        'ROSTERSTATUS': 1,
                        'FROM_YEAR': '',
                        'TO_YEAR': ''
                    })
                
                df = pd.DataFrame(df_data)
                print(f"대체 방법으로 {len(df)}명의 선수 데이터 수집")
                return df
                
            except Exception as e2:
                print(f"대체 방법도 실패: {e2}")
                return pd.DataFrame()
    
    def get_player_stats(self, player_id: int) -> Optional[Dict]:
        """특정 선수의 2024-25 시즌 스탯을 가져옵니다."""
        try:
            # 선수 커리어 스탯 가져오기
            career_stats = playercareerstats.PlayerCareerStats(player_id=player_id)
            season_stats = career_stats.get_data_frames()[0]
            
            if season_stats.empty:
                return None
            
            # 2024-25 시즌 스탯 먼저 시도
            current_season = season_stats[season_stats['SEASON_ID'] == self.current_season_id]
            
            # 2024-25 시즌 데이터가 없으면 최신 시즌 사용
            if current_season.empty:
                # 가장 최근 시즌 데이터 사용
                current_season = season_stats.head(1)
                if current_season.empty:
                    return None
            
            stats = current_season.iloc[0]
            
            # 기본값 설정으로 안전성 확보
            gp = max(stats.get('GP', 0), 1)  # 0으로 나누기 방지
            
            return {
                'games_played': stats.get('GP', 0),
                'minutes_per_game': stats.get('MIN', 0) / gp,
                'points': stats.get('PTS', 0) / gp,
                'rebounds': stats.get('REB', 0) / gp,
                'assists': stats.get('AST', 0) / gp,
                'steals': stats.get('STL', 0) / gp,
                'blocks': stats.get('BLK', 0) / gp,
                'field_goal_pct': stats.get('FG_PCT', 0.0) or 0.0,
                'three_point_pct': stats.get('FG3_PCT', 0.0) or 0.0,
                'free_throw_pct': stats.get('FT_PCT', 0.0) or 0.0
            }
            
        except Exception as e:
            # 디버깅을 위해 더 자세한 오류 정보 출력하지 않음 (너무 많은 로그)
            return None
    
    def calculate_fantasy_value(self, stats: Dict) -> float:
        """스탯을 기반으로 판타지 가치를 계산합니다."""
        if not stats:
            return 0.0
            
        # 간단한 판타지 점수 계산 (표준 9-cat 리그 기준)
        fantasy_score = (
            stats['points'] * 1.0 +
            stats['rebounds'] * 1.2 +
            stats['assists'] * 1.5 +
            stats['steals'] * 3.0 +
            stats['blocks'] * 3.0 +
            (stats['field_goal_pct'] - 0.45) * 100 +  # FG% bonus/penalty
            (stats['three_point_pct'] - 0.35) * 50 +   # 3P% bonus/penalty
            (stats['free_throw_pct'] - 0.75) * 50      # FT% bonus/penalty
        )
        
        return max(fantasy_score, 0.0)
    
    def get_player_position(self, player_name: str) -> str:
        """선수의 포지션 정보를 가져옵니다."""
        # NBA API에서 포지션 정보를 직접 제공하지 않으므로
        # 임시로 일반적인 포지션을 반환 (실제로는 추가 API나 데이터베이스 필요)
        position_map = {
            'C': ['Nikola Jokic', 'Joel Embiid', 'Karl-Anthony Towns'],
            'PF': ['Giannis Antetokounmpo', 'Anthony Davis', 'Domantas Sabonis'],
            'SF': ['Jayson Tatum', 'Kawhi Leonard', 'Jimmy Butler'],
            'SG': ['Devin Booker', 'Donovan Mitchell', 'Bradley Beal'],
            'PG': ['Luka Doncic', 'Stephen Curry', 'Damian Lillard']
        }
        
        for position, players_list in position_map.items():
            if player_name in players_list:
                return position
        
        return 'SF'  # 기본값
    
    def create_players_dataset(self) -> pd.DataFrame:
        """Basketball Reference에서 2024-25 시즌 선수 데이터를 수집합니다."""
        
        print("=== Basketball Reference에서 NBA 선수 데이터 수집 시작 ===")
        
        try:
            # Basketball Reference 수집기 사용
            br_collector = BasketballReferenceCollector()
            df = br_collector.get_season_stats()
            
            if df.empty:
                raise Exception("Basketball Reference에서 데이터를 가져올 수 없습니다.")
            
            print(f"\n=== Basketball Reference 수집 완료 ===")
            print(f"총 선수: {len(df)}명")
            print(f"평균 게임 수: {df['games_played'].mean():.1f}")
            print(f"평균 출전 시간: {df['minutes_per_game'].mean():.1f}분")
            
            # 상위 10명 확인
            print(f"\n상위 10명 선수:")
            top10 = df.head(10)[['name', 'team', 'games_played', 'minutes_per_game', 'points', 'fantasy_value', 'fantasy_rank']]
            for _, player in top10.iterrows():
                print(f"{player['fantasy_rank']:2d}. {player['name']:<20} ({player['team']}) - "
                      f"{player['games_played']:2.0f}G, {player['minutes_per_game']:4.1f}min, "
                      f"{player['points']:4.1f}pts, FV:{player['fantasy_value']:5.1f}")
            
            return df
            
        except Exception as e:
            print(f"Basketball Reference 데이터 수집 중 오류: {e}")
            raise e
    
    
    def save_players_data(self, df: pd.DataFrame, filepath: str = "data/players.csv"):
        """선수 데이터를 CSV 파일로 저장합니다."""
        df.to_csv(filepath, index=False, encoding='utf-8')
        print(f"선수 데이터가 {filepath}에 저장되었습니다.")
    
    def load_players_data(self, filepath: str = "data/players.csv") -> pd.DataFrame:
        """저장된 선수 데이터를 불러옵니다."""
        try:
            return pd.read_csv(filepath, encoding='utf-8')
        except FileNotFoundError:
            print(f"{filepath} 파일을 찾을 수 없습니다.")
            return pd.DataFrame()