import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# 2. 데이터 로딩 (구글 시트 연동 및 캐싱)
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

# 3. 세션 및 시간 로직
now = get_now()
if 'target_date' not in st.session_state: st.session_state.target_date = now.date()

color_theme = {"조식": "#E95444", "간편식": "#F1A33B", "중식": "#8BC34A", "석식": "#4A90E2", "야식": "#9C27B0"}

if 'selected_meal' not in st.session_state:
    t = now.time()
    if t < time(9, 0): st.session_state.selected_meal = "조식"
    elif t < time(14, 0): st.session_state.selected_meal = "중식"
    elif t < time(19, 20): st.session_state.selected_meal = "석식"
    else: st.session_state.selected_meal = "중식"

# 4. CSS: 라디오 버튼을 무지개색 인덱스 탭으로 변신
sel_color = color_theme[st.session_state.selected_meal]

st.markdown(f"""
<style>
    .block-container {{ padding: 1rem 0.6rem !important; max-width: 500px !important; }}
    header {{ visibility: hidden; }}
    
    /* 날짜 헤더 */
    .date-header {{ text-align: center; background: #F1F4F9; padding: 12px; border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; }}
    
    /* 라디오 버튼을 가로 탭으로 커스텀 */
    div[data-testid="stRadio"] > div {{
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-between !important;
        background: #F0F2F6;
        padding: 5px !important;
        border-radius: 0 0 15px 15px;
        gap: 4px;
    }}
    
    /* 각 라디오 버튼 아이템 스타일 */
    div[data-testid="stRadio"] label {{
        flex: 1;
        background: white;
        border: 1px solid #D1D9E6;
        border-radius: 8px;
        padding: 8px 0 !important;
        justify-content: center;
        transition: 0.2s;
    }}

    /* 선택된 버튼에만 해당 테마 색상 적용 */
    div[data-testid="stRadio"] label[data-checked="true"] {{
        background-color: {sel_color} !important;
        border-color: {sel_color} !important;
    }}
    div[data-testid="stRadio"] label[data-checked="true"] p {{
        color: white !important;
        font-weight: 800 !important;
    }}

    /* 메뉴 카드 디자인 */
    .menu-card {{ 
        border: 1px solid #D1D9E6; 
        border-top: 6px solid {sel_color}; 
        border-radius: 15px 15px 0 0; 
        padding: 35px 15px; text-align: center; background: white; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        margin-top: 10px;
    }}
</style>
""", unsafe_allow_html=True)

# 5. UI 렌더링
st.markdown('<div style="text-align:center; padding-bottom:5px;"><span style="font-size:20px; font-weight:800; color:#1E3A5F;">🍴 성의교정 주간 식단</span></div>', unsafe_allow_html=True)

d = st.session_state.target_date
st.markdown(f'<div class="date-header"><span style="font-size:16px; font-weight:800;">{d.strftime("%Y.%m.%d")} 식단</span></div>', unsafe_allow_html=True)

# 날짜 이동 (안정적인 st.columns)
c1, c2, c3 = st.columns(3)
if c1.button("◀ 이전", use_container_width=True): 
    st.session_state.target_date -= timedelta(days=1); st.rerun()
if c2.button("오늘", use_container_width=True): 
    st.session_state.target_date = now.date(); st.rerun()
if c3.button("다음 ▶", use_container_width=True): 
    st.session_state.target_date += timedelta(days=1); st.rerun()

# 6. 카드 본문 (라디오 버튼 위에 배치하여 인덱스 느낌 강화)
if meal_data:
    date_key = d.strftime("%Y-%m-%d")
    meal_info = meal_data.get(date_key, {}).get(st.session_state.selected_meal, {"menu": "정보 없음", "side": "등록된 식단이 없습니다."})

    st.markdown(f"""
        <div class="menu-card">
            <div style="font-size: 13px; font-weight: bold; color: {sel_color}; margin-bottom: 5px;">{st.session_state.selected_meal}</div>
            <div style="font-size: 21px; font-weight: 800; color: #111; margin-bottom: 15px; line-height: 1.3; word-break: keep-all;">{meal_info['menu']}</div>
            <div style="height: 1.5px; background: #f0f0f0; width: 40%; margin: 0 auto;"></div>
            <div style="color: #555; font-size: 15px; margin-top: 20px; line-height: 1.6; word-break: keep-all;">{meal_info['side']}</div>
        </div>
    """, unsafe_allow_html=True)

# 7. 라디오 버튼 (카드 아래에 붙여서 탭처럼 활용)
selected = st.radio(
    "식사 선택",
    options=list(color_theme.keys()),
    index=list(color_theme.keys()).index(st.session_state.selected_meal),
    horizontal=True,
    label_visibility="collapsed"
)

if selected != st.session_state.selected_meal:
    st.session_state.selected_meal = selected
    st.rerun()
