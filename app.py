import streamlit as st
import pandas as pd
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.data_manager import DataManager
from src.utils.auction_manager import AuctionManager
from src.utils.nba_data import NBADataCollector

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
else:
    # 이미 존재하는 경우에도 최신 상태 로드 (설정 변경 반영)
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
        
        # 선수 정보 표
        player_info = st.session_state.auction_manager.get_player_info(auction_info['current_player'])
        if player_info:
            st.markdown("### 선수 정보")
            
            # 선수 정보를 표 형태로 표시
            player_data = {
                '항목': ['팀', '포지션', '득점', '리바운드', '어시스트', '스틸', '블록', '판타지 순위'],
                '값': [
                    player_info['team'],
                    player_info['position'],
                    f"{player_info['points']:.1f}",
                    f"{player_info['rebounds']:.1f}",
                    f"{player_info['assists']:.1f}",
                    f"{player_info['steals']:.1f}",
                    f"{player_info['blocks']:.1f}",
                    f"#{player_info['fantasy_rank']}"
                ]
            }
            
            df_player = pd.DataFrame(player_data)
            st.dataframe(df_player, width='stretch', hide_index=True, height=300)
        
        # 입찰 히스토리
        bid_history = st.session_state.auction_manager.get_bid_history()
        if bid_history:
            st.markdown("### 입찰 히스토리")
            df_history = pd.DataFrame(bid_history)
            st.dataframe(df_history, width='stretch')
    
    else:
        st.info("현재 진행 중인 경매가 없습니다.")

def player_search_section():
    """선수 검색 섹션 (사이드바용으로 최적화)"""
    # 사용 가능한 모든 선수 목록 가져오기
    available_players = st.session_state.data_manager.get_available_players()

    if available_players.empty:
        st.warning("선수 데이터가 없습니다.")
        return

    # 선수 이름 목록 생성 (팀 정보 포함)
    player_options = []
    player_data_map = {}

    for _, player in available_players.iterrows():
        display_name = f"{player['name']} ({player['team']})"
        player_options.append(display_name)
        player_data_map[display_name] = player

    # 자동완성 selectbox
    # 검색에서 선택된 선수가 있으면 기본값으로 설정
    default_index = 0
    if hasattr(st.session_state, 'selected_player_from_search'):
        search_selection = st.session_state.selected_player_from_search
        if search_selection in player_options:
            default_index = sorted(player_options).index(search_selection) + 1
            # 한 번 사용한 후 삭제
            delattr(st.session_state, 'selected_player_from_search')

    selected_option = st.selectbox(
        "선수 선택",
        options=["선수 선택..."] + sorted(player_options),
        index=default_index,
        help="선수 이름을 타이핑하면 자동완성됩니다"
    )

    # 텍스트 검색도 병행 제공
    search_query = st.text_input(
        "이름으로 검색",
        placeholder="예: LeBron"
    )

    selected_player = None

    # selectbox에서 선수가 선택된 경우
    if selected_option != "선수 선택...":
        selected_player = player_data_map[selected_option]

        # 선수 정보 카드 표시 (컴팩트하게)
        st.markdown("---")

        # 선수 기본 정보 (한 줄에)
        st.markdown(f"**{selected_player['name']}** #{selected_player['fantasy_rank']}")
        st.caption(f"{selected_player['team']} {selected_player['position']} • {selected_player['points']:.1f}pts")

        # 핵심 스탯을 한 줄에 (작게)
        stats_line = f"📈 {selected_player['rebounds']:.1f}reb • {selected_player['assists']:.1f}ast • {selected_player['steals']:.1f}stl • {selected_player['blocks']:.1f}blk"
        st.caption(stats_line)

        # 경매 시작 버튼
        if st.button("🔥 경매 시작", type="primary", key="auction_start_sidebar", use_container_width=True):
            # 현재 경매 상태 확인
            current_auction = st.session_state.auction_manager.get_current_auction_info()
            if current_auction['is_active']:
                st.error(f"이미 {current_auction['current_player']} 경매가 진행 중입니다.")
            else:
                success = st.session_state.auction_manager.start_player_auction(selected_player['name'])
                if success:
                    st.success(f"{selected_player['name']} 경매 시작!")
                    st.rerun()
                else:
                    st.error("경매 시작 실패")

    # 텍스트 검색 결과
    elif search_query:
        search_results = st.session_state.data_manager.search_players(search_query, limit=3)

        if not search_results.empty:
            st.markdown("**검색 결과:**")

            # 간단한 목록 형태로 표시
            for idx, (_, player) in enumerate(search_results.iterrows()):
                if st.button(
                    f"{player['name']} ({player['team']})",
                    key=f"search_select_{idx}",
                    use_container_width=True
                ):
                    # 선택된 선수를 selectbox에 반영하기 위해 세션 상태 사용
                    display_name = f"{player['name']} ({player['team']})"
                    st.session_state.selected_player_from_search = display_name
                    st.rerun()
        else:
            st.info("검색 결과 없음")
    

def auction_control_section():
    """경매 제어 섹션 (사이드바 최적화)"""
    auction_info = st.session_state.auction_manager.get_current_auction_info()

    if auction_info['is_active']:
        # 현재 경매 중인 선수 표시
        st.markdown(f"**현재 경매: {auction_info['current_player']}**")
        st.caption(f"최고가: ${auction_info['highest_bid']} ({auction_info['highest_bidder']})")

        # 팀 선택
        team_names = list(st.session_state.data_manager.teams.keys())
        selected_team = st.selectbox("입찰 팀", team_names, key="sidebar_team_select")

        if selected_team:
            budget_left = st.session_state.data_manager.teams[selected_team].budget_left
            st.caption(f"남은 예산: ${budget_left}")

        # 입찰가 선택
        suggested_bids = st.session_state.auction_manager.get_suggested_bids()
        if suggested_bids:
            selected_bid = st.selectbox("입찰가", suggested_bids, key="sidebar_bid_select")
        else:
            selected_bid = st.number_input(
                "입찰가",
                min_value=auction_info['next_min_bid'],
                value=auction_info['next_min_bid'],
                key="sidebar_bid_input"
            )

        # 버튼들 (전체 폭 사용)
        if st.button("💰 입찰하기", type="primary", use_container_width=True, key="sidebar_bid_btn"):
            success, message = st.session_state.auction_manager.place_bid(selected_team, selected_bid)
            if success:
                st.success("입찰 성공!")
                st.rerun()
            else:
                st.error(message)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ 낙찰", key="sidebar_finalize_btn", use_container_width=True):
                success, message = st.session_state.auction_manager.finalize_current_auction()
                if success:
                    st.success("낙찰!")
                    st.rerun()
                else:
                    st.error(message)

        with col2:
            if st.button("❌ 취소", key="sidebar_cancel_btn", use_container_width=True):
                if st.session_state.auction_manager.cancel_current_auction():
                    st.info("경매 취소됨")
                    st.rerun()

    else:
        st.info("진행 중인 경매가 없습니다.")
        st.caption("👈 아래에서 선수를 선택하고 경매를 시작하세요.")

def team_settings_section():
    """팀 설정 섹션"""
    st.markdown("## 팀 설정")
    
    team_names = st.session_state.data_manager.get_team_names()
    
    with st.expander("팀 이름 변경", expanded=False):
        selected_team = st.selectbox("변경할 팀 선택", team_names)
        new_name = st.text_input("새 팀 이름", value=selected_team)
        
        if st.button("팀 이름 변경"):
            if new_name and new_name != selected_team:
                if new_name not in team_names:
                    success = st.session_state.data_manager.update_team_name(selected_team, new_name)
                    if success:
                        st.success(f"{selected_team} → {new_name}으로 변경되었습니다!")
                        st.rerun()
                    else:
                        st.error("팀 이름 변경에 실패했습니다.")
                else:
                    st.error("이미 존재하는 팀 이름입니다.")
            else:
                st.warning("새 팀 이름을 입력하세요.")

def team_overview_dashboard():
    """팀별 현황 대시보드 (표 형태)"""
    st.markdown("## 🏀 팀별 현황")

    team_summary = st.session_state.data_manager.get_team_summary()

    if not team_summary:
        st.info("팀 정보를 불러올 수 없습니다.")
        return

    # 팀별 현황을 표 형태로 구성
    team_overview_data = []

    for team_name, team_data in team_summary.items():
        # 최근 뽑은 선수 3명만 표시
        recent_players = []
        if team_data['players']:
            for player in team_data['players'][-3:]:  # 최근 3명
                recent_players.append(f"{player['name']} (${player['price']})")

        recent_players_str = " / ".join(recent_players) if recent_players else "없음"

        team_overview_data.append({
            '팀명': team_name,
            '뽑은 선수': f"{team_data['player_count']}/15",
            '남은 예산': f"${team_data['budget_left']}",
            '사용한 예산': f"${team_data['total_spent']}",
            '최근 영입 선수': recent_players_str
        })

    if team_overview_data:
        df_overview = pd.DataFrame(team_overview_data)
        st.dataframe(df_overview, width='stretch', hide_index=True, height=400)

def roster_board_section():
    """팀별 통계 요약 섹션"""
    with st.expander("📊 팀별 통계 요약", expanded=False):
        team_summary = st.session_state.data_manager.get_team_summary()

        team_summary_data = []
        for team_name, team_data in team_summary.items():
            total_points = sum(p['points'] for p in team_data['players']) if team_data['players'] else 0
            total_rebounds = sum(p['rebounds'] for p in team_data['players']) if team_data['players'] else 0
            total_assists = sum(p['assists'] for p in team_data['players']) if team_data['players'] else 0

            team_summary_data.append({
                '팀명': team_name,
                '선수 수': f"{team_data['player_count']}/15",
                '남은 예산': f"${team_data['budget_left']}",
                '사용한 예산': f"${team_data['total_spent']}",
                '총 득점': f"{total_points:.1f}",
                '총 리바운드': f"{total_rebounds:.1f}",
                '총 어시스트': f"{total_assists:.1f}"
            })

        if team_summary_data:
            df_summary = pd.DataFrame(team_summary_data)
            st.dataframe(df_summary, width='stretch', hide_index=True)
        else:
            st.info("팀 정보를 불러올 수 없습니다.")

def main():
    """메인 앱"""
    st.title("🏀 NBA Fantasy Auction Tool")
    
    # 사이드바
    with st.sidebar:
        st.markdown("## ⚡ 경매 제어")

        # 경매 제어 섹션을 사이드바 최상단으로 이동
        auction_control_section()

        st.divider()

        st.markdown("## 🎯 선수 검색")

        # 선수 검색 섹션
        player_search_section()

        st.divider()

        st.markdown("## ⚙️ 설정")

        # 팀 설정
        team_settings_section()

        st.divider()

        st.markdown("## 📊 데이터 현황")

        # 데이터 상태 확인
        df = st.session_state.data_manager.load_players()
        if df.empty:
            st.warning("선수 데이터가 없습니다. 설정에서 데이터를 불러오세요.")
        else:
            available_count = len(st.session_state.data_manager.get_available_players())
            drafted_count = len(st.session_state.data_manager.get_drafted_players())

            col1, col2 = st.columns(2)
            with col1:
                st.metric("사용 가능", available_count)
            with col2:
                st.metric("드래프트됨", drafted_count)

        st.divider()

        st.markdown("## 💾 내보내기")

        # CSV 내보내기
        if st.button("📥 드래프트 결과 내보내기", use_container_width=True):
            filepath = st.session_state.data_manager.export_draft_results()
            if filepath:
                st.success(f"결과가 {filepath}에 저장되었습니다.")
            else:
                st.error("내보내기에 실패했습니다.")
    
    # 메인 컨텐츠

    # 1. 현재 경매 정보 (최우선)
    display_current_auction()

    st.divider()

    # 2. 팀별 상세 선수 목록
    st.markdown("### 📋 팀별 상세 선수 목록")

    team_summary = st.session_state.data_manager.get_team_summary()

    # 모든 팀의 데이터를 하나의 테이블로 구성 (선수 컬럼 10개 고정)
    team_roster_data = []
    max_display_players = 10  # 표시할 최대 선수 수를 10명으로 고정

    for team_name, team_data in team_summary.items():
        row_data = {
            '팀명': team_name,
            '남은 예산': f"${team_data['budget_left']}",
            '선수 수': f"{team_data['player_count']}/15"
        }

        # 각 선수를 별도 컬럼으로 추가 (최대 10명까지)
        for i, player in enumerate(team_data['players'][:max_display_players]):
            player_info = f"{player['name']} ({player['position']}) ${player['price']}"
            row_data[f'선수{i+1}'] = player_info

        # 빈 선수 슬롯은 빈 문자열로 채움 (항상 10개 컬럼 유지)
        for i in range(len(team_data['players']), max_display_players):
            row_data[f'선수{i+1}'] = ""

        team_roster_data.append(row_data)

    if team_roster_data:
        df_roster = pd.DataFrame(team_roster_data)
        st.dataframe(df_roster, width='stretch', hide_index=True, height=460)
    else:
        st.info("팀 정보를 불러올 수 없습니다.")

    st.divider()

    # 5. 상세 통계는 확장 가능한 섹션으로
    roster_board_section()

if __name__ == "__main__":
    main()