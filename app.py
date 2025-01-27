import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from database import init_db
from components.player_page import show_player_page
from components.game_page import show_game_page
from components.upload_page import show_upload_page
from components.team_ranking_page import show_team_ranking_page
from components.player_ranking_page import show_player_ranking_page

# 페이지 설정을 가장 먼저 호출
st.set_page_config(
    page_title="농구 기록 관리",
    page_icon="🏀",
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

def main():
    """메인 함수"""
    # data 폴더가 없으면 생성
    os.makedirs("./data", exist_ok=True)
    
    # 데이터베이스 초기화 (앱 시작 시 한 번만)
    if 'db_initialized' not in st.session_state:
        init_db()
        st.session_state.db_initialized = True
    
    # 탭 메뉴
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["경기 기록", "선수 기록", "팀 순위", "개인 순위", "업로드"])
    
    # 경기 기록 탭
    with tab1:
        show_game_page()
    
    # 선수 기록 탭
    with tab2:
        show_player_page()
    
    # 팀 순위 탭
    with tab3:
        show_team_ranking_page()
    
    # 개인 순위 탭
    with tab4:
        show_player_ranking_page()
    
    # 업로드 탭
    with tab5:
        show_upload_page()

if __name__ == "__main__":
    main()
