import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# 2. 데이터 로딩 (전역 캐싱)
@st.cache_data(ttl=600)
def load_meal_data(url):
    try:
        df = pd.read_csv(url)
        structured_data = {}
        for _, row in df.iterrows():
            d_str = str(row['date']).strip()
            m_type = str(row['meal_type']).strip()
            if d_str not in structured_data: structured_data[d_str] = {}
            structured_data[d_str][m_type] = {
                "menu": str(row['menu']),
                "side": str(row['side'])
            }
        return structured_data
    except: return None

CSV_URL = "https://docs.google.com/spreadsheets/d/1l07s4rubmeB5ld8oJayYrstL34UPKtxQwYptIocgKV0/export?format=csv"
meal_data = load_meal_data(CSV_URL)

# 3. 세션 상태 관리 (페이지 리로드 방지를 위해 st.button 활용)
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

# 4. 스타일 정의 (깜박임 방지 및 디자인 보강)
st.markdown("""
<style>
    .block-container { padding: 1rem 0.6rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    
    /* 버튼 형태의 탭 구현을 위한 CSS */
    div[data-testid="stHorizontalBlock"] { gap: 0rem !important; }
    
    .date-header { text-align: center; background: #F1F4F9; padding: 12px; border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; }
    
    /* 카드 본문 디자인 */
    .menu-card { 
        border: 1px solid #D1D9E6;
        border-top: 6px solid var(--c); 
        border-radius: 0 0 15px 15px; 
        padding: 40px 20px; 
        text-align: center; 
        background: white; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    
    /* Streamlit 기본 버튼을 인덱스 탭처럼 보이게 수정 */
    button {
        border-radius: 10px 10px 0 0 !important;
        border: 1px solid #D1D9E6 !important;
        border-bottom: none !important;
        height: 45px !important;
        font-weight: 800 !important;
    }
</style>
""", unsafe_allow_html=True)

# 5. UI 렌더링 (타이틀)
st.markdown('<div style="text-align:center; padding-bottom:10px;"><span style="font-size:22px; font-weight:800; color:#1E3A5F;">🍴 성의교정 주간 식단</span></div>', unsafe_allow_html=True)

# 날짜 변경 컨트롤러 (st.button 사용으로 리로드 최소화)
d = st.session_state.target_date
st.markdown(f'<div class="date-header"><span style="font-size:17px; font-weight:800;">{d.strftime("%Y.%m.%d")} 식단</span></div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
if col1.button("◀ 이전", use_container_width=True):
    st.session_state.target_date -= timedelta(days=1)
    st.rerun()
if col2.button("오늘", use_container_width=True):
    st.session_state.target_date = now.date()
    st.rerun()
if col3.button("다음 ▶", use_container_width=True):
    st.session_state.target_date += timedelta(days=1)
    st.rerun()

st.write("") # 간격 조절

# 6. 인덱스 탭 구현 (st.columns와 st.button 조합)
color_theme = {"조식": "#E95444", "간편식": "#F1A33B", "중식": "#8BC34A", "석식": "#4A90E2", "야식": "#9C27B0"}
tabs = st.columns(len(color_theme))

for i, (m, color) in enumerate(color_theme.items()):
    is_sel = (st.session_state.selected_meal == m)
    # 선택된 탭은 강조 색상, 나머지는 회색조
    if tabs[i].button(m, use_container_width=True, key=f"tab_{m}"):
        st.session_state.selected_meal = m
        st.rerun()

# 7. 카드 본문 출력
if meal_data:
    date_key = d.strftime("%Y-%m-%d")
    meal_info = meal_data.get(date_key, {}).get(st.session_state.selected_meal, {"menu": "정보 없음", "side": "등록된 식단이 없습니다."})
    sel_color = color_theme[st.session_state.selected_meal]

    st.markdown(f"""
        <div class="menu-card" style="--c: {sel_color};">
            <div style="font-size: 14px; font-weight: bold; color: {sel_color}; margin-bottom: 8px;">{st.session_state.selected_meal}</div>
            <div style="font-size: 22px; font-weight: 800; color: #111; margin-bottom: 20px; line-height: 1.4; word-break: keep-all;">{meal_info['menu']}</div>
            <div style="height: 1.5px; background: #f0f0f0; width: 40%; margin: 0 auto;"></div>
            <div style="color: #555; font-size: 15px; margin-top: 25px; line-height: 1.6; word-break: keep-all;">{meal_info['side']}</div>
        </div>
    """, unsafe_allow_html=True)
