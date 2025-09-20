from typing import Dict, List, Optional, Tuple
import pandas as pd
from dataclasses import dataclass
from utils.data_manager import DataManager, Player

@dataclass
class BidHistory:
    team_name: str
    amount: int
    timestamp: str

class AuctionManager:
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.bid_history: List[BidHistory] = []
        self.min_bid_increment = 1
    
    def get_current_auction_info(self) -> Dict:
        """현재 경매 정보를 반환합니다."""
        auction_state = self.data_manager.auction_state
        
        if not auction_state.is_active:
            return {
                'is_active': False,
                'current_player': None,
                'highest_bid': 0,
                'highest_bidder': '',
                'next_min_bid': 1
            }
        
        next_min_bid = auction_state.highest_bid + self.min_bid_increment
        
        return {
            'is_active': auction_state.is_active,
            'current_player': auction_state.current_player,
            'highest_bid': auction_state.highest_bid,
            'highest_bidder': auction_state.highest_bidder,
            'next_min_bid': next_min_bid
        }
    
    def get_player_info(self, player_name: str) -> Optional[Dict]:
        """선수의 상세 정보를 반환합니다."""
        df = self.data_manager.get_available_players()
        if df.empty:
            return None
        
        player_data = df[df['name'] == player_name]
        if player_data.empty:
            return None
        
        player = player_data.iloc[0]
        return {
            'name': player['name'],
            'team': player['team'],
            'position': player['position'],
            'points': player['points'],
            'rebounds': player['rebounds'],
            'assists': player['assists'],
            'steals': player['steals'],
            'blocks': player['blocks'],
            'fantasy_value': player['fantasy_value'],
            'fantasy_rank': player['fantasy_rank']
        }
    
    def start_player_auction(self, player_name: str) -> bool:
        """선수 경매를 시작합니다."""
        # 현재 다른 경매가 진행 중인지 확인
        if self.data_manager.auction_state.is_active:
            return False
        
        # 선수가 존재하고 사용 가능한지 확인
        player_info = self.get_player_info(player_name)
        if not player_info:
            return False
        
        # 경매 시작
        self.data_manager.start_auction(player_name)
        self.bid_history = []  # 입찰 히스토리 초기화
        
        return True
    
    def place_bid(self, team_name: str, amount: int) -> Tuple[bool, str]:
        """입찰을 진행합니다."""
        # 경매가 진행 중인지 확인
        if not self.data_manager.auction_state.is_active:
            return False, "진행 중인 경매가 없습니다."
        
        # 팀이 존재하는지 확인
        if team_name not in self.data_manager.teams:
            return False, "존재하지 않는 팀입니다."
        
        # 팀 예산 확인
        team = self.data_manager.teams[team_name]
        if team.budget_left < amount:
            return False, f"예산 부족: 남은 예산 ${team.budget_left}"
        
        # 최소 입찰가 확인
        min_bid = self.data_manager.auction_state.highest_bid + self.min_bid_increment
        if amount < min_bid:
            return False, f"최소 입찰가는 ${min_bid}입니다."
        
        # 입찰 진행
        success = self.data_manager.place_bid(team_name, amount)
        if success:
            from datetime import datetime
            self.bid_history.append(BidHistory(
                team_name=team_name,
                amount=amount,
                timestamp=datetime.now().strftime("%H:%M:%S")
            ))
            return True, f"{team_name}이(가) ${amount}에 입찰했습니다."
        else:
            return False, "입찰에 실패했습니다."
    
    def finalize_current_auction(self) -> Tuple[bool, str]:
        """현재 경매를 마무리합니다."""
        if not self.data_manager.auction_state.is_active:
            return False, "진행 중인 경매가 없습니다."
        
        if not self.data_manager.auction_state.highest_bidder:
            return False, "입찰자가 없습니다."
        
        player_name = self.data_manager.auction_state.current_player
        winning_team = self.data_manager.auction_state.highest_bidder
        winning_bid = self.data_manager.auction_state.highest_bid
        
        success = self.data_manager.finalize_auction()
        
        if success:
            return True, f"{player_name}이(가) {winning_team}에게 ${winning_bid}에 낙찰되었습니다!"
        else:
            return False, "경매 마무리에 실패했습니다."
    
    def cancel_current_auction(self) -> bool:
        """현재 경매를 취소합니다."""
        if not self.data_manager.auction_state.is_active:
            return False
        
        # 경매 상태 초기화
        from utils.data_manager import AuctionState
        self.data_manager.auction_state = AuctionState()
        self.data_manager.save_state()
        self.bid_history = []
        
        return True
    
    def get_bid_history(self) -> List[Dict]:
        """입찰 히스토리를 반환합니다."""
        return [
            {
                'team': bid.team_name,
                'amount': bid.amount,
                'time': bid.timestamp
            }
            for bid in self.bid_history
        ]
    
    def get_team_budgets(self) -> Dict[str, int]:
        """모든 팀의 남은 예산을 반환합니다."""
        return {
            team_name: team.budget_left
            for team_name, team in self.data_manager.teams.items()
        }
    
    def get_affordable_teams(self, amount: int) -> List[str]:
        """특정 금액을 입찰할 수 있는 팀 목록을 반환합니다."""
        return [
            team_name for team_name, team in self.data_manager.teams.items()
            if team.budget_left >= amount
        ]
    
    def validate_bid_amount(self, amount: int) -> Tuple[bool, str]:
        """입찰 금액의 유효성을 검사합니다."""
        if not self.data_manager.auction_state.is_active:
            return False, "진행 중인 경매가 없습니다."
        
        if amount <= 0:
            return False, "입찰 금액은 0보다 커야 합니다."
        
        min_bid = self.data_manager.auction_state.highest_bid + self.min_bid_increment
        if amount < min_bid:
            return False, f"최소 입찰가는 ${min_bid}입니다."
        
        # 입찰 가능한 팀이 있는지 확인
        affordable_teams = self.get_affordable_teams(amount)
        if not affordable_teams:
            return False, f"${amount}를 입찰할 수 있는 팀이 없습니다."
        
        return True, "유효한 입찰 금액입니다."
    
    def get_suggested_bids(self) -> List[int]:
        """추천 입찰가 목록을 반환합니다."""
        if not self.data_manager.auction_state.is_active:
            return []
        
        current_bid = self.data_manager.auction_state.highest_bid
        suggestions = []
        
        # 최소 입찰가
        min_bid = current_bid + self.min_bid_increment
        suggestions.append(min_bid)
        
        # 추가 추천가 (5, 10, 15, 20 단위)
        increments = [5, 10, 15, 20]
        for inc in increments:
            suggested = current_bid + inc
            if suggested not in suggestions:
                suggestions.append(suggested)
        
        # 예산 범위 내에서만 반환
        max_budget = max(self.get_team_budgets().values())
        return [bid for bid in suggestions if bid <= max_budget]