"""
NBA 팀 정보 수동 업데이트 유틸리티
최신 트레이드나 이적 정보를 수동으로 관리
"""

def get_2024_25_season_updates():
    """
    2024-25 시즌 중 발생한 트레이드/이적 정보
    확인된 정보만 포함
    """
    return {
        # 형식: '선수 이름': '새 팀 약자'
        
        # NBA API 실시간 로스터 시스템으로 대체됨
        # 수동 업데이트는 더 이상 필요하지 않음
        
        # 다른 확인된 트레이드들을 여기에 추가
        # 예: 'Russell Westbrook': 'DEN'
    }

def get_recent_signings():
    """
    최근 FA 계약이나 10-day contract 등
    """
    return {
        # 형식: '선수 이름': '팀 약자'
        # 예: 'Russell Westbrook': 'DEN'
    }

def get_injured_reserve():
    """
    시즌 아웃 부상자 리스트
    이들은 드래프트에서 제외하거나 별도 표시 필요
    """
    return {
        # 형식: '선수 이름': '부상 상태'
        # 예: 'Kawhi Leonard': 'Season Ending Injury'
    }

def apply_team_updates(df, updates_dict, column_name='team'):
    """
    DataFrame에 팀 업데이트 적용
    """
    updates_applied = 0
    
    for player_name, new_value in updates_dict.items():
        mask = df['name'].str.contains(player_name, case=False, na=False)
        if mask.any():
            old_value = df.loc[mask, column_name].iloc[0] if mask.any() else 'N/A'
            df.loc[mask, column_name] = new_value
            print(f"업데이트: {player_name} {old_value} → {new_value}")
            updates_applied += 1
    
    return df, updates_applied