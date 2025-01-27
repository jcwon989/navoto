import streamlit as st
import pandas as pd
from database import get_leagues, get_team_rankings

def show_team_ranking_page():
    """팀 순위 페이지"""
    st.title("팀 순위")
    
    # 리그 선택
    leagues_df = get_leagues()
    if leagues_df.empty:
        st.info("등록된 리그가 없습니다.")
        return
        
    selected_league = st.selectbox(
        "리그 선택",
        leagues_df['league_id'].tolist(),
        format_func=lambda x: leagues_df[leagues_df['league_id'] == x]['league_name'].iloc[0],
        key="team_ranking_league_select"  # 고유한 key 추가
    )
    
    # 팀 순위 표시
    if selected_league:
        rankings_df = get_team_rankings(selected_league)
        if not rankings_df.empty:
            st.dataframe(
                rankings_df,
                column_config={
                    "순위": st.column_config.NumberColumn(
                        "순위",
                        help="순위",
                        format="%d",
                        width="small"
                    ),
                    "팀명": st.column_config.TextColumn(
                        "팀명",
                        width="medium"
                    ),
                    "경기수": st.column_config.NumberColumn(
                        "경기수",
                        help="총 경기 수",
                        format="%d",
                        width="small"
                    ),
                    "승": st.column_config.NumberColumn(
                        "승",
                        help="승리",
                        format="%d",
                        width="small"
                    ),
                    "패": st.column_config.NumberColumn(
                        "패",
                        help="패배",
                        format="%d",
                        width="small"
                    ),
                    "승률": st.column_config.NumberColumn(
                        "승률",
                        help="승률",
                        format="%.3f",
                        width="small"
                    ),
                    "득점": st.column_config.NumberColumn(
                        "득점",
                        help="평균 득점",
                        format="%.1f",
                        width="small"
                    ),
                    "실점": st.column_config.NumberColumn(
                        "실점",
                        help="평균 실점",
                        format="%.1f",
                        width="small"
                    ),
                    "득실차": st.column_config.NumberColumn(
                        "득실차",
                        help="평균 득실차",
                        format="%.1f",
                        width="small"
                    ),
                    "연속": st.column_config.TextColumn(
                        "연속",
                        help="최근 5경기",
                        width="small"
                    )
                },
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("해당 리그의 경기 기록이 없습니다.") 