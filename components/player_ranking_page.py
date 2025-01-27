import streamlit as st
import pandas as pd
from database import get_leagues, get_player_rankings

def show_player_ranking_page():
    """개인 순위 페이지"""
    st.title("개인 순위")
    
    # 리그 선택
    leagues_df = get_leagues()
    if leagues_df.empty:
        st.info("등록된 리그가 없습니다.")
        return
        
    selected_league = st.selectbox(
        "리그 선택",
        leagues_df['league_id'].tolist(),
        format_func=lambda x: leagues_df[leagues_df['league_id'] == x]['league_name'].iloc[0],
        key="player_ranking_league_select"
    )
    
    # 통계 항목과 컬럼명 매핑
    stat_mapping = {
        "득점": "points",
        "리바운드": "rebounds",
        "어시스트": "assists",
        "스틸": "steals",
        "블록": "blocks",
        "3점슛": "three_points",
        "자유투": "free_throws",
        "효율값": "efficiency"
    }
    
    if selected_league:
        # 순위 기준 선택
        selected_stat = st.selectbox(
            "순위 기준",
            list(stat_mapping.keys()),
            key="player_ranking_stat_select"
        )
            
        rankings_df = get_player_rankings(selected_league, stat_mapping[selected_stat])
        if not rankings_df.empty:
            # 주석 추가 (우측 정렬)
            st.markdown('<div style="text-align: right; font-size: 0.8em; color: gray; margin-bottom: 5px;">* 평균(총합)</div>', unsafe_allow_html=True)
            
            st.dataframe(
                rankings_df,
                column_config={
                    "순위": st.column_config.NumberColumn(
                        "순위",
                        help="순위",
                        format="%d",
                        width=None
                    ),
                    "선수명": st.column_config.TextColumn(
                        "선수명",
                        width=None
                    ),
                    "팀명": st.column_config.TextColumn(
                        "팀명",
                        width=None
                    ),
                    "경기수": st.column_config.NumberColumn(
                        "경기수",
                        help="출전 경기 수",
                        format="%d",
                        width=None
                    ),
                    "출전시간": st.column_config.TextColumn(
                        "출전시간",
                        help="평균 출전시간",
                        width=None
                    ),
                    "득점": st.column_config.TextColumn(
                        "득점",
                        help="평균 (총합)",
                        width=None
                    ),
                    "리바운드": st.column_config.TextColumn(
                        "리바운드",
                        help="평균 (총합)",
                        width=None
                    ),
                    "어시스트": st.column_config.TextColumn(
                        "어시스트",
                        help="평균 (총합)",
                        width=None
                    ),
                    "스틸": st.column_config.TextColumn(
                        "스틸",
                        help="평균 (총합)",
                        width=None
                    ),
                    "블록": st.column_config.TextColumn(
                        "블록",
                        help="평균 (총합)",
                        width=None
                    ),
                    "3점슛": st.column_config.TextColumn(
                        "3점슛",
                        help="평균 (총합)",
                        width=None
                    ),
                    "자유투": st.column_config.TextColumn(
                        "자유투",
                        help="평균 (총합)",
                        width=None
                    ),
                    "효율값": st.column_config.TextColumn(
                        "효율값",
                        help="평균 (총합)",
                        width=None
                    )
                },
                hide_index=True,
                use_container_width=True,
                height=600  # 20명이 모두 표시되도록 높이 조정
            )
        else:
            st.info("해당 리그의 선수 기록이 없습니다.") 