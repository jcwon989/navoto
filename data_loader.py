import pandas as pd
import os

def clean_value(val):
    """숫자 또는 퍼센트 문자열을 적절한 형태로 변환"""
    if pd.isna(val):
        return 0
    if isinstance(val, (int, float)):
        return int(val)
    if isinstance(val, str):
        # 퍼센트 문자열은 그대로 반환
        if '%' in val:
            return val.strip()
        try:
            return int(float(val))
        except ValueError:
            return 0
    return 0

def load_csv_data(file_path):
    """CSV 파일에서 데이터 읽기"""
    try:
        # CSV 파일 읽기
        df = pd.read_csv(file_path)
        
        # 구분자를 기준으로 팀 데이터 분리
        separator_idx = df[df['Nº'].isna()].index[0]
        team1_players = df[:separator_idx].copy()
        team2_players = df[separator_idx + 1:].copy()
        
        # 팀 전체 기록 (마지막 행)
        team1_total = team1_players.iloc[-1].copy()
        team2_total = team2_players.iloc[-1].copy()
        
        # 선수 기록만 추출 (전체 기록 제외)
        team1_players = team1_players[:-1].copy()
        team2_players = team2_players[:-1].copy()
        
        return team1_players, team1_total, team2_players, team2_total
        
    except Exception as e:
        print(f"CSV 파일 읽기 오류: {str(e)}")
        raise

def load_excel_data(file_path):
    """Excel 파일에서 데이터 읽기"""
    try:
        print("\n=== Excel 파일 읽기 시작 ===")
        
        # 엑셀 파일의 모든 시트 정보 출력
        xl = pd.ExcelFile(file_path)
        print("\n[엑셀 파일 시트 목록]")
        for idx, sheet in enumerate(xl.sheet_names):
            print(f"시트 {idx+1}: {sheet}")
        
        # 1. 팀1 선수 기록 읽기 (첫 번째 시트)
        team1_players = pd.read_excel(file_path, sheet_name=0)
        print("\n[팀1 선수 기록]")
        print(team1_players.head())
        
        # 2. 팀2 선수 기록 읽기 (두 번째 시트)
        team2_players = pd.read_excel(file_path, sheet_name=1)
        print("\n[팀2 선수 기록]")
        print(team2_players.head())
        
        # 3. 팀 스탯 데이터 읽기 (세 번째 시트)
        # 3.1 스코어보드 데이터 읽기 (A1:F3)
        quarter_scores = pd.read_excel(file_path, sheet_name=2, usecols="A:F", nrows=3)
        print("\n[스코어보드 데이터]")
        print(quarter_scores)
        
        # 3.2 팀 스탯 데이터 읽기 (A6:C28)
        team_stats = pd.read_excel(file_path, sheet_name=2, skiprows=4, nrows=23, usecols="A:C")
        print("\n[팀 스탯 데이터]")
        print(team_stats)
        
        # 팀명 가져오기
        team1_name = team_stats.iloc[0, 0]
        team2_name = team_stats.iloc[0, 2]
        print(f"\n팀1: {team1_name}")
        print(f"팀2: {team2_name}")
        
        # 팀 스탯 데이터 정리
        team_stats = team_stats.iloc[1:, :]  # 팀명 행 제외
        stat_labels = team_stats.iloc[:, 1]  # B열의 라벨
        team1_stats = team_stats.iloc[:, 0]  # A열의 팀1 데이터
        team2_stats = team_stats.iloc[:, 2]  # C열의 팀2 데이터
        
        print("\n[통계 라벨]")
        print(stat_labels.tolist())
        
        print("\n[팀1 통계]")
        for label, value in zip(stat_labels, team1_stats):
            print(f"{label}: {value}")
            
        print("\n[팀2 통계]")
        for label, value in zip(stat_labels, team2_stats):
            print(f"{label}: {value}")
        
        # 팀1 전체 기록 생성
        team1_total = pd.Series({
            'Q1': clean_value(quarter_scores.iloc[0, 1]),
            'Q2': clean_value(quarter_scores.iloc[0, 2]),
            'Q3': clean_value(quarter_scores.iloc[0, 3]),
            'Q4': clean_value(quarter_scores.iloc[0, 4]),
            'PTS': clean_value(quarter_scores.iloc[0, 5]),
            '2PA': clean_value(team1_stats[stat_labels == '2PA'].iloc[0]),
            '2PM': clean_value(team1_stats[stat_labels == '2PM'].iloc[0]),
            '2P%': team1_stats[stat_labels == '2P%'].iloc[0],
            '3PA': clean_value(team1_stats[stat_labels == '3PA'].iloc[0]),
            '3PM': clean_value(team1_stats[stat_labels == '3PM'].iloc[0]),
            '3P%': team1_stats[stat_labels == '3P%'].iloc[0],
            'FGA': clean_value(team1_stats[stat_labels == 'FGA'].iloc[0]),
            'FGM': clean_value(team1_stats[stat_labels == 'FGM'].iloc[0]),
            'FG%': team1_stats[stat_labels == 'FG%'].iloc[0],
            'FTA': clean_value(team1_stats[stat_labels == 'FTA'].iloc[0]),
            'FTM': clean_value(team1_stats[stat_labels == 'FTM'].iloc[0]),
            'FT%': team1_stats[stat_labels == 'FT%'].iloc[0],
            'OREB': clean_value(team1_stats[stat_labels == 'OREB'].iloc[0]),
            'DREB': clean_value(team1_stats[stat_labels == 'DREB'].iloc[0]),
            'REB': clean_value(team1_stats[stat_labels == 'REB'].iloc[0]),
            'AST': clean_value(team1_stats[stat_labels == 'AST'].iloc[0]),
            'STL': clean_value(team1_stats[stat_labels == 'STL'].iloc[0]),
            'BLK': clean_value(team1_stats[stat_labels == 'BLK'].iloc[0]),
            'TOV': clean_value(team1_stats[stat_labels == 'TOV'].iloc[0]),
            'PF': clean_value(team1_stats[stat_labels == 'PF'].iloc[0])
        })
        
        # 팀2 전체 기록 생성
        team2_total = pd.Series({
            'Q1': clean_value(quarter_scores.iloc[1, 1]),
            'Q2': clean_value(quarter_scores.iloc[1, 2]),
            'Q3': clean_value(quarter_scores.iloc[1, 3]),
            'Q4': clean_value(quarter_scores.iloc[1, 4]),
            'PTS': clean_value(quarter_scores.iloc[1, 5]),
            '2PA': clean_value(team2_stats[stat_labels == '2PA'].iloc[0]),
            '2PM': clean_value(team2_stats[stat_labels == '2PM'].iloc[0]),
            '2P%': team2_stats[stat_labels == '2P%'].iloc[0],
            '3PA': clean_value(team2_stats[stat_labels == '3PA'].iloc[0]),
            '3PM': clean_value(team2_stats[stat_labels == '3PM'].iloc[0]),
            '3P%': team2_stats[stat_labels == '3P%'].iloc[0],
            'FGA': clean_value(team2_stats[stat_labels == 'FGA'].iloc[0]),
            'FGM': clean_value(team2_stats[stat_labels == 'FGM'].iloc[0]),
            'FG%': team2_stats[stat_labels == 'FG%'].iloc[0],
            'FTA': clean_value(team2_stats[stat_labels == 'FTA'].iloc[0]),
            'FTM': clean_value(team2_stats[stat_labels == 'FTM'].iloc[0]),
            'FT%': team2_stats[stat_labels == 'FT%'].iloc[0],
            'OREB': clean_value(team2_stats[stat_labels == 'OREB'].iloc[0]),
            'DREB': clean_value(team2_stats[stat_labels == 'DREB'].iloc[0]),
            'REB': clean_value(team2_stats[stat_labels == 'REB'].iloc[0]),
            'AST': clean_value(team2_stats[stat_labels == 'AST'].iloc[0]),
            'STL': clean_value(team2_stats[stat_labels == 'STL'].iloc[0]),
            'BLK': clean_value(team2_stats[stat_labels == 'BLK'].iloc[0]),
            'TOV': clean_value(team2_stats[stat_labels == 'TOV'].iloc[0]),
            'PF': clean_value(team2_stats[stat_labels == 'PF'].iloc[0])
        })
        print("team1_total")
        print(team1_total)
        print("team2_total")
        print(team2_total)
        return team1_players, team1_total, team2_players, team2_total
        
    except Exception as e:
        print(f"Excel 파일 읽기 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def load_game_data(file_path):
    """파일 형식에 따라 적절한 로더 함수 호출"""
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.csv':
        return load_csv_data(file_path)
    elif ext in ['.xls', '.xlsx']:
        return load_excel_data(file_path)
    else:
        raise ValueError(f"지원하지 않는 파일 형식입니다: {ext}")

# 테스트 코드
if __name__ == "__main__":
    # CSV 파일 테스트
    csv_file = "./data/stats_스탯세탁기_vs_ngh_25-1-14.xls"
    if os.path.exists(csv_file):
        print("\n=== CSV 파일 테스트 ===")
        team1_players, team1_total, team2_players, team2_total = load_game_data(csv_file)
        print("CSV 파일 읽기 성공")
        print(f"팀1 선수 수: {len(team1_players)}")
        print(f"팀2 선수 수: {len(team2_players)}")
    
    # Excel 파일 테스트
    xls_file = "./data/stats_스탯세탁기_vs_pjh_25-1-21.xls"
    if os.path.exists(xls_file):
        print("\n=== Excel 파일 테스트 ===")
        team1_players, team1_total, team2_players, team2_total = load_game_data(xls_file)
        print("Excel 파일 읽기 성공")
        print(f"팀1 선수 수: {len(team1_players)}")
        print(f"팀2 선수 수: {len(team2_players)}") 