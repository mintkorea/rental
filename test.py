import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# 데이터 로딩 (실패 시 빈 딕셔너리 반환하여 멈춤 방지)
@st.cache_data(ttl=300)
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
    except Exception as e:
        return None  # 에러 발생 시 None 반환

# 2. 세션 상태 관리 (로딩 루프 방지)
now = get_now()
if 'target_date' not in st.session_state:
    st.session_state.target_date = now.date()

def get_default_meal():
    t = now.time()
    if t < time(9, 0): return "조식"
    if t < time(14, 0): return "중식"
    return "석식"

if 'selected_meal' not in st.session_state:
    st.session_state.selected_meal = get_default_meal()

# 3. 스타일 정의 (모바일 가로 배치 강제)
st.markdown("""
<style>
    .block-container { padding: 1rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    
    /* 버튼 가로 배열 유지 CSS */
    div[data-testid="column"] {
        flex: 1 1 0% !important;
        min-width: 0px !important;
    }
    button { 
        padding: 5px !important; 
        font-size: 14px !important; 
        font-weight: bold !important;
    }
    
    .menu-card { 
        border-top: 5px solid var(--c); 
        border-radius: 15px; 
        padding: 25px 15px; 
        text-align: center; 
        background: white; 
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin: 15px 0;
    }
    .msg-box { text-align: center; background: #f8f9fa; padding: 10px; border-radius: 10px; font-size: 13px; color: #666; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 불러오기
CSV_URL = "https://docs.google.com/spreadsheets/d/1l07s4rubmeB5ld8oJayYrstL34UPKtxQwYptIocgKV0/export?format=csv"
meal_data = load_meal_data(CSV_URL)

if meal_data is None:
    st.error("데이터를 불러올 수 없습니다. 인터넷 연결이나 시트 주소를 확인해주세요.")
    st.stop()

# 5. UI 레이아웃
st.title("🍽️ 성의교정 식단")

# 날짜 변경 (간소화)
d = st.session_state.target_date
col_prev, col_today, col_next = st.columns(3)
if col_prev.button("◀ 이전"): 
    st.session_state.target_date -= timedelta(days=1)
    st.rerun()
if col_today.button("오늘"): 
    st.session_state.target_date = now.date()
    st.rerun()
if col_next.button("다음 ▶"): 
    st.session_state.target_date += timedelta(days=1)
    st.rerun()

st.info(f"📅 {d.strftime('%Y-%m-%d')} 식단")

# 6. 식단 선택 (가로 버튼 메뉴)
color_theme = {"조식": "#E95444", "중식": "#8BC34A", "석식": "#4A90E2", "간편식": "#F1A33B"}
cols = st.columns(len(color_theme))

for i, (m, color) in enumerate(color_theme.items()):
    # 선택된 메뉴는 배경색 강조 (Streamlit 기본 버튼 활용)
    if cols[i].button(m, use_container_width=True, type="primary" if st.session_state.selected_meal == m else "secondary"):
        st.session_state.selected_meal = m
        st.rerun()

# 7. 식단 표시
date_key = d.strftime("%Y-%m-%d")
day_meals = meal_data.get(date_key, {})
meal_info = day_meals.get(st.session_state.selected_meal, {"menu": "정보 없음", "side": "등록된 식단이 없습니다."})
sel_color = color_theme[st.session_state.selected_meal]

st.markdown(f"""
    <div class="menu-card" style="--c: {sel_color};">
        <h3 style="color: {sel_color}; margin-bottom: 5px;">{st.session_state.selected_meal}</h3>
        <div style="font-size: 22px; font-weight: 800; color: #111;">{meal_info['menu']}</div>
        <hr style="border: 0.5px solid #eee; margin: 15px 0;">
        <div style="color: #555; font-size: 15px; line-height: 1.6;">{meal_info['side']}</div>
    </div>
""", unsafe_allow_html=True)
