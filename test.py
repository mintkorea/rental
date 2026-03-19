import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정 (시간대 고정)
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# 2. 데이터 로딩 (전역 캐싱으로 깜빡임 최소화)
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

# 3. 세션 상태 관리 (URL 파라미터 우선 처리)
now = get_now()
params = st.query_params

if "d" in params:
    try: st.session_state.target_date = datetime.strptime(params["d"], "%Y-%m-%d").date()
    except: st.session_state.target_date = now.date()
else:
    if 'target_date' not in st.session_state: st.session_state.target_date = now.date()

def get_default_meal():
    t = now.time()
    if t < time(9, 0): return "조식"
    if t < time(14, 0): return "중식"
    if t < time(19, 20): return "석식"
    return "중식"

if "meal" in params:
    st.session_state.selected_meal = params["meal"]
elif 'selected_meal' not in st.session_state:
    st.session_state.selected_meal = get_default_meal()

# 4. 스타일 정의 (카드 경계 및 로딩 최적화)
st.markdown("""
<style>
    .block-container { padding: 1rem 0.6rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    
    /* 날짜 헤더 디자인 */
    .date-header { text-align: center; background: #F1F4F9; padding: 15px; border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; }
    .nav-bar { display: flex; background: white; border: 1px solid #D1D9E6; border-radius: 0 0 12px 12px; margin-bottom: 20px; overflow: hidden; }
    .nav-bar a { flex: 1; text-align: center; padding: 12px; text-decoration: none; color: #1E3A5F; font-weight: bold; font-size: 14px; border-right: 1px solid #F0F0F0; }

    /* 커스텀 탭 (가로 고정) */
    .tab-container { display: flex; width: 100%; gap: 3px; margin-bottom: -1px; }
    .tab-item { 
        flex: 1; text-align: center; padding: 12px 0; font-size: 13px; font-weight: 800; 
        border-radius: 10px 10px 0 0; border: 1px solid #D1D9E6; border-bottom: none; 
        text-decoration: none; transition: 0.1s;
    }
    
    /* [개선] 카드 경계 강화 디자인 */
    .menu-card { 
        border: 1px solid #D1D9E6; /* 명확한 테두리 추가 */
        border-top: 6px solid var(--c); 
        border-radius: 0 0 15px 15px; 
        padding: 40px 20px; 
        text-align: center; 
        background: white; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.1); /* 그림자 강화로 입체감 부여 */
        margin-bottom: 20px;
    }
    
    .status-msg { text-align: center; background: #f8f9fa; padding: 12px; border-radius: 12px; font-size: 14px; font-weight: bold; color: #555; border: 1px solid #EEE; }
</style>
""", unsafe_allow_html=True)

# 5. UI 렌더링
st.markdown('<div style="text-align:center; padding-bottom:10px;"><span style="font-size:26px; font-weight:800; color:#1E3A5F;">🍴 성의교정 주간 식단</span></div>', unsafe_allow_html=True)

d = st.session_state.target_date
st.markdown(f"""
<div class="date-header">
    <span style="font-size:18px; font-weight:800;">{d.strftime("%Y.%m.%d")} 식단</span>
</div>
<div class="nav-bar">
    <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}&meal={st.session_state.selected_meal}" target="_self">◀ 이전</a>
    <a href="./?d={now.date().strftime('%Y-%m-%d')}&meal={st.session_state.selected_meal}" target="_self">오늘</a>
    <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}&meal={st.session_state.selected_meal}" target="_self">다음 ▶</a>
</div>
""", unsafe_allow_html=True)

# 6. 탭 메뉴 생성 (HTML)
color_theme = {"조식": "#E95444", "간편식": "#F1A33B", "중식": "#8BC34A", "석식": "#4A90E2", "야식": "#9C27B0"}
tab_html = '<div class="tab-container">'
for m, color in color_theme.items():
    is_sel = (st.session_state.selected_meal == m)
    bg = color if is_sel else "#f8f9fa"
    txt = "white" if is_sel else "#666"
    tab_html += f'<a href="./?d={d.strftime("%Y-%m-%d")}&meal={m}" target="_self" class="tab-item" style="background:{bg}; color:{txt};">{m}</a>'
tab_html += '</div>'
st.markdown(tab_html, unsafe_allow_html=True)

# 7. 카드 본문
if meal_data:
    date_key = d.strftime("%Y-%m-%d")
    meal_info = meal_data.get(date_key, {}).get(st.session_state.selected_meal, {"menu": "정보 없음", "side": "등록된 식단이 없습니다."})
    sel_color = color_theme[st.session_state.selected_meal]

    st.markdown(f"""
        <div class="menu-card" style="--c: {sel_color};">
            <div style="font-size: 15px; font-weight: bold; color: {sel_color}; margin-bottom: 10px;">{st.session_state.selected_meal}</div>
            <div style="font-size: 23px; font-weight: 800; color: #111; margin-bottom: 20px; line-height: 1.4; word-break: keep-all;">{meal_info['menu']}</div>
            <div style="height: 1.5px; background: #f0f0f0; width: 50%; margin: 0 auto;"></div>
            <div style="color: #666; font-size: 16px; margin-top: 25px; line-height: 1.7; word-break: keep-all;">{meal_info['side']}</div>
        </div>
        <div class="status-msg">💡 즐거운 식사 시간 되세요!</div>
    """, unsafe_allow_html=True)
