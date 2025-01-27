import streamlit as st
import os
import re
import pandas as pd
from data_loader import load_game_data
from database import (create_league, get_leagues, is_game_exists,
                     save_game_data, assign_game_to_league)

def extract_info_from_filename(filename):
    """파일명에서 날짜와 팀명 추출"""
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

def show_upload_page():
    """업로드 페이지"""
    st.title("데이터 업로드")
    
    # 리그 등록
    with st.expander("리그 등록", expanded=False):
        # 이전 메시지가 있으면 표시
        if 'league_message' in st.session_state:
            if st.session_state.league_message_type == 'success':
                st.success(st.session_state.league_message)
            elif st.session_state.league_message_type == 'error':
                st.error(st.session_state.league_message)
            elif st.session_state.league_message_type == 'warning':
                st.warning(st.session_state.league_message)
            # 메시지를 표시한 후 삭제
            del st.session_state.league_message
            del st.session_state.league_message_type
        
        league_name = st.text_input("리그 이름")
        create_button = st.button("리그 생성")
        
        if create_button:
            if league_name:
                if create_league(league_name):
                    # 성공 메시지 저장
                    st.session_state.league_message = f"리그가 생성되었습니다. - {league_name}"
                    st.session_state.league_message_type = 'success'
                    st.rerun()
                else:
                    # 실패 메시지 저장
                    st.session_state.league_message = "이미 존재하는 리그 이름입니다."
                    st.session_state.league_message_type = 'error'
                    st.rerun()
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