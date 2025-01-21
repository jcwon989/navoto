import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sqlite3
from datetime import datetime
import re
import shutil

# Pretendard 폰트 설정
from matplotlib import font_manager

font_path = "./font/Pretendard-Regular.ttf"
pretendard_font = font_manager.FontProperties(fname=font_path)
plt.rc('font', family=pretendard_font.get_name())
plt.rcParams['axes.unicode_minus'] = False

# SQLite 데이터베이스 초기화
def init_db():
    with sqlite3.connect('basketball_stats.db') as conn:
        c = conn.cursor()
        
        # 개인 기록 테이블
        c.execute('''CREATE TABLE IF NOT EXISTS player_stats
                     (game_date TEXT, team TEXT, player TEXT, 
                      player_number INTEGER,
                      points INTEGER, rebounds INTEGER, assists INTEGER,
                      steals INTEGER, blocks INTEGER, turnovers INTEGER,
                      two_points_made INTEGER, two_points_attempt INTEGER,
                      three_points_made INTEGER, three_points_attempt INTEGER,
                      free_throws_made INTEGER, free_throws_attempt INTEGER,
                      UNIQUE(game_date, team, player))''')
        
        # 팀 기록 테이블
        c.execute('''CREATE TABLE IF NOT EXISTS team_stats
                     (game_date TEXT, team TEXT, opponent TEXT,
                      q1_score INTEGER, q2_score INTEGER, q3_score INTEGER, q4_score INTEGER,
                      total_score INTEGER, field_goals_made INTEGER, field_goals_attempt INTEGER,
                      three_points_made INTEGER, three_points_attempt INTEGER,
                      free_throws_made INTEGER, free_throws_attempt INTEGER,
                      rebounds INTEGER, assists INTEGER, steals INTEGER,
                      blocks INTEGER, turnovers INTEGER,
                      UNIQUE(game_date, team))''')
        
        conn.commit()

def is_game_exists(game_date, team1, team2):
    with sqlite3.connect('basketball_stats.db') as conn:
        c = conn.cursor()
        c.execute('''SELECT 1 FROM player_stats 
                    WHERE game_date = ? AND (team = ? OR team = ?)''', 
                 (game_date, team1, team2))
        return c.fetchone() is not None

# 파일명에서 날짜와 팀명 추출
def extract_info_from_filename(filename):
    pattern = r'stats_(.+)_vs_(.+)_(\d{2})-(\d{1,2})-(\d{1,2})\.csv$'
    match = re.match(pattern, filename)
    if match:
        team1, team2, year_str, month_str, day_str = match.groups()
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

# CSV 파일에서 팀 데이터 추출
def extract_team_data(df):
    # 구분자로 팀 데이터 분리
    separator_indices = df.index[df.iloc[:, 0] == '-'].tolist()
    
    if len(separator_indices) != 1:
        raise ValueError("CSV 파일 형식이 올바르지 않습니다.")
    
    # 첫 번째 팀 데이터
    team1_data = df.iloc[:separator_indices[0]]
    # 두 번째 팀 데이터
    team2_data = df.iloc[separator_indices[0]+1:]
    
    # 각 팀의 선수 기록과 팀 전체 기록 분리
    team1_total = team1_data[team1_data['Player'] == 'Total'].iloc[0]
    team1_players = team1_data[team1_data['Player'] != 'Total']
    
    team2_total = team2_data[team2_data['Player'] == 'Total'].iloc[0]
    team2_players = team2_data[team2_data['Player'] != 'Total']
    
    return team1_players, team1_total, team2_players, team2_total

# 엑셀 데이터를 DB에 저장
def save_to_db(file_path, game_date, team1, team2):
    # 이미 저장된 경기인지 확인
    if is_game_exists(game_date, team1, team2):
        return False
        
    with sqlite3.connect('basketball_stats.db') as conn:
        # CSV 파일 읽기
        df = pd.read_csv(file_path)
        
        try:
            # 팀 데이터 추출
            team1_players, team1_total, team2_players, team2_total = extract_team_data(df)
            
            # 선수 기록 저장
            for team_name, players_df in [(team1, team1_players), (team2, team2_players)]:
                for _, row in players_df.iterrows():
                    player_data = {
                        'game_date': game_date,
                        'team': team_name,
                        'player': row['Player'],
                        'player_number': row.get('Nº', 0),
                        'points': row.get('PTS', 0),
                        'rebounds': row.get('REB', 0),
                        'assists': row.get('AST', 0),
                        'steals': row.get('STL', 0),
                        'blocks': row.get('BLK', 0),
                        'turnovers': row.get('TOV', 0),
                        'two_points_made': row.get('2PM', 0),
                        'two_points_attempt': row.get('2PA', 0),
                        'three_points_made': row.get('3PM', 0),
                        'three_points_attempt': row.get('3PA', 0),
                        'free_throws_made': row.get('FTM', 0),
                        'free_throws_attempt': row.get('FTA', 0)
                    }
                    
                    placeholders = ', '.join(['?'] * len(player_data))
                    columns = ', '.join(player_data.keys())
                    sql = f'INSERT OR REPLACE INTO player_stats ({columns}) VALUES ({placeholders})'
                    conn.execute(sql, list(player_data.values()))
            
            # 팀 기록 저장
            for team, opponent, total_row in [(team1, team2, team1_total), (team2, team1, team2_total)]:
                team_data = {
                    'game_date': game_date,
                    'team': team,
                    'opponent': opponent,
                    'q1_score': 0,  # CSV에는 쿼터별 점수가 없음
                    'q2_score': 0,
                    'q3_score': 0,
                    'q4_score': 0,
                    'total_score': total_row.get('PTS', 0),
                    'field_goals_made': total_row.get('2PM', 0) + total_row.get('3PM', 0),
                    'field_goals_attempt': total_row.get('2PA', 0) + total_row.get('3PA', 0),
                    'three_points_made': total_row.get('3PM', 0),
                    'three_points_attempt': total_row.get('3PA', 0),
                    'free_throws_made': total_row.get('FTM', 0),
                    'free_throws_attempt': total_row.get('FTA', 0),
                    'rebounds': total_row.get('REB', 0),
                    'assists': total_row.get('AST', 0),
                    'steals': total_row.get('STL', 0),
                    'blocks': total_row.get('BLK', 0),
                    'turnovers': total_row.get('TOV', 0)
                }
                
                placeholders = ', '.join(['?'] * len(team_data))
                columns = ', '.join(team_data.keys())
                sql = f'INSERT OR REPLACE INTO team_stats ({columns}) VALUES ({placeholders})'
                conn.execute(sql, list(team_data.values()))
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            raise e

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
        
        # 제목 설정
        # ax.set_title(f"{player_data['player']}의 개인 차트", fontproperties=pretendard_font, pad=15)
        
        # 그리드 스타일 설정
        ax.grid(True, linestyle='-', alpha=0.3)
        
        # 차트 표시
        st.pyplot(fig)
        plt.close(fig)  # 메모리 해제
        
    except Exception as e:
        st.error(f"차트 생성 중 오류가 발생했습니다: {str(e)}")

def get_player_stats(game_date, team, player):
    with sqlite3.connect('basketball_stats.db') as conn:
        query = '''SELECT * FROM player_stats 
                  WHERE game_date = ? AND team = ? AND player = ?'''
        df = pd.read_sql_query(query, conn, params=(game_date, team, player))
        return df.iloc[0] if not df.empty else None

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
        # 선택된 선수의 데이터를 DataFrame에서 직접 가져오기
        player_row = df[df['Player'] == selected_player].iloc[0]
        
        # DB에서 선수 데이터 가져오기
        player_stats = get_player_stats(game_date, team_name, selected_player)
        
        if player_stats is not None:
            # 선수 기록 표시
            col1, col2 = st.columns(2)
            
            with col1:
                # 선수 번호 가져오기 (DB에서)
                player_number = player_stats['player_number']
                st.write(f"**{player_number}번 {selected_player}의 기본 기록**")
                
                # 기본 기록을 데이터프레임으로 표시
                basic_stats = pd.DataFrame({
                    '항목': ['득점', '리바운드', '어시스트', '스틸', '블록', '턴오버'],
                    '기록': [
                        player_stats['points'],
                        player_stats['rebounds'],
                        player_stats['assists'],
                        player_stats['steals'],
                        player_stats['blocks'],
                        player_stats['turnovers']
                    ]
                })
                st.dataframe(basic_stats, hide_index=True)
            
            with col2:
                st.write("**슈팅 기록**")
                
                # 슈팅 기록 계산
                two_point_pct = f"{(player_stats['two_points_made']/player_stats['two_points_attempt']*100):.1f}%" if player_stats['two_points_attempt'] > 0 else "0.0%"
                three_point_pct = f"{(player_stats['three_points_made']/player_stats['three_points_attempt']*100):.1f}%" if player_stats['three_points_attempt'] > 0 else "0.0%"
                ft_pct = f"{(player_stats['free_throws_made']/player_stats['free_throws_attempt']*100):.1f}%" if player_stats['free_throws_attempt'] > 0 else "0.0%"
                
                # 슈팅 기록을 데이터프레임으로 표시
                shooting_stats = pd.DataFrame({
                    '구분': ['2점 슛', '3점 슛', '자유투'],
                    '성공/시도': [
                        f"{player_stats['two_points_made']}/{player_stats['two_points_attempt']}",
                        f"{player_stats['three_points_made']}/{player_stats['three_points_attempt']}",
                        f"{player_stats['free_throws_made']}/{player_stats['free_throws_attempt']}"
                    ],
                    '성공률': [two_point_pct, three_point_pct, ft_pct]
                })
                st.dataframe(shooting_stats, hide_index=True)
            
            # 레이더 차트 표시
            st.subheader(f"{player_number}번 {selected_player}의 레이더 차트")
            generate_radar_chart(player_stats)
        else:
            st.error(f"DB에서 {selected_player}의 기록을 찾을 수 없습니다. (game_date: {game_date}, team: {team_name})")

# 메인 앱
def main():
    # 데이터베이스 초기화
    init_db()
    
    # data 폴더가 없으면 생성
    if not os.path.exists("./data"):
        os.makedirs("./data")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("NOVATO 스탯 매니저")
    with col2:
        with st.popover("📊 업로드"):
            uploaded_file = st.file_uploader("경기 기록 파일 선택", type=['csv'])
            
            if uploaded_file:
                try:
                    # 파일을 data 폴더에 저장
                    file_path = os.path.join("./data", uploaded_file.name)
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    st.success(f"파일 '{uploaded_file.name}'이 성공적으로 저장되었습니다!")
                    
                    # 파일 처리
                    df = pd.read_csv(uploaded_file)
                    
                    # 파일명에서 정보 추출
                    game_date, team1, team2 = extract_info_from_filename(uploaded_file.name)
                    
                    if game_date and not is_game_exists(game_date, team1, team2):
                        with st.spinner("데이터를 저장하는 중..."):
                            if save_to_db(file_path, game_date, team1, team2):
                                st.success("새로운 경기 데이터가 저장되었습니다!")
                                st.rerun()
                    
                except Exception as e:
                    st.error(f"파일 처리 중 오류가 발생했습니다: {str(e)}")
    
    # 기존 파일 목록 표시
    files = [f for f in os.listdir("./data") if f.endswith('.csv')]
    
    if files:
        selected_file = st.selectbox(
            "경기를 선택하세요",
            options=files,
            format_func=lambda x: x
        )
        
        if selected_file:
            file_path = os.path.join("./data", selected_file)
            game_date, team1, team2 = extract_info_from_filename(selected_file)
            
            if game_date:
                # CSV 파일 읽기
                df = pd.read_csv(file_path)
                team1_players, team1_total, team2_players, team2_total = extract_team_data(df)
                
                # 제목에 경기 정보 표시
                game_date_formatted = datetime.strptime(game_date, '%Y-%m-%d').strftime('%Y년 %m월 %d일')
                st.title(f"{team1} vs {team2}")
                st.header(game_date_formatted, divider='red')
                
                # 팀 스탯 표시
                st.header("팀 스탯")
                stats_columns = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 
                               '2PM', '2PA', '3PM', '3PA', 'FTM', 'FTA']
                
                # 각 스탯의 승리 여부 (True: team1이 이김, False: team2가 이김)
                better_stats = {
                    'PTS': team1_total['PTS'] > team2_total['PTS'],  # 높은 게 좋음
                    'REB': team1_total['REB'] > team2_total['REB'],  # 높은 게 좋음
                    'AST': team1_total['AST'] > team2_total['AST'],  # 높은 게 좋음
                    'STL': team1_total['STL'] > team2_total['STL'],  # 높은 게 좋음
                    'BLK': team1_total['BLK'] > team2_total['BLK'],  # 높은 게 좋음
                    'TOV': team1_total['TOV'] < team2_total['TOV'],  # 낮은 게 좋음
                    '2PM': team1_total['2PM'] > team2_total['2PM'],  # 높은 게 좋음
                    '2PA': team1_total['2PA'] < team2_total['2PA'],  # 낮은 게 좋음
                    '3PM': team1_total['3PM'] > team2_total['3PM'],  # 높은 게 좋음
                    '3PA': team1_total['3PA'] < team2_total['3PA'],  # 낮은 게 좋음
                    'FTM': team1_total['FTM'] > team2_total['FTM'],  # 높은 게 좋음
                    'FTA': team1_total['FTA'] < team2_total['FTA']   # 낮은 게 좋음
                }
                
                team_stats_df = pd.DataFrame({
                    team1: [team1_total[col] for col in stats_columns],
                    '팀 스탯': ['득점', '리바운드', '어시스트', '스틸', '블록', '턴오버',
                             '2점 성공', '2점 시도', '3점 성공', '3점 시도', '자유투 성공', '자유투 시도'],
                    team2: [team2_total[col] for col in stats_columns]
                })
                
                # 스타일 적용
                def style_team1(val):
                    if pd.isna(val):
                        return ''
                    for i, stat in enumerate(stats_columns):
                        if val == team1_total[stat]:
                            return 'color: red' if better_stats[stat] else ''
                    return ''
                
                def style_team2(val):
                    if pd.isna(val):
                        return ''
                    for i, stat in enumerate(stats_columns):
                        if val == team2_total[stat]:
                            return 'color: red' if not better_stats[stat] else ''
                    return ''
                
                # 스타일 적용
                styled_df = team_stats_df.style.applymap(style_team1, subset=[team1]) \
                                              .applymap(style_team2, subset=[team2]) \
                                              .set_properties(**{'font-weight': 'bold'}, subset=['팀 스탯'])
                
                st.dataframe(styled_df, hide_index=True)
                
                # 선수 기록 표시
                st.header("선수 기록")
                tab1, tab2 = st.tabs([team1, team2])
                
                with tab1:
                    show_player_stats(team1_players, team1, game_date)
                    
                with tab2:
                    show_player_stats(team2_players, team2, game_date)
    else:
        st.info("저장된 경기 기록이 없습니다.")

if __name__ == "__main__":
    main()
