import streamlit as st
import pandas as pd
import sqlite3
import plotly.graph_objects as go
import plotly.express as px
from database import DB_PATH, get_player_career_stats

def get_league_players(league_id):
    """특정 리그에 참여한 모든 선수 목록 조회"""
    query = '''
    SELECT DISTINCT ps.player, ps.team
    FROM player_stats ps
    JOIN game_league gl ON ps.game_date = gl.game_date 
        AND (ps.team = gl.team1 OR ps.team = gl.team2)
    WHERE gl.league_id = ?
    ORDER BY ps.team, ps.player
    '''
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=(league_id,))

def get_player_teams(player_name, league_id):
    """특정 선수가 참여한 모든 팀 목록 조회"""
    query = '''
    SELECT DISTINCT ps.team
    FROM player_stats ps
    JOIN game_league gl ON ps.game_date = gl.game_date 
        AND (ps.team = gl.team1 OR ps.team = gl.team2)
    WHERE ps.player = ? AND gl.league_id = ?
    ORDER BY ps.team
    '''
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn, params=(player_name, league_id))
        return df['team'].tolist()

def get_player_games(player_name, league_id):
    """특정 선수의 모든 경기 목록 조회"""
    query = '''
    SELECT DISTINCT 
        ps.game_date,
        gl.team1,
        gl.team2,
        (SELECT total_score FROM team_stats WHERE game_date = gl.game_date AND team = gl.team1) as team1_score,
        (SELECT total_score FROM team_stats WHERE game_date = gl.game_date AND team = gl.team2) as team2_score
    FROM player_stats ps
    JOIN game_league gl ON ps.game_date = gl.game_date 
    WHERE ps.player = ? AND gl.league_id = ?
    ORDER BY ps.game_date DESC
    '''
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn, params=(player_name, league_id))
        df['game_name'] = df.apply(lambda x: f"{x['game_date']} {x['team1']} {x['team1_score']} vs {x['team2_score']} {x['team2']}", axis=1)
        return df

def get_player_game_stats(player_name, game_date):
    """특정 선수의 특정 경기 기록 조회"""
    query = '''
    SELECT *
    FROM player_stats
    WHERE player = ? AND game_date = ?
    '''
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn, params=(player_name, game_date)).iloc[0]

def create_radar_chart(stats, title):
    """레이더 차트 생성"""
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=list(stats.values()),
        theta=list(stats.keys()),
        fill='toself'
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        title=title,
        margin=dict(l=50, r=50, t=50, b=50),
        autosize=True
    )
    return fig

def create_trend_chart(games_stats, title):
    """트렌드 라인 차트 생성"""
    fig = go.Figure()
    
    stat_names = {
        'points': '득점',
        'rebounds': '리바운드',
        'assists': '어시스트'
    }
    
    for stat, name in stat_names.items():
        fig.add_trace(go.Scatter(
            x=games_stats['game_date'],
            y=games_stats[stat],
            name=name
        ))
    
    # 날짜 포맷 변환
    date_strings = games_stats['game_date'].dt.strftime('%m-%d').tolist()
    
    fig.update_layout(
        title=title,
        xaxis_title="경기 날짜",
        yaxis_title="기록",
        hovermode='x unified',
        xaxis=dict(
            tickmode='array',
            ticktext=date_strings,
            tickvals=games_stats['game_date'],
            tickangle=0,
            tickfont=dict(size=11)
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        autosize=True
    )
    return fig

def get_player_recent_games(player_name, league_id, limit=5):
    """최근 N경기 기록 조회"""
    query = '''
    SELECT 
        ps.game_date,
        ps.points,
        ps.rebounds,
        ps.assists,
        ps.steals,
        ps.blocks,
        ps.turnovers,
        ps.minutes,
        ps.two_points_made, ps.two_points_attempt,
        ps.three_points_made, ps.three_points_attempt,
        ps.free_throws_made, ps.free_throws_attempt
    FROM player_stats ps
    JOIN game_league gl ON ps.game_date = gl.game_date
    WHERE ps.player = ? AND gl.league_id = ?
    ORDER BY ps.game_date DESC
    LIMIT ?
    '''
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn, params=(player_name, league_id, limit))
        df['game_date'] = pd.to_datetime(df['game_date'])
        return df

def show_player_page():
    """선수 기록 페이지"""
    st.title("선수 기록 검색")
    
    if 'selected_league' not in st.session_state:
        st.info("먼저 경기 기록 탭에서 리그를 선택해주세요.")
        return
    
    selected_league = st.session_state.selected_league
    selected_league_name = st.session_state.selected_league_name
    
    st.write(f"선택된 리그: {selected_league_name}")
    
    players_df = get_league_players(selected_league)
    
    if not players_df.empty:
        selected_player = st.selectbox(
            "선수 선택",
            options=players_df['player'].tolist(),
            format_func=lambda x: f"{x} ({players_df[players_df['player'] == x]['team'].iloc[0]})"
        )
        
        if selected_player:
            team = players_df[players_df['player'] == selected_player]['team'].iloc[0]
            
            # 1. 선수 기본 정보
            st.header(f"🏀 {selected_player}")
            st.subheader(f"소속팀: {team}")
            
            # 2. 주요 기록 요약
            career_stats = get_player_career_stats(selected_player)
            if career_stats is not None:
                st.markdown("""
                <style>
                .stats-container {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 10px;
                    margin: 10px 0;
                    width: 100%;
                }
                .stat-box {
                    background-color: #f0f2f6;
                    border-radius: 8px;
                    padding: 12px 10px;
                    text-align: center;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                }
                .stat-label {
                    font-size: 0.9rem;
                    color: #555;
                    margin-bottom: 4px;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                .stat-value {
                    font-size: 1.2rem;
                    font-weight: bold;
                    color: #0f0f0f;
                    margin: 0;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                @media (max-width: 640px) {
                    .stat-box {
                        padding: 8px 4px;
                    }
                    .stat-label {
                        font-size: 0.8rem;
                    }
                    .stat-value {
                        font-size: 1rem;
                    }
                }
                </style>
                """, unsafe_allow_html=True)

                stats_html = f"""
                <div class="stats-container">
                    <div class="stat-box">
                        <p class="stat-label">출전시간</p>
                        <p class="stat-value">{career_stats['avg_minutes']:.1f}분</p>
                    </div>
                    <div class="stat-box">
                        <p class="stat-label">득점</p>
                        <p class="stat-value">{career_stats['avg_points']:.1f}점</p>
                    </div>
                    <div class="stat-box">
                        <p class="stat-label">리바운드</p>
                        <p class="stat-value">{career_stats['avg_rebounds']:.1f}개</p>
                    </div>
                    <div class="stat-box">
                        <p class="stat-label">어시스트</p>
                        <p class="stat-value">{career_stats['avg_assists']:.1f}개</p>
                    </div>
                    <div class="stat-box">
                        <p class="stat-label">스틸</p>
                        <p class="stat-value">{career_stats['avg_steals']:.1f}개</p>
                    </div>
                    <div class="stat-box">
                        <p class="stat-label">경기 수</p>
                        <p class="stat-value">{career_stats['games_played']}경기</p>
                    </div>
                </div>
                """
                st.markdown(stats_html, unsafe_allow_html=True)
            
            # 3. 차트 섹션
            col1, col2 = st.columns(2)
            
            with col1:
                # 슈팅 차트
                shooting_stats = {
                    '2점슛': (career_stats['total_2pm']/career_stats['total_2pa']*100 if career_stats['total_2pa'] > 0 else 0),
                    '3점슛': (career_stats['total_3pm']/career_stats['total_3pa']*100 if career_stats['total_3pa'] > 0 else 0),
                    '자유투': (career_stats['total_ftm']/career_stats['total_fta']*100 if career_stats['total_fta'] > 0 else 0)
                }
                st.plotly_chart(create_radar_chart(shooting_stats, "슈팅 성공률 (%)"), use_container_width=True)
            
            with col2:
                # 종합 기여도 차트
                contribution_stats = {
                    '득점': min(career_stats['avg_points'] * 4, 100),
                    '리바운드': min(career_stats['avg_rebounds'] * 10, 100),
                    '어시스트': min(career_stats['avg_assists'] * 10, 100),
                    '스틸': min(career_stats['avg_steals'] * 20, 100),
                    '블록': min(career_stats['avg_blocks'] * 20, 100),
                    '턴오버': min(100 - career_stats['avg_turnovers'] * 10, 100)
                }
                st.plotly_chart(create_radar_chart(contribution_stats, "종합 기여도"), use_container_width=True)
            
            # 4. 최근 경기 트렌드
            st.subheader("최근 경기 트렌드")
            recent_games = get_player_recent_games(selected_player, selected_league)
            if not recent_games.empty:
                st.markdown("""
                <style>
                .element-container:has([data-testid="stPlotlyChart"]) {
                    min-width: 300px !important;
                    max-width: 900px !important;
                    width: 100% !important;
                    margin: 0 auto !important;
                }
                </style>
                """, unsafe_allow_html=True)
                st.plotly_chart(create_trend_chart(recent_games, "최근 5경기 기록"), use_container_width=True)
            
            # 5. 상세 기록 테이블
            st.subheader("경기별 상세 기록")
            games_df = get_player_games(selected_player, selected_league)
            if not games_df.empty:
                for _, game in games_df.iterrows():
                    game_stats = get_player_game_stats(selected_player, game['game_date'])
                    with st.expander(f"{game['game_date']} {game['team1']} vs {game['team2']}"):
                        # 기본 기록과 슈팅 기록을 가로 방향 표로 표시
                        basic_stats = {
                            '득점': game_stats['points'],
                            '리바운드': game_stats['rebounds'],
                            '어시스트': game_stats['assists'],
                            '스틸': game_stats['steals'],
                            '블록': game_stats['blocks'],
                            '턴오버': game_stats['turnovers']
                        }
                        
                        shooting_stats = {
                            '2점슛': f"{game_stats['two_points_made']}/{game_stats['two_points_attempt']}",
                            '3점슛': f"{game_stats['three_points_made']}/{game_stats['three_points_attempt']}",
                            '자유투': f"{game_stats['free_throws_made']}/{game_stats['free_throws_attempt']}"
                        }
                        
                        # 가로 방향 표로 변환
                        basic_df = pd.DataFrame([basic_stats])
                        shooting_df = pd.DataFrame([shooting_stats])
                        
                        # CSS로 테이블 너비 제한 설정
                        st.markdown("""
                        <style>
                        .block-container {
                            max-width: 900px;
                            padding-left: 0;
                            padding-right: 0;
                            margin: 0 auto;
                        }
                        div[data-testid="stDataFrame"] {
                            width: 100% !important;
                        }
                        div.element-container:has([data-testid="stDataFrame"]) {
                            width: 100% !important;
                        }
                        [data-testid="stDataFrame"] table {
                            width: 100% !important;
                        }
                        </style>
                        """, unsafe_allow_html=True)
                        
                        st.write("기본 기록")
                        st.dataframe(basic_df, hide_index=True, use_container_width=True)
                        
                        st.write("슈팅 기록")
                        st.dataframe(shooting_df, hide_index=True, use_container_width=True)
                        
                        # 전체 기록 표
                        st.write("전체 기록")
                        
                        # 데이터를 세 줄로 나누어 표시
                        row1_stats = pd.DataFrame([{
                            '시간': f"{game_stats['minutes']}분",
                            '득점': game_stats['points'],
                            'FGM-A': f"{game_stats['field_goals_made']}-{game_stats['field_goals_attempt']}",
                            'FG%': f"{(game_stats['field_goals_made']/game_stats['field_goals_attempt']*100):.1f}%" if game_stats['field_goals_attempt'] > 0 else "0.0%",
                            '2PM-A': f"{game_stats['two_points_made']}-{game_stats['two_points_attempt']}",
                            '2P%': f"{(game_stats['two_points_made']/game_stats['two_points_attempt']*100):.1f}%" if game_stats['two_points_attempt'] > 0 else "0.0%"
                        }])

                        row2_stats = pd.DataFrame([{
                            '3PM-A': f"{game_stats['three_points_made']}-{game_stats['three_points_attempt']}",
                            '3P%': f"{(game_stats['three_points_made']/game_stats['three_points_attempt']*100):.1f}%" if game_stats['three_points_attempt'] > 0 else "0.0%",
                            'FTM-A': f"{game_stats['free_throws_made']}-{game_stats['free_throws_attempt']}",
                            'FT%': f"{(game_stats['free_throws_made']/game_stats['free_throws_attempt']*100):.1f}%" if game_stats['free_throws_attempt'] > 0 else "0.0%",
                            'REB': f"O/D {game_stats['offensive_rebounds']}/{game_stats['defensive_rebounds']} ({game_stats['rebounds']})",
                            'AST': game_stats['assists']
                        }])

                        row3_stats = pd.DataFrame([{
                            'STL': game_stats['steals'],
                            'BLK': game_stats['blocks'],
                            'TOV': game_stats['turnovers'],
                            'PF': game_stats['fouls'],
                            '+/-': game_stats['plus_minus'],
                            'EFF': game_stats['efficiency']
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
    else:
        st.info("선택한 리그에 등록된 선수가 없습니다.") 