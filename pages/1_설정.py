import streamlit as st
import sys
import os
import pandas as pd

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.nba_data import NBADataCollector
from utils.data_manager import DataManager

st.set_page_config(
    page_title="설정 - NBA Fantasy Auction Tool",
    page_icon="⚙️",
    layout="wide"
)

st.title("⚙️ 설정")

# 세션 상태 초기화
if 'data_manager' not in st.session_state:
    st.session_state.data_manager = DataManager()

def data_collection_section():
    """데이터 수집 섹션"""
    st.markdown("## NBA 선수 데이터 관리")
    
    # 현재 데이터 상태
    df = st.session_state.data_manager.load_players()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if not df.empty:
            st.info(f"현재 선수 데이터: {len(df)}명")
            st.metric("사용 가능한 선수", len(df[df['draft_status'] == 'available']))
            st.metric("드래프트된 선수", len(df[df['draft_status'] == 'drafted']))
        else:
            st.warning("선수 데이터가 없습니다.")
    
    with col2:
        st.markdown("**자동 수집 범위:**")
        st.write("✅ Basketball Reference 공식 데이터")
        st.write("✅ NBA API 실시간 로스터 정보")
        st.write("✅ 자동 트레이드 반영 시스템")
        st.write("✅ 정확한 판타지 순위 계산")
    
    st.info("🔄 **Basketball Reference 데이터**: 가장 정확하고 신뢰할 수 있는 Basketball Reference에서 2024-25 시즌 선수 데이터를 가져옵니다. (약 1-2분 소요)")
    
    # 데이터 수집 버튼
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🏀 Basketball Reference 데이터 수집", type="primary"):
            progress_placeholder = st.empty()
            
            with st.spinner("NBA 선수 데이터를 수집하는 중..."):
                try:
                    collector = NBADataCollector()
                    
                    # 진행상황 표시
                    progress_placeholder.info("🔍 활성 선수 목록을 가져오는 중...")
                    
                    # 모든 활성 선수 실시간 데이터 수집 (설정 없음)
                    new_df = collector.create_players_dataset()
                    
                    progress_placeholder.info("💾 데이터를 저장하는 중...")
                    
                    # 데이터 저장 전 현재 상태 확인
                    old_df = st.session_state.data_manager.load_players()
                    old_count = len(old_df) if not old_df.empty else 0
                    
                    # 데이터 저장
                    st.session_state.data_manager.save_players(new_df)
                    
                    # 저장 후 다시 로드해서 확인
                    saved_df = st.session_state.data_manager.load_players()
                    
                    progress_placeholder.empty()
                    
                    st.success(f"✅ {len(new_df)}명의 실시간 선수 데이터가 업데이트되었습니다!")
                    st.info(f"📊 이전: {old_count}명 → 현재: {len(saved_df)}명")
                    
                    # 실제 파일 존재 확인
                    import os
                    if os.path.exists("data/players.csv"):
                        file_size = os.path.getsize("data/players.csv")
                        st.info(f"📁 파일 크기: {file_size:,} bytes")
                    
                    st.rerun()
                        
                except Exception as e:
                    progress_placeholder.empty()
                    st.error(f"❌ 데이터 수집 실패: {str(e)}")
                    st.info("💡 해결 방법:")
                    st.info("• 네트워크 연결을 확인하세요")
                    st.info("• 잠시 후 다시 시도해보세요")
                    st.info("• NBA API 서버가 일시적으로 사용 불가할 수 있습니다")
    
    with col2:
        if st.button("🗑️ 데이터 초기화"):
            if st.session_state.get('confirm_reset', False):
                # 실제 초기화 수행
                os.makedirs('data', exist_ok=True)
                empty_df = pd.DataFrame()
                st.session_state.data_manager.save_players(empty_df)
                
                # 상태 파일도 초기화
                state_file = 'data/state.json'
                if os.path.exists(state_file):
                    os.remove(state_file)
                
                st.session_state.data_manager = DataManager()
                st.session_state['confirm_reset'] = False
                st.success("✅ 모든 데이터가 초기화되었습니다!")
                st.rerun()
            else:
                st.session_state['confirm_reset'] = True
                st.warning("⚠️ 한 번 더 클릭하면 모든 데이터가 삭제됩니다!")
    
    # 현재 데이터 미리보기
    if not df.empty:
        st.markdown("### 현재 선수 데이터 미리보기")
        
        # 필터링 옵션
        col1, col2, col3 = st.columns(3)
        
        with col1:
            show_status = st.selectbox(
                "상태",
                ['전체', 'available', 'drafted']
            )
        
        with col2:
            positions = ['전체'] + list(df['position'].unique())
            show_position = st.selectbox("포지션", positions)
        
        with col3:
            teams = ['전체'] + list(df['team'].unique())
            show_team = st.selectbox("팀", teams)
        
        # 필터링 적용
        filtered_df = df.copy()
        
        if show_status != '전체':
            filtered_df = filtered_df[filtered_df['draft_status'] == show_status]
        
        if show_position != '전체':
            filtered_df = filtered_df[filtered_df['position'] == show_position]
        
        if show_team != '전체':
            filtered_df = filtered_df[filtered_df['team'] == show_team]
        
        # 표시할 컬럼 선택
        display_columns = [
            'name', 'team', 'position', 'points', 'rebounds', 'assists',
            'steals', 'blocks', 'fantasy_rank', 'draft_status', 'draft_team', 'draft_price'
        ]
        
        st.dataframe(
            filtered_df[display_columns],
            width='stretch',
            height=400
        )

def league_settings_section():
    """리그 설정 섹션"""
    st.markdown("## 리그 설정")
    
    # 현재 설정 가져오기
    current_settings = st.session_state.data_manager.get_league_settings()
    
    with st.form("league_settings_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 기본 설정")
            
            league_name = st.text_input(
                "리그 이름",
                value=current_settings.league_name,
                help="판타지 리그의 이름을 설정하세요"
            )
            
            total_teams = st.slider(
                "총 팀 수",
                min_value=4,
                max_value=16,
                value=current_settings.total_teams,
                step=1,
                help="참여하는 팀의 수를 설정하세요"
            )
            
            team_budget = st.number_input(
                "팀별 초기 예산",
                min_value=100,
                max_value=1000,
                value=current_settings.team_budget,
                step=10,
                help="각 팀의 시작 예산 (달러)"
            )
        
        with col2:
            st.markdown("### 경매 설정")
            
            min_bid_increment = st.number_input(
                "최소 입찰 증가액",
                min_value=1,
                max_value=10,
                value=current_settings.min_bid_increment,
                help="각 입찰 시 최소 증가 금액"
            )
            
            max_players_per_team = st.number_input(
                "팀당 최대 선수 수",
                min_value=10,
                max_value=20,
                value=current_settings.max_players_per_team,
                help="각 팀이 드래프트할 수 있는 최대 선수 수"
            )
        
        # 설정 저장 버튼
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            submit_button = st.form_submit_button("💾 설정 저장", type="primary")
        
        with col2:
            reset_button = st.form_submit_button("🔄 기본값 복원")
    
    # 버튼 처리
    if submit_button:
        success = st.session_state.data_manager.update_league_settings(
            league_name=league_name,
            total_teams=total_teams,
            team_budget=team_budget,
            min_bid_increment=min_bid_increment,
            max_players_per_team=max_players_per_team
        )
        
        if success:
            st.success("✅ 리그 설정이 저장되었습니다!")
            st.rerun()
        else:
            st.error("❌ 설정 저장에 실패했습니다.")
    
    if reset_button:
        success = st.session_state.data_manager.update_league_settings(
            league_name="NBA Fantasy League",
            total_teams=12,
            team_budget=200,
            min_bid_increment=1,
            max_players_per_team=15
        )
        
        if success:
            st.success("✅ 기본 설정으로 복원되었습니다!")
            st.rerun()
        else:
            st.error("❌ 기본값 복원에 실패했습니다.")
    
    # 현재 팀 상태 표시
    st.markdown("### 현재 팀 상태")
    current_teams = list(st.session_state.data_manager.teams.keys())
    
    # 팀을 3개씩 표시
    for row in range(0, len(current_teams), 3):
        cols = st.columns(3)
        for col_idx, team_name in enumerate(current_teams[row:row+3]):
            if col_idx < len(cols):
                with cols[col_idx]:
                    team_data = st.session_state.data_manager.teams[team_name]
                    
                    with st.container():
                        st.markdown(f"**{team_name}**")
                        st.write(f"💰 ${team_data.budget_left} 남음")
                        st.write(f"👥 {len(team_data.players)}명 드래프트")


def main():
    """메인 설정 페이지"""
    data_collection_section()
    st.divider()
    league_settings_section()

if __name__ == "__main__":
    main()