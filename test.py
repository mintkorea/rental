import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정 및 시간대
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# [데이터 로딩] 캐싱 적용 및 오류 방지
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
    except Exception:
        return None

# 근무조 계산 함수
def get_work_shift(target_date):
    anchor = datetime(2026, 3, 13).date()
    diff = (target_date - anchor).days
    shifts = [{"n": "A조", "bg": "#FF9800"}, {"n": "B조", "bg": "#E91E63"}, {"n": "C조", "bg": "#2196F3"}]
    return shifts[diff % 3]

# 2. 데이터 불러오기 및 세션 초기화
CSV_URL = "https://docs.google.com/spreadsheets/d/1l07s4rubmeB5ld8oJayYrstL34UPKtxQwYptIocgKV0/export?format=csv"
meal_data = load_meal_data(CSV_URL)

now = get_now()
curr_date = now.date()

if 'target_date' not in st.session_state:
    st.session_state.target_date = curr_date

def get_default_meal():
    t = now.time()
    if t < time(9, 0): return "조식"
    if t < time(14, 0): return "중식"
    if t < time(19, 20): return "석식"
    return "중식"

if 'selected_meal' not in st.session_state:
    st.session_state.selected_meal = get_default_meal()

# 3. 모바일 최적화 스타일 (핵심 디자인)
st.markdown("""
<style>
    .block-container { padding: 1rem 1.2rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    
    /* 날짜 헤더 & 네비게이션 */
    .date-box { text-align: center; background: #F8FAFF; padding: 15px 10px 8px; border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; }
    .res-sub-title { font-size: 19px !important; font-weight: 800; color: #333; }
    .nav-bar { display: flex; width: 100%; background: white; border: 1px solid #D1D9E6; border-radius: 0 0 10px 10px; margin-bottom: 25px; }
    .nav-btn { flex: 1; text-align: center; padding: 12px 0; text-decoration: none; color: #1E3A5F; font-weight: bold; font-size: 14px; border-right: 1px solid #F0F0F0; }
    
    /* 가로 탭 버튼 레이아웃 */
    div[data-testid="column"] { flex: 1 1 0% !important; min-width: 0px !important; padding: 0 1px !important; }
    
    button { 
        border-radius: 10px 10px 0 0 !important; 
        height: 42px !important; 
        font-weight: 800 !important; 
        font-size: 13px !important;
        border: 1px solid #D1D9E6 !important;
        border-bottom: none !important;
        margin-bottom: -5px !important;
    }

    /* 식단 카드 디자인 */
    .menu-card { 
        border-top: 6px solid var(--c); 
        border-radius: 0 0 15px 15px; 
        padding: 35px 15px; 
        text-align: center; 
        background: white; 
        box-shadow: 0 8px 20px rgba(0,0,0,0.08); 
        margin-top: -1px;
    }
    
    .msg-box { text-align: center; background: #f8f9fa; padding: 12px; border-radius: 12px; font-size: 14px; font-weight: bold; color: #555; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# 헤더
st.markdown('<div style="text-align:center; padding-bottom:10px;"><span style="font-size:28px; font-weight:800; color:#1E3A5F;">🍴 성의교정 주간 식단</span></div>', unsafe_allow_html=True)

# 4. 날짜 네비게이션
d = st.session_state.target_date
shift = get_work_shift(d)
w_list = ["월","화","수","목","금","토","일"]
w_str = w_list[d.weekday()]
w_class = "color: #0000FF;" if d.weekday() == 5 else ("color: #FF0000;" if d.weekday() == 6 else "")

st.markdown(f"""
<div class="date-box">
    <span class="res-sub-title">{d.strftime("%Y.%m.%d")}.<span style="{w_class}">({w_str})</span>
    <span style="background:{shift['bg']}; color:white; padding:2px 10px; border-radius:12px; font-size:14px; margin-left:5px;">{shift['n']}</span></span>
</div>
<div class="nav-bar">
    <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-btn">◀ 이전</a>
    <a href="./?d={curr_date.strftime('%Y-%m-%d')}" target="_self" class="nav-btn">오늘</a>
    <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-btn">다음 ▶</a>
</div>
""", unsafe_allow_html=True)

# 5. 고유 컬러 탭 버튼 (가로 배치)
color_theme = {"조식": "#E95444", "간편식": "#F1A33B", "중식": "#8BC34A", "석식": "#4A90E2", "야식": "#9C27B0"}
cols = st.columns(len(color_theme))

for i, (m, color) in enumerate(color_theme.items()):
    is_selected = (st.session_state.selected_meal == m)
    
    # CSS 주입: 선택된 버튼에만 고유 색상 입히기
    btn_style = f"""
    <style>
        div[data-testid="column"]:nth-child({i+1}) button {{
            background-color: {color if is_selected else "#f8f9fa"} !important;
            color: {"white" if is_selected else "#666"} !important;
            border-color: {color if is_selected else "#D1D9E6"} !important;
            opacity: {1 if is_selected else 0.6} !important;
        }
    </style>
    """
    st.markdown(btn_style, unsafe_allow_html=True)
    
    if cols[i].button(m, use_container_width=True):
        st.session_state.selected_meal = m
        st.rerun()

# 6. 식단 카드 출력
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
    """, unsafe_allow_html=True)
else:
    st.error("데이터 로딩 중 오류가 발생했습니다.")

# 7. 시간 안내 메시지
meal_times = {"조식": (time(7, 0), time(9, 0)), "중식": (time(11, 20), time(14, 0)), "석식": (time(17, 20), time(19, 20))}
msg = "💡 즐거운 식사 시간 되세요!"
if st.session_state.selected_meal in meal_times:
    s_t, e_t = meal_times[st.session_state.selected_meal]
    t_dt_s = datetime.combine(d, s_t).replace(tzinfo=KST)
    t_dt_e = datetime.combine(d, e_t).replace(tzinfo=KST)

    if d == curr_date:
        if now < t_dt_s:
            diff = t_dt_s - now
            msg = f"⏳ {st.session_state.selected_meal} 시작까지 {diff.seconds//3600}시간 {(diff.seconds%3600)//60}분 남음"
        elif now <= t_dt_e:
            msg = f"🍴 {st.session_state.selected_meal} 배식 중! 맛있게 드세요."
        else:
            msg = "🚩 배식이 종료된 메뉴입니다."

st.markdown(f'<div class="msg-box">{msg}</div>', unsafe_allow_html=True)
