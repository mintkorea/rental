import streamlit as st

# 탭을 사용하면 모바일에서도 상단 가로 메뉴처럼 작동합니다.
tab1, tab2, tab3, tab4 = st.tabs(["🏠 홈", "📅 일정", "📞 연락망", "⚙️ 설정"])

with tab1:
    st.write("홈 화면 콘텐츠")
with tab2:
    st.write("시설 예약 현황 등 일정 관리")
# ... 나머지 탭 구성



import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정 및 시간대
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# [개선] 데이터 로딩 함수 (캐싱 적용)
@st.cache_data(ttl=600)  # 10분 동안 데이터를 메모리에 유지
def load_meal_data(url):
    try:
        # 구글 시트 CSV 읽기
        df = pd.read_csv(url)
        structured_data = {}
        for _, row in df.iterrows():
            d_str = str(row['date']).strip()
            m_type = str(row['meal_type']).strip()
            if d_str not in structured_data:
                structured_data[d_str] = {}
            structured_data[d_str][m_type] = {
                "menu": row['menu'],
                "side": row['side']
            }
        return structured_data
    except Exception as e:
        st.error(f"데이터 연결 오류: {e}")
        return {}

# 근무조 계산 함수
def get_work_shift(target_date):
    anchor = datetime(2026, 3, 13).date()
    diff = (target_date - anchor).days
    shifts = [{"n": "A조", "bg": "#FF9800"}, {"n": "B조", "bg": "#E91E63"}, {"n": "C조", "bg": "#2196F3"}]
    return shifts[diff % 3]

# 2. 데이터 불러오기 및 세션 초기화
CSV_URL = "https://docs.google.com/spreadsheets/d/1l07s4rubmeB5ld8oJayYrstL34UPKtxQwYptIocgKV0/export?format=csv"

# 헤더 선출력 (사용자 응답성 향상)
st.markdown("""
<div style="text-align:center; padding: 15px 0 5px 0;">
    <span style="
        font-size: 35px !important; 
        font-weight: 800; 
        color: #1E3A5F; 
        letter-spacing: -0.5px;
        white-space: nowrap;
    ">
        🍽️ 성의교정 주간 식단
    </span>
</div>
""", unsafe_allow_html=True)

with st.spinner('최신 식단 정보를 가져오고 있습니다...'):
    meal_data = load_meal_data(CSV_URL)

now = get_now()
curr_date = now.date()

if 'target_date' not in st.session_state:
    st.session_state.target_date = curr_date

# 시간대별 기본 식사 설정
def get_default_meal():
    t = now.time()
    if t < time(9, 0): return "조식"
    if t < time(14, 0): return "중식"
    if t < time(19, 20): return "석식"
    return "중식"

if 'selected_meal' not in st.session_state:
    st.session_state.selected_meal = get_default_meal()

# URL 파라미터 처리
params = st.query_params
if "d" in params:
    try:
        st.session_state.target_date = datetime.strptime(params["d"], "%Y-%m-%d").date()
    except: pass

# 3. 화면 레이아웃 및 스타일
d = st.session_state.target_date
shift = get_work_shift(d)
w_list = ["월","화","수","목","금","토","일"]
w_str = w_list[d.weekday()]
w_class = "sat" if d.weekday() == 5 else ("sun" if d.weekday() == 6 else "")

color_theme = {"조식": "#E95444", "간편식": "#F1A33B", "중식": "#8BC34A", "석식": "#4A90E2", "야식": "#673AB7"}
meal_times = {"조식": (time(7, 0), time(9, 0)), "중식": (time(11, 20), time(14, 0)), "석식": (time(17, 20), time(19, 20))}

st.markdown(f"""
<style>
    .block-container {{ padding: 1rem 1.2rem !important; max-width: 500px !important; }}
    header {{ visibility: hidden; }}
    .date-box {{ text-align: center; background: #F8FAFF; padding: 15px 10px 8px; border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; }}
    .res-sub-title {{ font-size: 18px !important; font-weight: 700; color: #333; }}
    .sat {{ color: #0000FF !important; }} .sun {{ color: #FF0000 !important; }}
    .nav-bar {{ display: flex; width: 100%; background: white; border: 1px solid #D1D9E6; border-radius: 0 0 10px 10px; margin-bottom: 20px; }}
    .nav-btn {{ flex: 1; text-align: center; padding: 10px 0; text-decoration: none; color: #1E3A5F; font-weight: bold; font-size: 13px; border-right: 1px solid #F0F0F0; }}
    .menu-card {{ border: 3px solid var(--c); border-radius: 20px 20px 0 0; padding: 25px 15px; text-align: center; background: white; min-height: 200px; display: flex; flex-direction: column; justify-content: center; }}
    .tab-wrap {{ display: flex; width: 100%; margin-top: -3px; }}
    .tab-item {{ flex: 1; text-align: center; padding: 10px 0; font-size: 12px; font-weight: bold; color: white; }}
    div[data-testid="stRadio"] > div {{ display: flex !important; flex-wrap: nowrap !important; background: #f1f3f5; padding: 10px 2px !important; border-radius: 0 0 20px 20px; }}
    div[data-testid="stRadio"] label p {{ font-size: 12px !important; font-weight: 800 !important; white-space: nowrap !important; }}
    .msg-box {{ text-align: center; background: #f8f9fa; padding: 12px; border-radius: 12px; font-size: 14px; font-weight: bold; color: #555; margin-top: 15px; }}
</style>
""", unsafe_allow_html=True)

# 날짜 네비게이션
st.markdown(f"""
<div class="date-box">
    <span class="res-sub-title">{d.strftime("%Y.%m.%d")}.<span class="{w_class}">({w_str})</span>
    <span style="background:{shift['bg']}; color:white; padding:2px 10px; border-radius:12px; font-size:14px; margin-left:5px;">{shift['n']}</span></span>
</div>
<div class="nav-bar">
    <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-btn">◀ Before</a>
    <a href="./?d={curr_date.strftime('%Y-%m-%d')}" target="_self" class="nav-btn">Today</a>
    <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-btn">Next ▶</a>
</div>
""", unsafe_allow_html=True)

# 식단 카드 출력
date_key = d.strftime("%Y-%m-%d")
day_meals = meal_data.get(date_key, {})
meal_info = day_meals.get(st.session_state.selected_meal, {"menu": "정보 없음", "side": "식단 정보가 등록되지 않았습니다."})
sel_color = color_theme[st.session_state.selected_meal]

st.markdown(f"""
    <div class="menu-card" style="--c: {sel_color};">
        <div style="font-size: 26px; font-weight: 800; color: #111; margin-bottom: 12px;">{meal_info['menu']}</div>
        <div style="height: 1px; background: #eee; width: 30%; margin: 0 auto;"></div>
        <div style="color: #444; font-size: 16px; margin-top: 15px; line-height: 1.5; word-break: keep-all;">{meal_info['side']}</div>
    </div>
""", unsafe_allow_html=True)

# 탭 버튼 UI
st.markdown('<div class="tab-wrap">' + "".join([f'<div class="tab-item" style="background:{c}; opacity:{"1" if m==st.session_state.selected_meal else "0.3"};">{m}</div>' for m,c in color_theme.items()]) + '</div>', unsafe_allow_html=True)

selected = st.radio("select", options=list(color_theme.keys()), index=list(color_theme.keys()).index(st.session_state.selected_meal), horizontal=True, label_visibility="collapsed")
if selected != st.session_state.selected_meal:
    st.session_state.selected_meal = selected
    st.rerun()

# 4. 시간 메시지 로직
msg = "💡 식단 정보를 확인 중입니다."
if st.session_state.selected_meal in meal_times:
    s_t, e_t = meal_times[st.session_state.selected_meal]
    t_dt_s = datetime.combine(d, s_t).replace(tzinfo=KST)
    t_dt_e = datetime.combine(d, e_t).replace(tzinfo=KST)

    if d < curr_date:
        msg = "🚩 이미 배식이 종료된 식단입니다."
    elif d > curr_date:
        msg = f"🗓️ {d.strftime('%m/%d')} 배식 예정인 식단입니다."
    else:
        if now < t_dt_s:
            diff = t_dt_s - now
            msg = f"⏳ {st.session_state.selected_meal} 시작까지 {diff.seconds//3600}시간 {(diff.seconds%3600)//60}분 남음"
        elif now <= t_dt_e:
            msg = f"🍴 {st.session_state.selected_meal} 배식 중! 종료까지 {((t_dt_e-now).seconds%3600)//60}분 남음"
        else:
            msg = "🚩 이미 배식이 종료된 식단입니다."

st.markdown(f'<div class="msg-box">{msg}</div>', unsafe_allow_html=True)
