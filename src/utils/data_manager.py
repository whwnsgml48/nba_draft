import json
import pandas as pd
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class Player:
    player_id: int
    name: str
    team: str
    position: str
    points: float
    rebounds: float
    assists: float
    steals: float
    blocks: float
    fantasy_value: float
    fantasy_rank: int
    draft_status: str = 'available'  # 'available', 'drafted'
    draft_price: int = 0
    draft_team: str = ''

@dataclass
class Team:
    name: str
    budget_left: int
    players: List[Dict]
    
    def add_player(self, player: Player, price: int):
        self.players.append({
            'name': player.name,
            'position': player.position,
            'price': price,
            'points': player.points,
            'rebounds': player.rebounds,
            'assists': player.assists,
            'steals': player.steals,
            'blocks': player.blocks
        })
        self.budget_left -= price

@dataclass
class AuctionState:
    current_player: Optional[str] = None
    highest_bid: int = 0
    highest_bidder: str = ''
    is_active: bool = False

@dataclass
class LeagueSettings:
    team_budget: int = 200
    min_bid_increment: int = 1
    max_players_per_team: int = 15
    league_name: str = "NBA Fantasy League"
    total_teams: int = 12

class DataManager:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.players_file = os.path.join(data_dir, "players.csv")
        self.state_file = os.path.join(data_dir, "state.json")
        
        # 데이터 디렉토리 생성
        os.makedirs(data_dir, exist_ok=True)
        
        # 기본값으로 초기화
        self.league_settings = LeagueSettings()
        self.auction_state = AuctionState()
        self.teams = {}
        
        # 저장된 상태가 있으면 로드, 없으면 기본 팀 생성
        self._load_or_initialize()
    
    def _load_or_initialize(self):
        """저장된 상태를 로드하거나 기본값으로 초기화"""
        if os.path.exists(self.state_file):
            self.load_state()
        else:
            # 처음 실행 시 기본 팀 생성
            self.teams = self._initialize_teams()
    
    def _initialize_teams(self, budget_per_team: int = None) -> Dict[str, Team]:
        """설정된 팀 수만큼 팀을 초기화합니다."""
        if budget_per_team is None:
            budget_per_team = self.league_settings.team_budget

        # 실제 팀 이름들
        team_names = ["준희", "정명", "단열", "경찬", "병욱", "원준",
                     "윤범", "진빈", "지원", "두현", "수현", "철웅"]

        teams = {}
        for i in range(self.league_settings.total_teams):
            team_name = team_names[i] if i < len(team_names) else f"Team {i+1}"
            teams[team_name] = Team(
                name=team_name,
                budget_left=budget_per_team,
                players=[]
            )
        return teams
    
    def load_players(self) -> pd.DataFrame:
        """선수 데이터를 불러옵니다."""
        try:
            if os.path.exists(self.players_file):
                df = pd.read_csv(self.players_file, encoding='utf-8')
                # Ensure proper data types
                if not df.empty:
                    df['draft_price'] = df['draft_price'].astype('int64')
                    df['draft_team'] = df['draft_team'].astype('string')
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"선수 데이터 로드 중 오류: {e}")
            return pd.DataFrame()
    
    def save_players(self, df: pd.DataFrame):
        """선수 데이터를 저장합니다."""
        try:
            df.to_csv(self.players_file, index=False, encoding='utf-8')
        except Exception as e:
            print(f"선수 데이터 저장 중 오류: {e}")
    
    def load_state(self):
        """드래프트 상태를 불러옵니다."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 리그 설정 복원
                if 'league_settings' in data:
                    settings_data = data['league_settings']
                    self.league_settings = LeagueSettings(
                        team_budget=settings_data.get('team_budget', 200),
                        min_bid_increment=settings_data.get('min_bid_increment', 1),
                        max_players_per_team=settings_data.get('max_players_per_team', 15),
                        league_name=settings_data.get('league_name', "NBA Fantasy League"),
                        total_teams=settings_data.get('total_teams', 12)
                    )
                
                # 팀 데이터 복원
                if 'teams' in data:
                    self.teams = {}
                    for team_name, team_data in data['teams'].items():
                        self.teams[team_name] = Team(
                            name=team_data['name'],
                            budget_left=team_data['budget_left'],
                            players=team_data['players']
                        )
                
                # 경매 상태 복원
                if 'auction_state' in data:
                    auction_data = data['auction_state']
                    self.auction_state = AuctionState(
                        current_player=auction_data.get('current_player'),
                        highest_bid=auction_data.get('highest_bid', 0),
                        highest_bidder=auction_data.get('highest_bidder', ''),
                        is_active=auction_data.get('is_active', False)
                    )
        
        except Exception as e:
            print(f"상태 로드 중 오류: {e}")
    
    def save_state(self):
        """현재 드래프트 상태를 저장합니다."""
        try:
            data = {
                'league_settings': asdict(self.league_settings),
                'teams': {name: asdict(team) for name, team in self.teams.items()},
                'auction_state': asdict(self.auction_state),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        except Exception as e:
            print(f"상태 저장 중 오류: {e}")
    
    def start_auction(self, player_name: str):
        """특정 선수의 경매를 시작합니다."""
        self.auction_state.current_player = player_name
        self.auction_state.highest_bid = 1  # 최소 입찰가
        self.auction_state.highest_bidder = ''
        self.auction_state.is_active = True
        self.save_state()
    
    def place_bid(self, team_name: str, amount: int) -> bool:
        """입찰을 진행합니다."""
        if not self.auction_state.is_active:
            return False
        
        if team_name not in self.teams:
            return False
        
        if self.teams[team_name].budget_left < amount:
            return False
        
        if amount <= self.auction_state.highest_bid:
            return False
        
        self.auction_state.highest_bid = amount
        self.auction_state.highest_bidder = team_name
        self.save_state()
        return True
    
    def finalize_auction(self) -> bool:
        """경매를 마무리하고 선수를 낙찰시킵니다."""
        if not self.auction_state.is_active or not self.auction_state.highest_bidder:
            return False
        
        # 선수 데이터 업데이트
        df = self.load_players()
        if not df.empty:
            player_idx = df[df['name'] == self.auction_state.current_player].index
            if len(player_idx) > 0:
                df.loc[player_idx[0], 'draft_status'] = 'drafted'
                df.loc[player_idx[0], 'draft_price'] = int(self.auction_state.highest_bid)
                df.loc[player_idx[0], 'draft_team'] = str(self.auction_state.highest_bidder)
                
                # 팀에 선수 추가
                player_data = df.loc[player_idx[0]]
                player = Player(
                    player_id=int(player_data['player_id']),
                    name=player_data['name'],
                    team=player_data['team'],
                    position=player_data['position'],
                    points=float(player_data['points']),
                    rebounds=float(player_data['rebounds']),
                    assists=float(player_data['assists']),
                    steals=float(player_data['steals']),
                    blocks=float(player_data['blocks']),
                    fantasy_value=float(player_data['fantasy_value']),
                    fantasy_rank=int(player_data['fantasy_rank'])
                )
                
                self.teams[self.auction_state.highest_bidder].add_player(
                    player, self.auction_state.highest_bid
                )
                
                self.save_players(df)
        
        # 경매 상태 초기화
        self.auction_state = AuctionState()
        self.save_state()
        return True
    
    def get_available_players(self) -> pd.DataFrame:
        """사용 가능한 선수 목록을 반환합니다."""
        df = self.load_players()
        if df.empty:
            return df
        return df[df['draft_status'] == 'available'].copy()
    
    def get_drafted_players(self) -> pd.DataFrame:
        """드래프트된 선수 목록을 반환합니다."""
        df = self.load_players()
        if df.empty:
            return df
        return df[df['draft_status'] == 'drafted'].copy()
    
    def search_players(self, query: str, limit: int = 10) -> pd.DataFrame:
        """선수 이름으로 검색합니다."""
        available_players = self.get_available_players()
        if available_players.empty:
            return available_players
        
        # 이름에 쿼리가 포함된 선수들 찾기
        filtered = available_players[
            available_players['name'].str.contains(query, case=False, na=False)
        ]
        
        return filtered.head(limit)
    
    def export_draft_results(self, filename: str = None) -> str:
        """드래프트 결과를 CSV로 내보냅니다."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"draft_results_{timestamp}.csv"
        
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            df = self.load_players()
            if not df.empty:
                # 드래프트 결과만 필터링
                export_df = df[['name', 'team', 'position', 'draft_status', 
                              'draft_price', 'draft_team', 'points', 'rebounds', 
                              'assists', 'steals', 'blocks', 'fantasy_rank']].copy()
                
                export_df.to_csv(filepath, index=False, encoding='utf-8')
                return filepath
            
        except Exception as e:
            print(f"내보내기 중 오류: {e}")
            return ""
        
        return ""
    
    def get_team_summary(self) -> Dict:
        """모든 팀의 요약 정보를 반환합니다."""
        summary = {}
        for team_name, team in self.teams.items():
            total_spent = 200 - team.budget_left
            player_count = len(team.players)
            
            summary[team_name] = {
                'budget_left': team.budget_left,
                'total_spent': total_spent,
                'player_count': player_count,
                'players': team.players
            }
        
        return summary
    
    def update_team_name(self, old_name: str, new_name: str) -> bool:
        """팀 이름을 변경합니다."""
        if old_name not in self.teams or new_name in self.teams:
            return False
        
        # 새 이름으로 팀 복사
        team = self.teams[old_name]
        team.name = new_name
        self.teams[new_name] = team
        
        # 기존 이름의 팀 삭제
        del self.teams[old_name]
        
        # 선수 데이터의 draft_team도 업데이트
        df = self.load_players()
        if not df.empty:
            df.loc[df['draft_team'] == old_name, 'draft_team'] = new_name
            self.save_players(df)
        
        # 경매 상태의 highest_bidder도 업데이트
        if self.auction_state.highest_bidder == old_name:
            self.auction_state.highest_bidder = new_name
        
        self.save_state()
        return True
    
    def get_team_names(self) -> List[str]:
        """모든 팀 이름을 반환합니다."""
        return list(self.teams.keys())
    
    def update_league_settings(self, **kwargs) -> bool:
        """리그 설정을 업데이트합니다."""
        try:
            old_total_teams = self.league_settings.total_teams
            old_team_budget = self.league_settings.team_budget
            
            # 설정 업데이트
            for key, value in kwargs.items():
                if hasattr(self.league_settings, key):
                    setattr(self.league_settings, key, value)
            
            # 팀 수 변경 시 처리
            if 'total_teams' in kwargs and kwargs['total_teams'] != old_total_teams:
                new_teams = kwargs['total_teams']
                print(f"팀 수 변경: {old_total_teams} → {new_teams}")
                
                # 기존 팀 데이터 백업
                existing_teams_data = {}
                for name, team in self.teams.items():
                    existing_teams_data[name] = {
                        'budget_left': team.budget_left,
                        'players': team.players.copy()
                    }
                
                # 새 팀 구조 생성
                self.teams = self._initialize_teams()
                
                # 기존 데이터 복원 (새 팀 수 범위 내에서)
                for name, team in self.teams.items():
                    if name in existing_teams_data:
                        team.budget_left = existing_teams_data[name]['budget_left']
                        team.players = existing_teams_data[name]['players']
            
            # 예산 변경 시 처리 (팀 수 변경과 별개로 처리)
            if 'team_budget' in kwargs and kwargs['team_budget'] != old_team_budget:
                new_budget = kwargs['team_budget']
                print(f"팀 예산 변경: ${old_team_budget} → ${new_budget}")
                
                # 드래프트하지 않은 팀들의 예산 업데이트
                for team in self.teams.values():
                    if team.budget_left == old_team_budget:  # 기본 예산 그대로인 팀만
                        team.budget_left = new_budget
            
            self.save_state()
            print("리그 설정 업데이트 및 저장 완료")
            return True
            
        except Exception as e:
            print(f"리그 설정 업데이트 중 오류: {e}")
            return False
    
    def get_league_settings(self) -> LeagueSettings:
        """현재 리그 설정을 반환합니다."""
        return self.league_settings