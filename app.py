import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import sqlite3
from datetime import datetime
import re

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
        c.execute('''SELECT 1 FROM team_stats 
                    WHERE game_date = ? AND (team = ? OR team = ?)''', 
                 (game_date, team1, team2))
        return c.fetchone() is not None

# 파일명에서 날짜와 팀명 추출
def extract_info_from_filename(filename):
    pattern = r'stats_(.+)_vs_(.+)_(\d{2})-(\d{1,2})-(\d{1,2})\.xlsx$'
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

# 안전하게 정수값 가져오기
def safe_get_int(df, row_idx, col_idx, default=0):
    try:
        val = df.iloc[row_idx, col_idx]
        return int(val) if pd.notna(val) and isinstance(val, (int, float)) else default
    except (ValueError, TypeError, IndexError):
        return default

# 엑셀 데이터를 DB에 저장
def save_to_db(file_path, game_date, team1, team2):
    # 이미 저장된 경기인지 확인
    if is_game_exists(game_date, team1, team2):
        return False
        
    with sqlite3.connect('basketball_stats.db') as conn:
        # 엑셀 파일 읽기
        excel_file = pd.ExcelFile(file_path)
        
        # 시트 이름에서 팀명 추출
        team1_sheet = excel_file.sheet_names[0]  # 첫 번째 시트
        team2_sheet = excel_file.sheet_names[1]  # 두 번째 시트
        
        # "{팀명} Stats" 형식에서 팀명 추출
        team1_name = team1_sheet.replace(" Stats", "")
        team2_name = team2_sheet.replace(" Stats", "")
        
        # 팀1 선수 기록
        df_team1 = pd.read_excel(excel_file, sheet_name=0)
        # 팀2 선수 기록
        df_team2 = pd.read_excel(excel_file, sheet_name=1)
        # 팀 종합 기록
        df_team_total = pd.read_excel(excel_file, sheet_name=2)
        
        try:
            # 선수 기록 저장
            for team_name, df in [(team1_name, df_team1), (team2_name, df_team2)]:
                for _, row in df.iterrows():
                    player_data = {
                        'game_date': game_date,
                        'team': team_name,
                        'player': row['Player'],
                        'player_number': row.get('Nº', 0),  # 선수 번호 저장
                        'points': row.get('PTS', 0),
                        'rebounds': row.get('REB', 0),
                        'assists': row.get('AST', 0),
                        'steals': row.get('STL', 0),
                        'blocks': row.get('BLK', 0),
                        'turnovers': row.get('TO', 0),
                        'two_points_made': row.get('2PM', 0),
                        'two_points_attempt': row.get('2PA', 0),
                        'three_points_made': row.get('3PM', 0),
                        'three_points_attempt': row.get('3PA', 0),
                        'free_throws_made': row.get('FTM', 0),
                        'free_throws_attempt': row.get('FTA', 0)
                    }
                    
                    # SQL 쿼리 실행 (REPLACE 사용하여 중복 처리)
                    placeholders = ', '.join(['?'] * len(player_data))
                    columns = ', '.join(player_data.keys())
                    sql = f'INSERT OR REPLACE INTO player_stats ({columns}) VALUES ({placeholders})'
                    conn.execute(sql, list(player_data.values()))
            
            # 팀 기록 저장 (team1, team2는 파일명에서 추출한 값 사용)
            for team, opponent, team_idx in [(team1, team2, 0), (team2, team1, 1)]:
                scores = df_team_total.iloc[team_idx, 1:6]
                team_col = 1 if team_idx == 0 else 3
                
                team_data = {
                    'game_date': game_date,
                    'team': team,
                    'opponent': opponent,
                    'q1_score': safe_get_int(df_team_total, team_idx, 1),
                    'q2_score': safe_get_int(df_team_total, team_idx, 2),
                    'q3_score': safe_get_int(df_team_total, team_idx, 3),
                    'q4_score': safe_get_int(df_team_total, team_idx, 4),
                    'total_score': safe_get_int(df_team_total, team_idx, 5),
                    'field_goals_made': safe_get_int(df_team_total, 7, team_col),
                    'field_goals_attempt': safe_get_int(df_team_total, 8, team_col),
                    'three_points_made': safe_get_int(df_team_total, 9, team_col),
                    'three_points_attempt': safe_get_int(df_team_total, 10, team_col),
                    'free_throws_made': safe_get_int(df_team_total, 11, team_col),
                    'free_throws_attempt': safe_get_int(df_team_total, 12, team_col),
                    'rebounds': safe_get_int(df_team_total, 13, team_col),
                    'assists': safe_get_int(df_team_total, 14, team_col),
                    'steals': safe_get_int(df_team_total, 15, team_col),
                    'blocks': safe_get_int(df_team_total, 16, team_col),
                    'turnovers': safe_get_int(df_team_total, 17, team_col)
                }
                
                # SQL 쿼리 실행
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
                "Player",
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
    
    # 데이터 폴더에서 파일 목록 가져오기
    data_folder = "./data"
    files = [f for f in os.listdir(data_folder) if f.endswith('.xlsx')]
    
    # 사이드바에서 파일 선택
    st.sidebar.header("경기 선택")
    selected_file = st.sidebar.selectbox("경기를 선택하세요", files)
    
    if selected_file:
        file_path = os.path.join(data_folder, selected_file)
        game_date, team1, team2 = extract_info_from_filename(selected_file)
        
        if game_date is None:
            st.error("파일 이름에서 날짜를 추출할 수 없습니다.")
            return
            
        # 새로운 파일이면 DB에 저장
        if not is_game_exists(game_date, team1, team2):
            with st.spinner("데이터를 저장하는 중..."):
                if save_to_db(file_path, game_date, team1, team2):
                    st.success("새로운 경기 데이터가 저장되었습니다!")
        
        # 엑셀 파일 읽기
        excel_file = pd.ExcelFile(file_path)
        team1_name = excel_file.sheet_names[0].replace(" Stats", "")
        team2_name = excel_file.sheet_names[1].replace(" Stats", "")
        
        # 제목에 경기 정보 표시
        game_date_formatted = datetime.strptime(game_date, '%Y-%m-%d').strftime('%Y년 %m월 %d일')
        st.title(f"{team1_name} vs {team2_name} ({game_date_formatted})")
        
        df_team1 = pd.read_excel(file_path, sheet_name=0)
        df_team2 = pd.read_excel(file_path, sheet_name=1)
        df_team_total = pd.read_excel(file_path, sheet_name=2)
        
        # 스코어보드 표시 (첫 2행만)
        st.header("스코어보드")
        score_df = df_team_total.iloc[0:2, :]
        st.dataframe(score_df, hide_index=True)
        
        # 팀 스탯 표시
        st.header("팀 스탯")
        # 팀 스탯 데이터 가져오기 (B열이 기록 이름)
        stats_names = df_team_total.iloc[6:29, 1]  # B7:B29 (기록 이름)
        team1_stats = df_team_total.iloc[6:29, 0]  # A7:A29 (팀1 데이터)
        team2_stats = df_team_total.iloc[6:29, 2]  # C7:C29 (팀2 데이터)
        
        # 데이터프레임 생성 (기록 열을 가운데로)
        team_stats_df = pd.DataFrame({
            str(team1_name): team1_stats.values,
            '팀 스탯': stats_names.values,
            str(team2_name): team2_stats.values
        })
        
        # 열 순서 변경
        team_stats_df = team_stats_df[[str(team1_name), '팀 스탯', str(team2_name)]]
        
        # 가운데 열의 글자를 두껍게 표시
        st.dataframe(
            team_stats_df.style.set_properties(**{'font-weight': 'bold'}, subset=['팀 스탯']),
            hide_index=True
        )
        
        # 선수 기록 표시
        st.header("선수 기록")
        tab1, tab2 = st.tabs([str(team1_name), str(team2_name)])
        
        with tab1:
            show_player_stats(df_team1, team1_name, game_date)
            
        with tab2:
            show_player_stats(df_team2, team2_name, game_date)

if __name__ == "__main__":
    main()
