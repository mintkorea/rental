import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# 2. 데이터 로딩 (캐싱)
@st.cache_data(ttl=600)
def load_meal_data(url):
    try:
        df = pd.read_csv(url)
        structured_data = {}
        for _, row in df.iterrows():
            d_str = str(row['date']).strip()
            m_type = str(row['meal_type']).strip()
            if d_str not in structured_data: structured_data[d_str] = {}
            structured_data[d_str][m_type] = {"menu": str(row['menu']), "side": str(row['side'])}
        return structured_data
    except: return None

CSV_URL = "https://docs.google.com/spreadsheets/d/1l07s4rubmeB5ld8oJayYrstL34UPKtxQwYptIocgKV0/export?format=csv"
meal_data = load_meal_data(CSV_URL)

# 3. 세션 상태 관리
now = get_now()
if 'target_date' not in st.session_state: st.session_state.target_date = now.date()
if 'selected_meal' not in st.session_state:
    t = now.time()
    if t < time(9, 0): st.session_state.selected_meal = "조식"
    elif t < time(14, 0): st.session_state.selected_meal = "중식"
    elif t < time(19, 20): st.session_state.selected_meal = "석식"
    else: st.session_state.selected_meal = "중식"

# 4. CSS: 모바일 가로 유지 및 특정 버튼 색상 타겟팅
color_theme = {"조식": "#E95444", "간편식": "#F1A33B", "중식": "#8BC34A", "석식": "#4A90E2", "야식": "#9C27B0"}

# 식단 탭 버튼 전용 스타일 (상단 날짜 버튼과 분리하기 위해 div[data-testid="column"] 조합 사용)
tab_styles = ""
for i, (m, color) in enumerate(color_theme.items()):
    is_sel = (st.session_state.selected_meal == m)
    bg = color if is_sel else "#F0F2F6"
    txt = "white" if is_sel else "#555"
    tab_styles += f"""
        /* 2번째 가로 블록(식단 탭) 내의 버튼들만 타겟팅 */
        div[data-testid="stVerticalBlock"] > div:nth-child(7) div[data-testid="column"]:nth-child({i+1}) button {{
            background-color: {bg} !important;
            color: {txt} !important;
            border: 1px solid {color if is_sel else "#D1D9E6"} !important;
            border-radius: 10px 10px 0 0 !important;
            height: 45px !important;
            font-size: 13px !important;
            margin-bottom: -1px !important;
        }}
    """

st.markdown(f"""
<style>
    .block-container {{ padding: 1rem 0.5rem !important; max-width: 500px !important; }}
    header {{ visibility: hidden; }}
    
    /* [핵심] 모바일에서도 컬럼 가로 배열 유지 */
    div[data-testid="column"] {{
        min-width: 0px !important;
        flex: 1 1 0% !important;
    }}
    div[data-testid="stHorizontalBlock"] {{
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        align-items: flex-end !important;
    }}

    {tab_styles}

    .date-header {{ text-align: center; background: #F1F4F9; padding: 12px; border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; }}
    .menu-card {{ 
        border: 1px solid #D1D9E6; border-top: 6px solid var(--c); border-radius: 0 0 15px 15px; 
        padding: 35px 15px; text-align: center; background: white; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.05); margin-bottom: 15px;
    }}
</style>
""", unsafe_allow_html=True)

# 5. UI 렌더링
st.markdown('<div style="text-align:center; padding-bottom:5px;"><span style="font-size:20px; font-weight:800; color:#1E3A5F;">🍴 성의교정 주간 식단</span></div>', unsafe_allow_html=True)

d = st.session_state.target_date
st.markdown(f'<div class="date-header"><span style="font-size:16px; font-weight:800;">{d.strftime("%Y.%m.%d")} 식단</span></div>', unsafe_allow_html=True)

# [가로 블록 1] 날짜 컨트롤러
c1, c2, c3 = st.columns(3)
if c1.button("◀ 이전", use_container_width=True): 
    st.session_state.target_date -= timedelta(days=1); st.rerun()
if c2.button("오늘", use_container_width=True): 
    st.session_state.target_date = now.date(); st.rerun()
if c3.button("다음 ▶", use_container_width=True): 
    st.session_state.target_date += timedelta(days=1); st.rerun()

st.write("") 

# [가로 블록 2] 식단 인덱스 탭 (모바일 가로 고정)
m_cols = st.columns(len(color_theme))
for i, m in enumerate(color_theme.keys()):
    if m_cols[i].button(m, use_container_width=True):
        st.session_state.selected_meal = m
        st.rerun()

# 6. 카드 본문
if meal_data:
    date_key = d.strftime("%Y-%m-%d")
    meal_info = meal_data.get(date_key, {}).get(st.session_state.selected_meal, {"menu": "정보 없음", "side": "등록된 식단이 없습니다."})
    sel_color = color_theme[st.session_state.selected_meal]

    st.markdown(f"""
        <div class="menu-card" style="--c: {sel_color};">
            <div style="font-size: 13px; font-weight: bold; color: {sel_color}; margin-bottom: 5px;">{st.session_state.selected_meal}</div>
            <div style="font-size: 21px; font-weight: 800; color: #111; margin-bottom: 15px; line-height: 1.3; word-break: keep-all;">{meal_info['menu']}</div>
            <div style="height: 1.5px; background: #f0f0f0; width: 40%; margin: 0 auto;"></div>
            <div style="color: #555; font-size: 15px; margin-top: 20px; line-height: 1.6; word-break: keep-all;">{meal_info['side']}</div>
        </div>
    """, unsafe_allow_html=True)
