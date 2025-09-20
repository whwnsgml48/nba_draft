import streamlit as st
import pandas as pd
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.data_manager import DataManager
from utils.auction_manager import AuctionManager
from utils.nba_data import NBADataCollector

# 페이지 설정
st.set_page_config(
    page_title="NBA Fantasy Auction Tool",
    page_icon="🏀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세션 상태 초기화
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()
    st.session_state.data_manager.load_state()

if 'auction_manager' not in st.session_state:
    st.session_state.auction_manager = AuctionManager(st.session_state.data_manager)

def display_current_auction():
    """현재 경매 정보를 표시합니다."""
    auction_info = st.session_state.auction_manager.get_current_auction_info()
    
    if auction_info['is_active']:
        st.success(f"🔥 **현재 경매 중:** {auction_info['current_player']}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("현재 최고가", f"${auction_info['highest_bid']}")
        with col2:
            st.metric("최고 입찰자", auction_info['highest_bidder'])
        with col3:
            st.metric("다음 최소가", f"${auction_info['next_min_bid']}")
        
        # 선수 정보 카드
        player_info = st.session_state.auction_manager.get_player_info(auction_info['current_player'])
        if player_info:
            with st.container():
                st.markdown("### 선수 정보")
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("팀", player_info['team'])
                    st.metric("포지션", player_info['position'])
                
                with col2:
                    st.metric("득점", f"{player_info['points']:.1f}")
                    st.metric("리바운드", f"{player_info['rebounds']:.1f}")
                
                with col3:
                    st.metric("어시스트", f"{player_info['assists']:.1f}")
                    st.metric("스틸", f"{player_info['steals']:.1f}")
                
                with col4:
                    st.metric("블록", f"{player_info['blocks']:.1f}")
                    st.metric("판타지 순위", f"#{player_info['fantasy_rank']}")
        
        # 입찰 히스토리
        bid_history = st.session_state.auction_manager.get_bid_history()
        if bid_history:
            st.markdown("### 입찰 히스토리")
            df_history = pd.DataFrame(bid_history)
            st.dataframe(df_history, use_container_width=True)
    
    else:
        st.info("현재 진행 중인 경매가 없습니다.")

def player_search_section():
    """선수 검색 섹션"""
    st.markdown("### 선수 검색")
    
    search_query = st.text_input("선수 이름을 입력하세요", placeholder="예: LeBron James")
    
    if search_query:
        search_results = st.session_state.data_manager.search_players(search_query, limit=10)
        
        if not search_results.empty:
            st.markdown("#### 검색 결과")
            
            for idx, (_, player) in enumerate(search_results.iterrows()):
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                
                with col1:
                    st.write(f"**{player['name']}** ({player['team']} - {player['position']})")
                    st.caption(f"득점: {player['points']:.1f} | 리바운드: {player['rebounds']:.1f} | 어시스트: {player['assists']:.1f}")
                
                with col2:
                    st.metric("판타지 순위", f"#{player['fantasy_rank']}")
                
                with col3:
                    st.metric("판타지 점수", f"{player['fantasy_value']:.1f}")
                
                with col4:
                    if st.button(f"경매 시작", key=f"start_auction_{idx}"):
                        success = st.session_state.auction_manager.start_player_auction(player['name'])
                        if success:
                            st.success(f"{player['name']} 경매가 시작되었습니다!")
                            st.experimental_rerun()
                        else:
                            st.error("경매 시작에 실패했습니다.")
                
                st.divider()
        else:
            st.warning("검색 결과가 없습니다.")

def auction_control_section():
    """경매 제어 섹션"""
    auction_info = st.session_state.auction_manager.get_current_auction_info()
    
    if auction_info['is_active']:
        st.markdown("### 입찰하기")
        
        col1, col2 = st.columns(2)
        
        with col1:
            team_names = list(st.session_state.data_manager.teams.keys())
            selected_team = st.selectbox("입찰 팀", team_names)
            
            if selected_team:
                budget_left = st.session_state.data_manager.teams[selected_team].budget_left
                st.info(f"{selected_team} 남은 예산: ${budget_left}")
        
        with col2:
            suggested_bids = st.session_state.auction_manager.get_suggested_bids()
            if suggested_bids:
                selected_bid = st.selectbox("입찰가", suggested_bids)
            else:
                selected_bid = st.number_input(
                    "입찰가", 
                    min_value=auction_info['next_min_bid'], 
                    value=auction_info['next_min_bid']
                )
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("입찰하기", type="primary"):
                success, message = st.session_state.auction_manager.place_bid(selected_team, selected_bid)
                if success:
                    st.success(message)
                    st.experimental_rerun()
                else:
                    st.error(message)
        
        with col2:
            if st.button("낙찰", type="secondary"):
                success, message = st.session_state.auction_manager.finalize_current_auction()
                if success:
                    st.success(message)
                    st.experimental_rerun()
                else:
                    st.error(message)
        
        with col3:
            if st.button("경매 취소"):
                if st.session_state.auction_manager.cancel_current_auction():
                    st.info("경매가 취소되었습니다.")
                    st.experimental_rerun()

def roster_board_section():
    """로스터 보드 섹션"""
    st.markdown("### 팀별 로스터")
    
    team_summary = st.session_state.data_manager.get_team_summary()
    
    # 팀을 4개씩 3행으로 배치
    team_names = list(team_summary.keys())
    
    for row in range(0, len(team_names), 4):
        cols = st.columns(4)
        
        for col_idx, team_name in enumerate(team_names[row:row+4]):
            if col_idx < len(cols):
                with cols[col_idx]:
                    team_data = team_summary[team_name]
                    
                    st.markdown(f"**{team_name}**")
                    st.metric("남은 예산", f"${team_data['budget_left']}")
                    st.metric("선수 수", team_data['player_count'])
                    
                    if team_data['players']:
                        st.markdown("**선수 목록:**")
                        for player in team_data['players']:
                            st.caption(f"• {player['name']} ({player['position']}) - ${player['price']}")
                    else:
                        st.caption("선수 없음")

def main():
    """메인 앱"""
    st.title("🏀 NBA Fantasy Auction Tool")
    
    # 사이드바
    with st.sidebar:
        st.markdown("## 메뉴")
        
        # 데이터 상태 확인
        df = st.session_state.data_manager.load_players()
        if df.empty:
            st.warning("선수 데이터가 없습니다. 설정에서 데이터를 불러오세요.")
        else:
            available_count = len(st.session_state.data_manager.get_available_players())
            drafted_count = len(st.session_state.data_manager.get_drafted_players())
            st.info(f"사용 가능한 선수: {available_count}")
            st.info(f"드래프트된 선수: {drafted_count}")
        
        # CSV 내보내기
        if st.button("드래프트 결과 내보내기"):
            filepath = st.session_state.data_manager.export_draft_results()
            if filepath:
                st.success(f"결과가 {filepath}에 저장되었습니다.")
            else:
                st.error("내보내기에 실패했습니다.")
    
    # 메인 컨텐츠
    display_current_auction()
    
    st.divider()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        player_search_section()
    
    with col2:
        auction_control_section()
    
    st.divider()
    
    roster_board_section()

if __name__ == "__main__":
    main()