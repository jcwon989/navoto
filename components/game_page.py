import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import (get_leagues, get_league_games, get_player_stats)

def show_player_stats(df, team_name, game_date):
    """선수 기록 표시 함수"""
    # 데이터프레임 표시
    st.dataframe(
        df,
        use_container_width=True,
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
    
    # 선수 선택을 위한 선택 박스
    st.subheader("선수 상세 기록")
    players = df['Player'].tolist()
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