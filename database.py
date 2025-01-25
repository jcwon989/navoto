import sqlite3
import pandas as pd
from datetime import datetime
import os
import time

# DB 파일 경로 설정
DB_PATH = os.path.join('./data', 'basketball_stats.db')

def get_db_connection():
    """데이터베이스 연결을 생성하고 반환"""
    # 데이터베이스 파일이 있는 디렉토리 확인 및 생성
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 연결 시도 (timeout 증가 및 isolation_level 설정)
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging 모드 사용
    conn.execute("PRAGMA busy_timeout=30000")  # busy timeout 설정 (30초)
    return conn

def execute_with_retry(func, max_retries=5):
    """락 문제 발생 시 재시도하는 래퍼 함수"""
    last_error = None
    for attempt in range(max_retries):
        try:
            return func()
        except sqlite3.OperationalError as e:
            last_error = e
            if "database is locked" in str(e) and attempt < max_retries - 1:
                print(f"데이터베이스 락 감지, {attempt + 1}번째 재시도...")
                time.sleep(2)  # 대기 시간 증가
                continue
            raise
        except Exception as e:
            raise e
    
    if last_error:
        raise last_error

def init_db():
    """데이터베이스 초기화 및 테이블 생성"""
    def _init():
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # 테이블 생성 (이미 있으면 건너뜀)
            c.execute('''CREATE TABLE IF NOT EXISTS player_stats
                         (game_date TEXT, team TEXT, player TEXT, 
                          player_number INTEGER,
                          minutes TEXT,
                          points INTEGER,
                          two_points_made INTEGER, two_points_attempt INTEGER, two_point_percentage REAL,
                          three_points_made INTEGER, three_points_attempt INTEGER, three_point_percentage REAL,
                          field_goals_made INTEGER, field_goals_attempt INTEGER, field_goal_percentage REAL,
                          free_throws_made INTEGER, free_throws_attempt INTEGER, free_throw_percentage REAL,
                          offensive_rebounds INTEGER,
                          defensive_rebounds INTEGER,
                          rebounds INTEGER,
                          assists INTEGER,
                          turnovers INTEGER,
                          steals INTEGER,
                          blocks INTEGER,
                          fouls INTEGER,
                          plus_minus INTEGER,
                          efficiency REAL,
                          UNIQUE(game_date, team, player))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS team_stats
                         (game_date TEXT, team TEXT, opponent TEXT,
                          q1_score INTEGER DEFAULT 0,
                          q2_score INTEGER DEFAULT 0,
                          q3_score INTEGER DEFAULT 0,
                          q4_score INTEGER DEFAULT 0,
                          total_score INTEGER,
                          field_goals_made INTEGER,
                          field_goals_attempt INTEGER,
                          field_goal_percentage TEXT,
                          two_points_made INTEGER,
                          two_points_attempt INTEGER,
                          two_point_percentage TEXT,
                          three_points_made INTEGER,
                          three_points_attempt INTEGER,
                          three_point_percentage TEXT,
                          free_throws_made INTEGER,
                          free_throws_attempt INTEGER,
                          free_throw_percentage TEXT,
                          offensive_rebounds INTEGER,
                          defensive_rebounds INTEGER,
                          rebounds INTEGER,
                          assists INTEGER,
                          steals INTEGER,
                          blocks INTEGER,
                          turnovers INTEGER,
                          fouls INTEGER,
                          plus_minus INTEGER,
                          UNIQUE(game_date, team))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS leagues
                         (league_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          league_name TEXT UNIQUE NOT NULL,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS game_league
                         (game_date TEXT,
                          team1 TEXT,
                          team2 TEXT,
                          league_id INTEGER,
                          FOREIGN KEY (league_id) REFERENCES leagues(league_id),
                          PRIMARY KEY (game_date, team1, team2))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS players
                         (player_id INTEGER PRIMARY KEY AUTOINCREMENT,
                          player_name TEXT NOT NULL,
                          team TEXT,
                          player_number INTEGER,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          UNIQUE(player_name, team))''')
    
    return execute_with_retry(_init)

def is_game_exists(game_date, team1, team2):
    """해당 경기가 이미 DB에 저장되어 있는지 확인"""
    def _check():
        with get_db_connection() as conn:
            c = conn.cursor()
            
            # game_league 테이블에서 확인 (팀 순서 상관없이)
            c.execute('''SELECT COUNT(*) FROM game_league 
                        WHERE game_date = ? AND 
                              ((team1 = ? AND team2 = ?) OR 
                               (team1 = ? AND team2 = ?))''', 
                     (game_date, team1, team2, team2, team1))
            
            exists_in_game_league = c.fetchone()[0] > 0
            print(f"game_league 테이블 확인 결과: {exists_in_game_league}")
                
            # player_stats 테이블에서도 확인
            c.execute('''SELECT COUNT(*) FROM player_stats 
                        WHERE game_date = ? AND (team = ? OR team = ?)''', 
                     (game_date, team1, team2))
            
            exists_in_player_stats = c.fetchone()[0] > 0
            print(f"player_stats 테이블 확인 결과: {exists_in_player_stats}")
            
            return exists_in_game_league or exists_in_player_stats
    
    return execute_with_retry(_check)

def save_game_data(game_date, team1, team2, team1_players, team1_total, team2_players, team2_total):
    """경기 데이터를 DB에 저장"""
    def _save():
        if is_game_exists(game_date, team1, team2):
            print("이미 저장된 경기입니다.")
            return False
            
        with get_db_connection() as conn:
            try:
                # 선수 기록 저장
                for team_name, players_df in [(team1, team1_players), (team2, team2_players)]:
                    for _, row in players_df.iterrows():
                        # 선수 마스터 데이터 저장
                        player_number = row.get('Nº', 0)
                        get_or_create_player(row['Player'], team_name, player_number)
                        
                        # 경기 기록 저장
                        player_data = {
                            'game_date': game_date,
                            'team': team_name,
                            'player': row['Player'],
                            'player_number': player_number,
                            'minutes': row.get('MIN', '0'),
                            'points': row.get('PTS', 0),
                            'two_points_made': row.get('2PM', 0),
                            'two_points_attempt': row.get('2PA', 0),
                            'two_point_percentage': row.get('2P%', 0),
                            'three_points_made': row.get('3PM', 0),
                            'three_points_attempt': row.get('3PA', 0),
                            'three_point_percentage': row.get('3P%', 0),
                            'field_goals_made': row.get('FGM', 0),
                            'field_goals_attempt': row.get('FGA', 0),
                            'field_goal_percentage': row.get('FG%', 0),
                            'free_throws_made': row.get('FTM', 0),
                            'free_throws_attempt': row.get('FTA', 0),
                            'free_throw_percentage': row.get('FT%', 0),
                            'offensive_rebounds': row.get('OREB', 0),
                            'defensive_rebounds': row.get('DREB', 0),
                            'rebounds': row.get('REB', 0),
                            'assists': row.get('AST', 0),
                            'turnovers': row.get('TOV', 0),
                            'steals': row.get('STL', 0),
                            'blocks': row.get('BLK', 0),
                            'fouls': row.get('PF', 0),
                            'plus_minus': row.get('+/-', 0),
                            'efficiency': row.get('EFF', 0)
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
                        'q1_score': int(total_row.get('Q1', 0)),
                        'q2_score': int(total_row.get('Q2', 0)),
                        'q3_score': int(total_row.get('Q3', 0)),
                        'q4_score': int(total_row.get('Q4', 0)),
                        'total_score': int(total_row.get('PTS', 0)),
                        'field_goals_made': int(total_row.get('FGM', 0)),
                        'field_goals_attempt': int(total_row.get('FGA', 0)),
                        'field_goal_percentage': total_row.get('FG%', 0),
                        'two_points_made': total_row.get('2PM', 0),
                        'two_points_attempt': total_row.get('2PA', 0),
                        'two_point_percentage': total_row.get('2P%', 0),
                        'three_points_made': total_row.get('3PM', 0),
                        'three_points_attempt': total_row.get('3PA', 0),
                        'three_point_percentage': total_row.get('3P%', 0),
                        'free_throws_made': total_row.get('FTM', 0),
                        'free_throws_attempt': total_row.get('FTA', 0),
                        'free_throw_percentage': total_row.get('FT%', 0),
                        'offensive_rebounds': total_row.get('OREB', 0),
                        'defensive_rebounds': total_row.get('DREB', 0),
                        'rebounds': total_row.get('REB', 0),
                        'assists': total_row.get('AST', 0),
                        'steals': total_row.get('STL', 0),
                        'blocks': total_row.get('BLK', 0),
                        'turnovers': total_row.get('TOV', 0),
                        'fouls': total_row.get('PF', 0),
                        'plus_minus': total_row.get('+/-', 0)
                    }
                    
                    placeholders = ', '.join(['?'] * len(team_data))
                    columns = ', '.join(team_data.keys())
                    sql = f'INSERT OR REPLACE INTO team_stats ({columns}) VALUES ({placeholders})'
                    conn.execute(sql, list(team_data.values()))
                
                print("데이터 저장 완료")
                conn.commit()
                return True
                
            except Exception as e:
                print(f"데이터 저장 중 오류 발생: {str(e)}")
                conn.rollback()
                raise e
    
    return execute_with_retry(_save)

def get_player_stats(game_date, team, player):
    """특정 선수의 경기 기록 조회"""
    with get_db_connection() as conn:
        query = '''SELECT * FROM player_stats 
                  WHERE game_date = ? AND team = ? AND player = ?'''
        df = pd.read_sql_query(query, conn, params=(game_date, team, player))
        return df.iloc[0] if not df.empty else None 

# 리그 관련 함수들
def create_league(league_name):
    """새로운 리그 생성"""
    with get_db_connection() as conn:
        try:
            c = conn.cursor()
            c.execute('INSERT INTO leagues (league_name) VALUES (?)', (league_name,))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

def get_leagues():
    """모든 리그 목록 조회 (생성일 역순)"""
    with get_db_connection() as conn:
        query = 'SELECT * FROM leagues ORDER BY created_at DESC'
        return pd.read_sql_query(query, conn)

def assign_game_to_league(game_date, team1, team2, league_id):
    """경기를 리그에 할당"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO game_league 
                    (game_date, team1, team2, league_id) 
                    VALUES (?, ?, ?, ?)''',
                 (game_date, team1, team2, league_id))
        conn.commit()

def get_league_games(league_id):
    """특정 리그의 모든 경기 조회 (날짜 역순)"""
    def _get_games():
        with get_db_connection() as conn:
            # 기본 경기 정보와 팀 스탯 조회
            query = '''
            SELECT 
                gl.game_date,
                gl.team1,
                gl.team2,
                ts1.total_score as team1_points,
                ts2.total_score as team2_points,
                ts1.q1_score as team1_q1,
                ts1.q2_score as team1_q2,
                ts1.q3_score as team1_q3,
                ts1.q4_score as team1_q4,
                ts2.q1_score as team2_q1,
                ts2.q2_score as team2_q2,
                ts2.q3_score as team2_q3,
                ts2.q4_score as team2_q4,
                ts1.two_points_made as team1_2PM,
                ts1.two_points_attempt as team1_2PA,
                ts1.three_points_made as team1_3PM,
                ts1.three_points_attempt as team1_3PA,
                ts1.free_throws_made as team1_FTM,
                ts1.free_throws_attempt as team1_FTA,
                ts1.two_point_percentage as team1_2P_PCT,
                ts1.three_point_percentage as team1_3P_PCT,
                ts1.free_throw_percentage as team1_FT_PCT,
                ts1.rebounds as team1_rebounds,
                ts1.assists as team1_assists,
                ts1.steals as team1_steals,
                ts1.blocks as team1_blocks,
                ts1.turnovers as team1_turnovers,
                ts2.two_points_made as team2_2PM,
                ts2.two_points_attempt as team2_2PA,
                ts2.three_points_made as team2_3PM,
                ts2.three_points_attempt as team2_3PA,
                ts2.free_throws_made as team2_FTM,
                ts2.free_throws_attempt as team2_FTA,
                ts2.two_point_percentage as team2_2P_PCT,
                ts2.three_point_percentage as team2_3P_PCT,
                ts2.free_throw_percentage as team2_FT_PCT,
                ts2.rebounds as team2_rebounds,
                ts2.assists as team2_assists,
                ts2.steals as team2_steals,
                ts2.blocks as team2_blocks,
                ts2.turnovers as team2_turnovers
            FROM game_league gl
            JOIN team_stats ts1 ON gl.game_date = ts1.game_date AND gl.team1 = ts1.team
            JOIN team_stats ts2 ON gl.game_date = ts2.game_date AND gl.team2 = ts2.team
            WHERE gl.league_id = ?
            ORDER BY gl.game_date DESC
            '''
            
            games_df = pd.read_sql_query(query, conn, params=(league_id,))
            
            if not games_df.empty:
                # 각 경기의 선수 기록을 딕셔너리로 저장
                games_with_players = []
                for _, game in games_df.iterrows():
                    game_dict = game.to_dict()
                    
                    # 팀1 선수 기록
                    team1_query = '''
                    SELECT 
                        player_number as "Nº",
                        player as "Player",
                        minutes as "MIN",
                        points as "PTS",
                        field_goals_made as "FGM",
                        field_goals_attempt as "FGA",
                        field_goal_percentage as "FG%",
                        two_points_made as "2PM",
                        two_points_attempt as "2PA",
                        two_point_percentage as "2P%",
                        three_points_made as "3PM",
                        three_points_attempt as "3PA",
                        three_point_percentage as "3P%",
                        free_throws_made as "FTM",
                        free_throws_attempt as "FTA",
                        free_throw_percentage as "FT%",
                        offensive_rebounds as "OREB",
                        defensive_rebounds as "DREB",
                        rebounds as "REB",
                        assists as "AST",
                        steals as "STL",
                        blocks as "BLK",
                        turnovers as "TOV",
                        fouls as "PF",
                        plus_minus as "+/-",
                        efficiency as "EFF"
                    FROM player_stats
                    WHERE game_date = ? AND team = ?
                    ORDER BY player_number
                    '''
                    team1_players = pd.read_sql_query(team1_query, conn, 
                                                    params=(game['game_date'], game['team1']))
                    game_dict['team1_players'] = team1_players
                    
                    # 팀2 선수 기록
                    team2_players = pd.read_sql_query(team1_query, conn, 
                                                    params=(game['game_date'], game['team2']))
                    game_dict['team2_players'] = team2_players
                    
                    games_with_players.append(game_dict)
                
                print(f"리그 {league_id}의 경기 수: {len(games_with_players)}")
                return pd.DataFrame(games_with_players)
            
            return games_df
    
    return execute_with_retry(_get_games)

# 선수 관련 함수들
def get_or_create_player(player_name, team, player_number):
    """선수 정보 조회 또는 생성"""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO players 
                    (player_name, team, player_number)
                    VALUES (?, ?, ?)''',
                 (player_name, team, player_number))
        conn.commit()
        
        c.execute('''SELECT player_id FROM players 
                    WHERE player_name = ? AND team = ?''',
                 (player_name, team))
        return c.fetchone()[0]

def get_player_career_stats(player_name, team=None):
    """선수의 전체 경기 통산 기록 조회"""
    with get_db_connection() as conn:
        query = '''
        SELECT 
            COUNT(DISTINCT game_date) as games_played,
            AVG(points) as avg_points,
            AVG(rebounds) as avg_rebounds,
            AVG(assists) as avg_assists,
            AVG(steals) as avg_steals,
            AVG(blocks) as avg_blocks,
            AVG(turnovers) as avg_turnovers,
            SUM(two_points_made) as total_2pm,
            SUM(two_points_attempt) as total_2pa,
            SUM(three_points_made) as total_3pm,
            SUM(three_points_attempt) as total_3pa,
            SUM(free_throws_made) as total_ftm,
            SUM(free_throws_attempt) as total_fta
        FROM player_stats
        WHERE player = ? {}
        GROUP BY player
        '''.format('AND team = ?' if team else '')
        
        params = (player_name, team) if team else (player_name,)
        df = pd.read_sql_query(query, conn, params=params)
        
        if not df.empty:
            df['fg_percentage'] = (df['total_2pm'] + df['total_3pm']) / (df['total_2pa'] + df['total_3pa']) * 100
            df['three_point_percentage'] = df['total_3pm'] / df['total_3pa'] * 100
            df['ft_percentage'] = df['total_ftm'] / df['total_fta'] * 100
            
        return df.iloc[0] if not df.empty else None 