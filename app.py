import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sqlite3
from datetime import datetime
import re
from data_loader import load_game_data
from database import (init_db, is_game_exists, save_game_data, get_player_stats,
                     create_league, get_leagues, assign_game_to_league, get_league_games,
                     get_player_career_stats, DB_PATH)
from components.player_page import show_player_page
import plotly.graph_objects as go

# 페이지 설정을 가장 먼저 호출
st.set_page_config(
    page_title="농구 기록 관리",
    layout="wide"
)

# Pretendard 폰트 설정
from matplotlib import font_manager

font_path = "./font/Pretendard-Regular.ttf"
pretendard_font = font_manager.FontProperties(fname=font_path)
plt.rc('font', family=pretendard_font.get_name())
plt.rcParams['axes.unicode_minus'] = False

# CSS 스타일 정의
st.markdown("""
<style>
    /* 상단 여백 제거 */
    .block-container {
        padding-top: 0;
        margin-top: 0;
        padding-left: 5rem !important;
        padding-right: 5rem !important;
    }
    
    /* 헤더 여백 제거 */
    header {
        margin-top: -2rem;
    }
    
    /* 모바일 화면에서는 패딩 축소 */
    @media (max-width: 640px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }
    
    /* 기존 스타일 유지 */
    .top-area {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        border: 1px solid #e0e0e0;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 4rem;
    }
</style>
""", unsafe_allow_html=True)

# 파일명에서 날짜와 팀명 추출
def extract_info_from_filename(filename):
    pattern = r'stats_(.+)_vs_(.+)_(\d{2})-(\d{1,2})-(\d{1,2})\.(csv|xls|xlsx)$'
    match = re.match(pattern, filename)
    if match:
        team1, team2, year_str, month_str, day_str, _ = match.groups()
        # YY를 YYYY로 변환
        year = int(year_str)
        full_year = 2000 + year if year < 50 else 1900 + year
        # 월과 일을 2자리로 포맷팅
        month = int(month_str)
        day = int(day_str)
        date = f"{full_year}-{month:02d}-{day:02d}"
        return date, team1, team2
    
    st.error("파일명이 예상 형식과 일치하지 않습니다.")
    return None, None, None

# Helper function: Generate radar chart
def generate_radar_chart(player_data):
    # 2P%, 3P% 계산
    try:
        two_point_pct = (float(player_data['two_points_made']) / float(player_data['two_points_attempt']) * 100) if float(player_data['two_points_attempt']) > 0 else 0
        three_point_pct = (float(player_data['three_points_made']) / float(player_data['three_points_attempt']) * 100) if float(player_data['three_points_attempt']) > 0 else 0
        
        radar_stats = {
            "2점 성공률": two_point_pct / 70,  # Normalize: Max 70%
            "3점 성공률": three_point_pct / 50,  # Normalize: Max 50%
            "리바운드": float(player_data["rebounds"]) / 20,  # Normalize: Max 20
            "스틸": float(player_data["steals"]) / 5,  # Normalize: Max 5
            "어시스트": float(player_data["assists"]) / 15,  # Normalize: Max 15
        }
        
        # 각도 계산
        stats = list(radar_stats.keys())
        angles = np.linspace(0, 2 * np.pi, len(stats), endpoint=False).tolist()
        angles += angles[:1]  # 첫 번째 각도를 마지막에 추가하여 폐곡선 생성
        
        # 값 조정 (0.1에서 1.0 사이로)
        offset = 0.1
        values = list(radar_stats.values())
        values = [max(min(v, 1.0), 0.0) for v in values]  # 0~1 사이로 클리핑
        values = [offset + v * (1 - offset) for v in values]  # offset 적용
        values += values[:1]  # 첫 번째 값을 마지막에 추가
        
        # 차트 생성
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(polar=True))
        
        # 배경 그리드 설정
        ax.set_ylim(0, 1)
        yticks = [offset + i * (1-offset)/5 for i in range(6)]  # offset을 고려한 눈금 위치
        ax.set_yticks(yticks)
        ax.set_yticklabels(['0%', '20%', '40%', '60%', '80%', '100%'],
                          fontproperties=pretendard_font)
        
        # 데이터 플롯
        ax.fill(angles, values, color='blue', alpha=0.25)
        ax.plot(angles, values, color='blue', linewidth=2)
        
        # 축 레이블 설정
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(stats, fontproperties=pretendard_font)
        
        # 그리드 스타일 설정
        ax.grid(True, linestyle='-', alpha=0.3)
        
        # 차트 표시
        st.pyplot(fig)
        plt.close(fig)  # 메모리 해제
        
    except Exception as e:
        st.error(f"차트 생성 중 오류가 발생했습니다: {str(e)}")

# 선수 기록 표시 함수
def show_player_stats(df, team_name, game_date):
    # 선수 번호와 이름 열을 고정하고 나머지는 스크롤되게 설정
    df_display = df.copy()  # 데이터프레임 복사
    
    # 데이터프레임 표시
    st.dataframe(
        df_display,
        use_container_width=True,  # 컨테이너 너비에 맞춤
        column_config={
            "Nº": st.column_config.NumberColumn(
                "Nº",
                help="선수 번호",
                width=50,
                format="%d",
            ),
            "Player": st.column_config.TextColumn(
                "선수 이름",
                help="선수 이름",
                width=80,
            ),
        },
        hide_index=True,
    )
    
    # 선수 선택을 위한 선택 박스 (데이터프레임 아래에 배치)
    st.subheader("선수 상세 기록")
    players = df_display['Player'].tolist()
    selected_player = st.selectbox("선수를 선택하세요", players, key=f"player_select_{team_name}")
    
    # 선수가 선택되면 레이더 차트와 상세 기록 표시
    if selected_player:
        # DB에서 선수 데이터 가져오기
        player_stats = get_player_stats(game_date, team_name, selected_player)
        
        if player_stats is not None:
            st.write(f"### {selected_player} 상세 기록")
            
            # 선수 기록 표시
            st.write("선수 기록")
            
            # 데이터를 세 줄로 나누어 표시
            row1_stats = pd.DataFrame([{
                '시간': f"{player_stats['minutes']}분",
                '득점': player_stats['points'],
                'FGM-A': f"{player_stats['field_goals_made']}-{player_stats['field_goals_attempt']}",
                'FG%': f"{(player_stats['field_goals_made']/player_stats['field_goals_attempt']*100):.1f}%" if player_stats['field_goals_attempt'] > 0 else "0.0%",
                '2PM-A': f"{player_stats['two_points_made']}-{player_stats['two_points_attempt']}",
                '2P%': f"{(player_stats['two_points_made']/player_stats['two_points_attempt']*100):.1f}%" if player_stats['two_points_attempt'] > 0 else "0.0%"
            }])

            row2_stats = pd.DataFrame([{
                '3PM-A': f"{player_stats['three_points_made']}-{player_stats['three_points_attempt']}",
                '3P%': f"{(player_stats['three_points_made']/player_stats['three_points_attempt']*100):.1f}%" if player_stats['three_points_attempt'] > 0 else "0.0%",
                'FTM-A': f"{player_stats['free_throws_made']}-{player_stats['free_throws_attempt']}",
                'FT%': f"{(player_stats['free_throws_made']/player_stats['free_throws_attempt']*100):.1f}%" if player_stats['free_throws_attempt'] > 0 else "0.0%",
                'REB': f"O/D {player_stats['offensive_rebounds']}/{player_stats['defensive_rebounds']} ({player_stats['rebounds']})",
                'AST': player_stats['assists']
            }])

            row3_stats = pd.DataFrame([{
                'STL': player_stats['steals'],
                'BLK': player_stats['blocks'],
                'TOV': player_stats['turnovers'],
                'PF': player_stats['fouls'],
                '+/-': player_stats['plus_minus'],
                'EFF': player_stats['efficiency']
            }])

            # 열 설정
            def get_column_config(df):
                config = {}
                for col in df.columns:
                    if col in ['시간', 'FG%', '2P%', '3P%', 'FT%', 'FGM-A', '2PM-A', '3PM-A', 'FTM-A', 'REB']:
                        config[col] = st.column_config.TextColumn(
                            col,
                            help=f"{col} 기록",
                            width="small"
                        )
                    else:
                        config[col] = st.column_config.NumberColumn(
                            col,
                            help=f"{col} 기록",
                            width="small"
                        )
                return config

            # CSS로 자동 줄바꿈 설정
            st.markdown("""
            <style>
            [data-testid="stDataFrame"] table {
                white-space: normal !important;
            }
            [data-testid="stDataFrame"] td {
                white-space: normal !important;
                min-width: 50px !important;
                max-width: 100px !important;
                overflow-wrap: break-word !important;
                word-wrap: break-word !important;
            }
            </style>
            """, unsafe_allow_html=True)

            # 각 행 표시
            st.dataframe(row1_stats, hide_index=True, column_config=get_column_config(row1_stats), use_container_width=True)
            st.dataframe(row2_stats, hide_index=True, column_config=get_column_config(row2_stats), use_container_width=True)
            st.dataframe(row3_stats, hide_index=True, column_config=get_column_config(row3_stats), use_container_width=True)
            
            # 레이더 차트
            col1, col2 = st.columns(2)
            
            with col1:
                # 슈팅 차트
                shooting_percentages = {
                    '2점슛': (player_stats['two_points_made']/player_stats['two_points_attempt']*100 if player_stats['two_points_attempt'] > 0 else 0),
                    '3점슛': (player_stats['three_points_made']/player_stats['three_points_attempt']*100 if player_stats['three_points_attempt'] > 0 else 0),
                    '자유투': (player_stats['free_throws_made']/player_stats['free_throws_attempt']*100 if player_stats['free_throws_attempt'] > 0 else 0)
                }
                fig1 = go.Figure()
                fig1.add_trace(go.Scatterpolar(
                    r=list(shooting_percentages.values()),
                    theta=list(shooting_percentages.keys()),
                    fill='toself'
                ))
                fig1.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=False,
                    title="슈팅 성공률 (%)",
                    width=350,
                    height=350,
                    margin=dict(l=50, r=50, t=50, b=50),
                    autosize=False
                )
                st.plotly_chart(fig1)
            
            with col2:
                # 종합 기여도 차트
                contribution_stats = {
                    '득점': min(player_stats['points'] * 4, 100),
                    '리바운드': min(player_stats['rebounds'] * 10, 100),
                    '어시스트': min(player_stats['assists'] * 10, 100),
                    '스틸': min(player_stats['steals'] * 20, 100),
                    '블록': min(player_stats['blocks'] * 20, 100),
                    '턴오버': min(100 - player_stats['turnovers'] * 10, 100)
                }
                fig2 = go.Figure()
                fig2.add_trace(go.Scatterpolar(
                    r=list(contribution_stats.values()),
                    theta=list(contribution_stats.keys()),
                    fill='toself'
                ))
                fig2.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
                    showlegend=False,
                    title="종합 기여도",
                    width=350,
                    height=350,
                    margin=dict(l=50, r=50, t=50, b=50),
                    autosize=False
                )
                st.plotly_chart(fig2)
        else:
            st.error(f"DB에서 {selected_player}의 기록을 찾을 수 없습니다. (game_date: {game_date}, team: {team_name})")

def show_game_page():
    """경기 기록 페이지"""
    st.title("NOVATO 스탯 매니저")
    
    # 리그 선택
    leagues_df = get_leagues()
    if not leagues_df.empty:
        selected_league = st.selectbox(
            "리그 선택",
            options=leagues_df['league_id'].tolist(),
            format_func=lambda x: leagues_df[leagues_df['league_id'] == x]['league_name'].iloc[0]
        )
        # 선택된 리그를 session_state에 저장
        st.session_state.selected_league = selected_league
        st.session_state.selected_league_name = leagues_df[leagues_df['league_id'] == selected_league]['league_name'].iloc[0]
        
        # 선택된 리그의 경기 목록
        games_df = get_league_games(selected_league)
        if not games_df.empty:
            selected_idx = st.selectbox(
                "경기 선택",
                options=games_df.index,
                format_func=lambda x: f"{games_df.loc[x, 'game_date']} - {games_df.loc[x, 'team1']} vs {games_df.loc[x, 'team2']}"
            )
            
            # 경기 상세 정보 표시
            if selected_idx is not None:
                selected_game = games_df.loc[selected_idx]
                game_date = selected_game['game_date']
                team1 = selected_game['team1']
                team2 = selected_game['team2']
                
                st.write(f"### {team1} vs {team2} ({game_date})")
                
                # 스코어보드 표시
                st.write("#### 스코어보드")
                score_df = pd.DataFrame({
                    '팀': [team1, team2],
                    '1Q': [selected_game['team1_q1'], selected_game['team2_q1']],
                    '2Q': [selected_game['team1_q2'], selected_game['team2_q2']],
                    '3Q': [selected_game['team1_q3'], selected_game['team2_q3']],
                    '4Q': [selected_game['team1_q4'], selected_game['team2_q4']],
                    '총점': [selected_game['team1_points'], selected_game['team2_points']]
                })
                st.dataframe(score_df, hide_index=True, use_container_width=True)
                
                # 팀별 통계 표시
                st.write("#### 팀 스탯")
                team_stats_df = pd.DataFrame({
                    '팀': [team1, team2],
                    'PTS': [selected_game['team1_points'], selected_game['team2_points']],
                    '2PM': [selected_game['team1_2PM'], selected_game['team2_2PM']],
                    '2PA': [selected_game['team1_2PA'], selected_game['team2_2PA']],
                    '2P%': [selected_game['team1_2P_PCT'], selected_game['team2_2P_PCT']],
                    '3PM': [selected_game['team1_3PM'], selected_game['team2_3PM']],
                    '3PA': [selected_game['team1_3PA'], selected_game['team2_3PA']],
                    '3P%': [selected_game['team1_3P_PCT'], selected_game['team2_3P_PCT']],
                    'FTM': [selected_game['team1_FTM'], selected_game['team2_FTM']],
                    'FTA': [selected_game['team1_FTA'], selected_game['team2_FTA']],
                    'FT%': [selected_game['team1_FT_PCT'], selected_game['team2_FT_PCT']],
                    'REB': [selected_game['team1_rebounds'], selected_game['team2_rebounds']],
                    'AST': [selected_game['team1_assists'], selected_game['team2_assists']],
                    'STL': [selected_game['team1_steals'], selected_game['team2_steals']],
                    'BLK': [selected_game['team1_blocks'], selected_game['team2_blocks']],
                    'TOV': [selected_game['team1_turnovers'], selected_game['team2_turnovers']]
                })
                st.dataframe(team_stats_df, hide_index=True)
                
                # 선수 기록 표시
                st.header("선수 기록")
                tab1, tab2 = st.tabs([team1, team2])
                
                with tab1:
                    show_player_stats(selected_game['team1_players'], team1, game_date)
                    
                with tab2:
                    show_player_stats(selected_game['team2_players'], team2, game_date)
            else:
                st.info("저장된 경기 기록이 없습니다.")
        else:
            st.info("선택한 리그에 등록된 경기가 없습니다.")
    else:
        st.info("등록된 리그가 없습니다. 먼저 리그를 등록해주세요.")

def show_upload_page():
    """업로드 페이지"""
    st.title("데이터 업로드")
    
    # 리그 등록
    with st.expander("리그 등록", expanded=False):
        league_name = st.text_input("리그 이름")
        if st.button("리그 생성"):
            if league_name:
                if create_league(league_name):
                    st.success(f"리그가 생성되었습니다. - {league_name}")
                    st.rerun()
                else:
                    st.error("이미 존재하는 리그 이름입니다.")
            else:
                st.warning("리그 이름을 입력해주세요.")
    
    # 경기 기록 업로드
    with st.expander("경기 기록 업로드", expanded=False):
        # 리그 선택
        leagues_df = get_leagues()
        if not leagues_df.empty:
            selected_league = st.selectbox(
                "리그 선택",
                options=leagues_df['league_id'].tolist(),
                format_func=lambda x: leagues_df[leagues_df['league_id'] == x]['league_name'].iloc[0],
                key="upload_league_select"
            )
            
            uploaded_file = st.file_uploader("경기 기록 파일 선택", type=['csv', 'xls', 'xlsx'])
            
            if uploaded_file:
                try:
                    # 파일을 data 폴더에 저장
                    file_path = os.path.join("./data", uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    st.success(f"파일 '{uploaded_file.name}'이 성공적으로 저장되었습니다!")
                    
                    # 파일명에서 정보 추출
                    game_date, team1, team2 = extract_info_from_filename(uploaded_file.name)
                    st.write(f"추출된 정보: 날짜={game_date}, 팀1={team1}, 팀2={team2}")
                    
                    if game_date:
                        exists = is_game_exists(game_date, team1, team2)
                        st.write(f"경기 존재 여부: {exists}")
                        
                        if not exists:
                            with st.spinner("데이터를 저장하는 중..."):
                                try:
                                    # 데이터 로더를 사용하여 파일 읽기
                                    team1_players, team1_total, team2_players, team2_total = load_game_data(file_path)
                                    st.write("파일 읽기 성공")
                                    st.write(f"팀1 선수 수: {len(team1_players)}")
                                    st.write(f"팀2 선수 수: {len(team2_players)}")
                                    
                                    # DB에 저장
                                    if save_game_data(game_date, team1, team2, team1_players, team1_total, team2_players, team2_total):
                                        # 리그에 경기 할당
                                        assign_game_to_league(game_date, team1, team2, selected_league)
                                        st.success("새로운 경기 데이터가 저장되었습니다!")
                                        st.rerun()
                                    else:
                                        st.error("데이터 저장에 실패했습니다.")
                                except Exception as e:
                                    st.error(f"데이터 처리 중 오류 발생: {str(e)}")
                        else:
                            st.warning("이미 저장된 경기입니다.")
                    else:
                        st.error("파일명에서 정보를 추출할 수 없습니다.")
                    
                except Exception as e:
                    st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
        else:
            st.info("먼저 리그를 등록해주세요.")

def main():
    # data 폴더가 없으면 생성
    os.makedirs("./data", exist_ok=True)
    os.makedirs("./pages", exist_ok=True)  # pages 폴더도 생성
    
    # 데이터베이스 초기화 (앱 시작 시 한 번만)
    if 'db_initialized' not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    # 탭 메뉴
    tab1, tab2, tab3 = st.tabs(["경기 기록", "선수 기록", "업로드"])
    
    with tab1:
        show_game_page()
    with tab2:
        show_player_page()
    with tab3:
        show_upload_page()

if __name__ == "__main__":
    main()
