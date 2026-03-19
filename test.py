import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# [데이터 로딩]
@st.cache_data(ttl=600)
def load_meal_data(url):
    try:
        df = pd.read_csv(url)
        structured_data = {}
        for _, row in df.iterrows():
            d_str = str(row['date']).strip()
            m_type = str(row['meal_type']).strip()
            if d_str not in structured_data:
                structured_data[d_str] = {}
            structured_data[d_str][m_type] = {
                "menu": str(row['menu']),
                "side": str(row['side'])
            }
        return structured_data
    except Exception: return None

# 2. 데이터 및 세션 초기화
CSV_URL = "https://docs.google.com/spreadsheets/d/1l07s4rubmeB5ld8oJayYrstL34UPKtxQwYptIocgKV0/export?format=csv"
meal_data = load_meal_data(CSV_URL)

now = get_now()
if 'target_date' not in st.session_state:
    st.session_state.target_date = now.date()

def get_default_meal():
    t = now.time()
    if t < time(9, 0): return "조식"
    if t < time(14, 0): return "중식"
    if t < time(19, 20): return "석식"
    return "중식"

if 'selected_meal' not in st.session_state:
    st.session_state.selected_meal = get_default_meal()

# 3. 쿼리 파라미터를 통한 탭 클릭 감지 (HTML 버튼 연동용)
params = st.query_params
if "meal" in params:
    st.session_state.selected_meal = params["meal"]

# 4. 전체 스타일 정의 (완벽 가로 고정)
st.markdown("""
<style>
    .block-container { padding: 1rem 0.5rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    
    /* [핵심] 커스텀 HTML 탭 디자인 */
    .tab-container {
        display: flex !important;
        flex-direction: row !important;
        width: 100% !important;
        justify-content: space-between !important;
        margin-bottom: -1px !important;
        gap: 2px !important;
    }
    .tab-item {
        flex: 1 !important;
        text-align: center !important;
        padding: 12px 0 !important;
        font-size: 13px !important;
        font-weight: 800 !important;
        border-radius: 10px 10px 0 0 !important;
        border: 1px solid #D1D9E6 !important;
        border-bottom: none !important;
        text-decoration: none !important;
        transition: 0.2s;
    }
    
    .menu-card { 
        border-top: 6px solid var(--c); 
        border-radius: 0 0 15px 15px; 
        padding: 35px 15px; 
        text-align: center; 
        background: white; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.08); 
    }
    
    /* 날짜 네비게이션용 */
    .date-nav { display: flex; background: white; border: 1px solid #D1D9E6; border-radius: 12px; margin-bottom: 20px; overflow: hidden; }
    .date-nav a { flex: 1; text-align: center; padding: 12px; text-decoration: none; color: #1E3A5F; font-weight: bold; font-size: 14px; border-right: 1px solid #F0F0F0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div style="text-align:center; padding-bottom:15px;"><span style="font-size:26px; font-weight:800; color:#1E3A5F;">🍴 성의교정 주간 식단</span></div>', unsafe_allow_html=True)

# 5. 날짜 네비게이션 (생략 가능하나 유지를 위해 HTML로 구현)
d = st.session_state.target_date
date_str = d.strftime("%Y.%m.%d")
st.markdown(f"""
<div style="text-align:center; background:#F8FAFF; padding:15px; border-radius:12px 12px 0 0; border:1px solid #D1D9E6; border-bottom:none;">
    <span style="font-size:18px; font-weight:800;">{date_str} 식단</span>
</div>
<div class="date-nav">
    <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self">◀ 이전</a>
    <a href="./?d={now.date().strftime('%Y-%m-%d')}" target="_self">오늘</a>
    <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}" target="_self">다음 ▶</a>
</div>
""", unsafe_allow_html=True)

# 6. [결정적 해결책] HTML 커스텀 가로 탭
color_theme = {"조식": "#E95444", "간편식": "#F1A33B", "중식": "#8BC34A", "석식": "#4A90E2", "야식": "#9C27B0"}
tab_html = '<div class="tab-container">'

for m, color in color_theme.items():
    is_sel = (st.session_state.selected_meal == m)
    bg = color if is_sel else "#f8f9fa"
    txt = "white" if is_sel else "#666"
    opacity = "1" if is_sel else "0.6"
    # 클릭 시 URL 파라미터를 변경하여 페이지를 리로드하는 방식
    tab_html += f'<a href="./?meal={m}" target="_self" class="tab-item" style="background:{bg}; color:{txt}; opacity:{opacity};">{m}</a>'

tab_html += '</div>'
st.markdown(tab_html, unsafe_allow_html=True)

# 7. 식단 내용 표시
if meal_data:
    date_key = d.strftime("%Y-%m-%d")
    day_meals = meal_data.get(date_key, {})
    meal_info = day_meals.get(st.session_state.selected_meal, {"menu": "정보 없음", "side": "등록된 식단 정보가 없습니다."})
    sel_color = color_theme[st.session_state.selected_meal]

    st.markdown(f"""
        <div class="menu-card" style="--c: {sel_color};">
            <div style="font-size: 16px; font-weight: bold; color: {sel_color}; margin-bottom: 10px;">{st.session_state.selected_meal}</div>
            <div style="font-size: 24px; font-weight: 800; color: #111; margin-bottom: 15px; line-height: 1.3;">{meal_info['menu']}</div>
            <div style="height: 1px; background: #eee; width: 40%; margin: 0 auto;"></div>
            <div style="color: #555; font-size: 16px; margin-top: 20px; line-height: 1.6; word-break: keep-all;">{meal_info['side']}</div>
        </div>
        <div style="text-align: center; background: #f8f9fa; padding: 12px; border-radius: 12px; font-size: 14px; font-weight: bold; color: #555; margin-top: 20px;">
            💡 즐거운 식사 시간 되세요!
        </div>
    """, unsafe_allow_html=True)
