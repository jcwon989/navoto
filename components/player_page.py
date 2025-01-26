import streamlit as st
import pandas as pd
import sqlite3
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

def show_player_page():
    """선수 기록 페이지"""
    st.title("선수 기록 검색")
    
    # session_state에서 선택된 리그 확인
    if 'selected_league' not in st.session_state:
        st.info("먼저 경기 기록 탭에서 리그를 선택해주세요.")
        return
    
    selected_league = st.session_state.selected_league
    selected_league_name = st.session_state.selected_league_name
    
    st.write(f"선택된 리그: {selected_league_name}")
    
    # 선수 목록 가져오기
    players_df = get_league_players(selected_league)
    
    if not players_df.empty:
            
        # 선수 선택
        selected_player = st.selectbox(
            "선수 선택",
                options=players_df['player'].tolist(),
            format_func=lambda x: f"{x} ({players_df[players_df['player'] == x]['team'].iloc[0]})"
        )
        
        if selected_player:
            # 경기 선택 (전체 + 경기 목록)
            games_df = get_player_games(selected_player, selected_league)
            game_options = ["전체"] + games_df['game_name'].tolist()
            selected_game = st.selectbox(
                "경기 선택",
                options=game_options,
                format_func=lambda x: "전체 경기" if x == "전체" else x
            )
            
            # 선수 기록 조회
            if selected_game == "전체":
                career_stats = get_player_career_stats(selected_player)
                display_title = f"{selected_player}의 통산 기록"
            else:
                game_date = games_df[games_df['game_name'] == selected_game]['game_date'].iloc[0]
                career_stats = get_player_game_stats(selected_player, game_date)
                display_title = f"{selected_player}의 경기 기록 ({selected_game})"
            
            if career_stats is not None:
                st.header(display_title)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.subheader("기본 기록")
                    basic_stats = pd.DataFrame({
                        '항목': ['경기수', '평균득점', '평균리바운드', '평균어시스트',
                               '평균스틸', '평균블록', '평균턴오버'],
                        '기록': [
                            str(career_stats['games_played']) if selected_game == "전체" else "1",
                            f"{career_stats['avg_points' if selected_game == '전체' else 'points']:.1f}",
                            f"{career_stats['avg_rebounds' if selected_game == '전체' else 'rebounds']:.1f}",
                            f"{career_stats['avg_assists' if selected_game == '전체' else 'assists']:.1f}",
                            f"{career_stats['avg_steals' if selected_game == '전체' else 'steals']:.1f}",
                            f"{career_stats['avg_blocks' if selected_game == '전체' else 'blocks']:.1f}",
                            f"{career_stats['avg_turnovers' if selected_game == '전체' else 'turnovers']:.1f}"
                        ]
                    }).astype({'항목': str, '기록': str})
                    st.dataframe(basic_stats, hide_index=True)
                
                with col2:
                    st.subheader("슈팅 기록")
                    if selected_game == "전체":
                        shooting_stats = pd.DataFrame({
                            '구분': ['2점슛', '3점슛', '자유투'],
                            '성공/시도': [
                                f"{career_stats['total_2pm']}/{career_stats['total_2pa']}",
                                f"{career_stats['total_3pm']}/{career_stats['total_3pa']}",
                                f"{career_stats['total_ftm']}/{career_stats['total_fta']}"
                            ],
                            '성공률': [
                                f"{(career_stats['total_2pm']/career_stats['total_2pa']*100 if career_stats['total_2pa'] > 0 else 0):.1f}%",
                                f"{(career_stats['total_3pm']/career_stats['total_3pa']*100 if career_stats['total_3pa'] > 0 else 0):.1f}%",
                                f"{(career_stats['total_ftm']/career_stats['total_fta']*100 if career_stats['total_fta'] > 0 else 0):.1f}%"
                            ]
                        })
                    else:
                        shooting_stats = pd.DataFrame({
                            '구분': ['2점슛', '3점슛', '자유투'],
                            '성공/시도': [
                                f"{career_stats['two_points_made']}/{career_stats['two_points_attempt']}",
                                f"{career_stats['three_points_made']}/{career_stats['three_points_attempt']}",
                                f"{career_stats['free_throws_made']}/{career_stats['free_throws_attempt']}"
                            ],
                            '성공률': [
                                f"{(career_stats['two_points_made']/career_stats['two_points_attempt']*100 if career_stats['two_points_attempt'] > 0 else 0):.1f}%",
                                f"{(career_stats['three_points_made']/career_stats['three_points_attempt']*100 if career_stats['three_points_attempt'] > 0 else 0):.1f}%",
                                f"{(career_stats['free_throws_made']/career_stats['free_throws_attempt']*100 if career_stats['free_throws_attempt'] > 0 else 0):.1f}%"
                            ]
                        })
                    st.dataframe(shooting_stats, hide_index=True)
        else:
            st.info("검색 결과가 없습니다.")
    else:
        st.info("선택한 리그에 등록된 선수가 없습니다.") 