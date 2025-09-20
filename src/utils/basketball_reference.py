import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import re
from typing import Dict, List, Optional
try:
    from nba_api.stats.endpoints import commonteamroster
    from nba_api.stats.static import teams
    NBA_API_AVAILABLE = True
except ImportError:
    NBA_API_AVAILABLE = False

class BasketballReferenceCollector:
    def __init__(self):
        self.season_year = '2025'  # 2024-25 시즌
        self.fallback_season_year = '2024'  # 2023-24 시즌 (폴백)
        self.base_url = 'https://www.basketball-reference.com'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_season_stats(self) -> pd.DataFrame:
        """Basketball Reference에서 2024-25 시즌 선수 스탯을 가져옵니다."""
        print("Basketball Reference에서 최신 선수 데이터를 수집하는 중...")

        # 먼저 현재 시즌으로 시도
        df = self._fetch_season_data(self.season_year)

        # 현재 시즌 데이터가 없으면 이전 시즌으로 폴백
        if df.empty:
            print(f"2024-25 시즌 데이터를 사용할 수 없습니다. 2023-24 시즌 데이터로 폴백합니다.")
            df = self._fetch_season_data(self.fallback_season_year)

        if df.empty:
            raise Exception("Basketball Reference에서 데이터를 가져올 수 없습니다.")

        return df

    def _fetch_season_data(self, season_year: str) -> pd.DataFrame:
        """특정 시즌의 데이터를 가져옵니다."""
        try:
            # Per game stats 페이지
            url = f"{self.base_url}/leagues/NBA_{season_year}_per_game.html"
            print(f"시도 중인 URL: {url}")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # pandas로 테이블 읽기
            tables = pd.read_html(response.content, header=0)
            df = tables[0]  # 첫 번째 테이블이 선수 스탯

            # 컬럼 이름을 수동으로 설정 (Basketball Reference 표준 순서)
            expected_columns = [
                'Rank', 'Player', 'Age', 'Tm', 'Pos', 'G', 'GS', 'MP', 'FG', 'FGA', 'FG%',
                '3P', '3PA', '3P%', '2P', '2PA', '2P%', 'eFG%', 'FT', 'FTA', 'FT%',
                'ORB', 'DRB', 'TRB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PTS', 'Awards'
            ]

            # 실제 컬럼 수에 맞춰 조정
            if len(df.columns) >= len(expected_columns):
                df.columns = expected_columns + [f'Extra_{i}' for i in range(len(df.columns) - len(expected_columns))]
            else:
                df.columns = expected_columns[:len(df.columns)]

            print(f"{season_year} 시즌 원본 데이터: {len(df)}명의 선수")

            # 현재 시즌 트레이드 정보 업데이트
            df = self._update_current_teams(df)

            # 데이터 정리
            df = self._clean_data(df)
            print(f"{season_year} 시즌 정리된 데이터: {len(df)}명의 선수")

            return df

        except Exception as e:
            print(f"{season_year} 시즌 Basketball Reference 데이터 수집 오류: {e}")
            return pd.DataFrame()
    
    def _update_current_teams(self, df: pd.DataFrame) -> pd.DataFrame:
        """NBA API에서 실시간 로스터 정보를 가져와서 팀 정보를 업데이트"""
        print("실시간 NBA 로스터 정보로 팀 데이터 업데이트 중...")
        
        if not NBA_API_AVAILABLE:
            print("NBA API를 사용할 수 없습니다. Basketball Reference 원본 데이터를 사용합니다.")
            return df
        
        try:
            # 모든 NBA 팀 정보 가져오기
            nba_teams = teams.get_teams()
            current_rosters = {}
            
            print("NBA 팀별 현재 로스터 정보 수집 중...")
            for team in nba_teams:
                team_id = team['id']
                team_abbr = team['abbreviation']
                
                try:
                    # 현재 시즌 로스터 정보
                    roster = commonteamroster.CommonTeamRoster(
                        team_id=team_id, 
                        season='2024-25'
                    )
                    roster_df = roster.get_data_frames()[0]
                    
                    if not roster_df.empty:
                        for _, player in roster_df.iterrows():
                            player_name = player['PLAYER']
                            current_rosters[player_name] = team_abbr
                    
                    time.sleep(0.1)  # API 제한 준수
                    
                except Exception as e:
                    print(f"{team_abbr} 로스터 정보 가져오기 실패: {e}")
                    continue
            
            print(f"수집된 로스터 정보: {len(current_rosters)}명의 선수")
            
            # Basketball Reference 데이터와 NBA API 로스터 정보 비교 및 업데이트
            updates_count = 0
            for idx, row in df.iterrows():
                br_player_name = row['Player']
                br_team = row['Tm']
                
                # 이름 매칭 (다양한 형태로 시도)
                matched_team = self._find_player_current_team(br_player_name, current_rosters)
                
                if matched_team and matched_team != br_team:
                    df.loc[idx, 'Tm'] = matched_team
                    print(f"팀 업데이트: {br_player_name} {br_team} → {matched_team}")
                    updates_count += 1
            
            if updates_count > 0:
                print(f"총 {updates_count}명의 선수 팀 정보가 업데이트되었습니다.")
            else:
                print("업데이트할 팀 정보가 없습니다. Basketball Reference 데이터가 최신 상태입니다.")
            
            return df
            
        except Exception as e:
            print(f"NBA API 로스터 업데이트 실패: {e}")
            print("Basketball Reference 원본 데이터를 사용합니다.")
            return df
    
    def _find_player_current_team(self, br_name: str, rosters: Dict[str, str]) -> Optional[str]:
        """Basketball Reference 선수명과 NBA API 로스터를 매칭"""
        # 정확한 매칭
        if br_name in rosters:
            return rosters[br_name]
        
        # 부분 매칭 (성씨로)
        br_last_name = br_name.split()[-1] if ' ' in br_name else br_name
        for roster_name, team in rosters.items():
            if br_last_name in roster_name or roster_name in br_name:
                # 추가 검증: 이름이 비슷한지 확인
                if len(set(br_name.lower().split()) & set(roster_name.lower().split())) >= 1:
                    return team
        
        return None
    
    def _check_latest_rosters(self, df: pd.DataFrame):
        """ESPN이나 다른 소스에서 최신 로스터 확인 (간단한 구현)"""
        # 현재는 Basketball Reference가 가장 신뢰할 수 있는 소스이므로
        # 추가적인 외부 소스 확인은 선택적으로만 구현
        print("Basketball Reference 데이터가 가장 최신 상태입니다.")
    
    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """데이터를 정리하고 판타지 점수를 계산합니다."""
        try:
            # 필요한 컬럼만 선택하고 이름 변경
            required_columns = {
                'Player': 'name',
                'Tm': 'team',
                'Pos': 'position',
                'G': 'games_played',
                'MP': 'minutes_per_game',
                'PTS': 'points',
                'TRB': 'rebounds',
                'AST': 'assists',
                'STL': 'steals',
                'BLK': 'blocks',
                'FG%': 'field_goal_pct',
                '3P%': 'three_point_pct',
                'FT%': 'free_throw_pct'
            }
            
            # 필요한 컬럼이 있는지 확인
            available_columns = {}
            for old_col, new_col in required_columns.items():
                if old_col in df.columns:
                    available_columns[old_col] = new_col
                else:
                    print(f"경고: {old_col} 컬럼을 찾을 수 없음")
            
            # 사용 가능한 컬럼만 선택
            df_clean = df[list(available_columns.keys())].copy()
            df_clean = df_clean.rename(columns=available_columns)
            
            # 중복 제거 (TOT 제거 - 여러 팀을 거친 선수의 총합)
            df_clean = df_clean[df_clean['team'] != 'TOT']
            
            # 헤더 행 제거 (중간에 끼어있는 헤더)
            df_clean = df_clean[df_clean['name'] != 'Player']
            
            # 결측치 및 잘못된 데이터 처리
            numeric_columns = ['games_played', 'minutes_per_game', 'points', 'rebounds', 'assists', 'steals', 'blocks']
            percentage_columns = ['field_goal_pct', 'three_point_pct', 'free_throw_pct']
            
            # 숫자 컬럼 변환
            for col in numeric_columns:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
            
            # 퍼센티지 컬럼 변환
            for col in percentage_columns:
                if col in df_clean.columns:
                    df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
            
            # 최소 조건 필터링 (10게임 이상, 5분 이상)
            df_clean = df_clean[
                (df_clean['games_played'] >= 10) & 
                (df_clean['minutes_per_game'] >= 5.0)
            ].copy()
            
            # 판타지 점수 계산
            df_clean['fantasy_value'] = self._calculate_fantasy_score(df_clean)
            
            # 순위 매기기
            df_clean = df_clean.sort_values('fantasy_value', ascending=False).reset_index(drop=True)
            df_clean['fantasy_rank'] = df_clean.index + 1
            
            # player_id 생성 (이름 기반 해시)
            df_clean['player_id'] = df_clean['name'].apply(lambda x: hash(x) % 1000000)
            
            # 드래프트 관련 컬럼 추가
            df_clean['draft_status'] = 'available'
            df_clean['draft_price'] = 0
            df_clean['draft_team'] = ''
            
            return df_clean
            
        except Exception as e:
            print(f"데이터 정리 중 오류: {e}")
            return pd.DataFrame()
    
    def _calculate_fantasy_score(self, df: pd.DataFrame) -> pd.Series:
        """표준 9-카테고리 판타지 점수를 계산합니다."""
        # 기본 스탯 점수
        score = (
            df['points'] * 1.0 +
            df['rebounds'] * 1.2 +
            df['assists'] * 1.5 +
            df['steals'] * 3.0 +
            df['blocks'] * 3.0
        )
        
        # 퍼센티지 보너스/패널티 (리그 평균 기준)
        fg_avg = 0.465  # NBA 평균 FG%
        three_avg = 0.365  # NBA 평균 3P%
        ft_avg = 0.780  # NBA 평균 FT%
        
        # 퍼센티지 보너스 (충분한 시도가 있을 때만)
        score += (df['field_goal_pct'] - fg_avg) * 100 * (df['minutes_per_game'] / 30)
        score += (df['three_point_pct'] - three_avg) * 50 * (df['minutes_per_game'] / 30)
        score += (df['free_throw_pct'] - ft_avg) * 30 * (df['minutes_per_game'] / 30)
        
        return score.clip(lower=0)  # 음수 방지
    
    def get_team_abbreviations(self) -> Dict[str, str]:
        """팀 약자 매핑을 반환합니다."""
        return {
            'ATL': 'Atlanta Hawks', 'BOS': 'Boston Celtics', 'BRK': 'Brooklyn Nets',
            'CHO': 'Charlotte Hornets', 'CHI': 'Chicago Bulls', 'CLE': 'Cleveland Cavaliers',
            'DAL': 'Dallas Mavericks', 'DEN': 'Denver Nuggets', 'DET': 'Detroit Pistons',
            'GSW': 'Golden State Warriors', 'HOU': 'Houston Rockets', 'IND': 'Indiana Pacers',
            'LAC': 'LA Clippers', 'LAL': 'Los Angeles Lakers', 'MEM': 'Memphis Grizzlies',
            'MIA': 'Miami Heat', 'MIL': 'Milwaukee Bucks', 'MIN': 'Minnesota Timberwolves',
            'NOP': 'New Orleans Pelicans', 'NYK': 'New York Knicks', 'OKC': 'Oklahoma City Thunder',
            'ORL': 'Orlando Magic', 'PHI': 'Philadelphia 76ers', 'PHX': 'Phoenix Suns',
            'POR': 'Portland Trail Blazers', 'SAC': 'Sacramento Kings', 'SAS': 'San Antonio Spurs',
            'TOR': 'Toronto Raptors', 'UTA': 'Utah Jazz', 'WAS': 'Washington Wizards'
        }