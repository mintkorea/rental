import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

# 1. 기초 설정 및 시간대
KST = ZoneInfo("Asia/Seoul")
def get_now(): return datetime.now(KST)

st.set_page_config(page_title="성의교정 식단 가이드", page_icon="🍴", layout="centered")

# [데이터 로딩] 캐싱 적용
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

with st.spinner('최신 정보를 가져오고 있습니다...'):
    meal_data = load_meal_data(CSV_URL)

now = get_now()
curr_date = now.date()

# 세션 상태 초기화
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

# URL 파라미터 처리
params = st.query_params
if "d" in params:
    try:
        st.session_state.target_date = datetime.strptime(params["d"], "%Y-%m-%d").date()
    except: pass

# 3. 스타일 정의 (모바일 최적화)
st.markdown(f"""
<style>
    .block-container {{ padding: 1rem 1.2rem !important; max-width: 500px !important; }}
    header {{ visibility: hidden; }}
    
    /* 날짜 헤더 */
    .date-box {{ text-align: center; background: #F8FAFF; padding: 15px 10px 8px; border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; }}
    .res-sub-title {{ font-size: 18px !important; font-weight: 700; color: #333; }}
    .sat {{ color: #0000FF !important; }} .sun {{ color: #FF0000 !important; }}
    
    /* 네비게이션 바 */
    .nav-bar {{ display: flex; width: 100%; background: white; border: 1px solid #D1D9E6; border-radius: 0 0 10px 10px; margin-bottom: 20px; }}
    .nav-btn {{ flex: 1; text-align: center; padding: 10px 0; text-decoration: none; color: #1E3A5F; font-weight: bold; font-size: 13px; border-right: 1px solid #F0F0F0; }}
    
    /* 식단 카드 */
    .menu-card {{ border-top: 5px solid var(--c); border-radius: 15px; padding: 30px 15px; text-align: center; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-top: 10px; }}
    
    /* 탭 스타일 조정 (모바일 가로 유지) */
    div[data-testid="stTabs"] button {{
        flex: 1;
        font-size: 14px !important;
        font-weight: 800 !important;
    }}
    
    .msg-box {{ text-align: center; background: #f8f9fa; padding: 12px; border-radius: 12px; font-size: 14px; font-weight: bold; color: #555; margin-top: 15px; }}
</style>
""", unsafe_allow_html=True)

# 헤더 출력
st.markdown('<div style="text-align:center; padding-bottom:10px;"><span style="font-size:30px; font-weight:800; color:#1E3A5F;">🍽️ 성의교정 식단</span></div>', unsafe_allow_html=True)

# 날짜 네비게이션
d = st.session_state.target_date
shift = get_work_shift(d)
w_list = ["월","화","수","목","금","토","일"]
w_str = w_list[d.weekday()]
w_class = "sat" if d.weekday() == 5 else ("sun" if d.weekday() == 6 else "")

st.markdown(f"""
<div class="date-box">
    <span class="res-sub-title">{d.strftime("%Y.%m.%d")}.<span class="{w_class}">({w_str})</span>
    <span style="background:{shift['bg']}; color:white; padding:2px 10px; border-radius:12px; font-size:14px; margin-left:5px;">{shift['n']}</span></span>
</div>
<div class="nav-bar">
    <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-btn">◀ 이전</a>
    <a href="./?d={curr_date.strftime('%Y-%m-%d')}" target="_self" class="nav-btn">오늘</a>
    <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-btn">다음 ▶</a>
</div>
""", unsafe_allow_html=True)

# 4. 식단 선택 탭 (Radio 대신 Tabs 사용)
color_theme = {"조식": "#E95444", "중식": "#8BC34A", "석식": "#4A90E2", "간편식": "#F1A33B"}
meal_options = list(color_theme.keys())
curr_idx = meal_options.index(st.session_state.selected_meal)

# 모바일 가로 배치를 보장하는 탭 생성
tabs = st.tabs(meal_options)

# 각 탭 클릭 이벤트 처리
for i, tab in enumerate(tabs):
    if i == curr_idx:
        with tab:
            # 현재 선택된 탭일 때만 식단 카드 렌더링
            date_key = d.strftime("%Y-%m-%d")
            day_meals = meal_data.get(date_key, {})
            meal_info = day_meals.get(meal_options[i], {"menu": "정보 없음", "side": "식단 정보가 등록되지 않았습니다."})
            sel_color = color_theme[meal_options[i]]
            
            st.markdown(f"""
                <div class="menu-card" style="--c: {sel_color};">
                    <div style="font-size: 24px; font-weight: 800; color: #111; margin-bottom: 12px;">{meal_info['menu']}</div>
                    <div style="height: 1px; background: #eee; width: 30%; margin: 0 auto;"></div>
                    <div style="color: #444; font-size: 16px; margin-top: 15px; line-height: 1.6; word-break: keep-all;">{meal_info['side']}</div>
                </div>
            """, unsafe_allow_html=True)
    else:
        with tab:
            # 다른 탭을 누르면 세션 상태 업데이트 후 재실행
            st.session_state.selected_meal = meal_options[i]
            st.rerun()

# 5. 시간 메시지 로직
meal_times = {"조식": (time(7, 0), time(9, 0)), "중식": (time(11, 20), time(14, 0)), "석식": (time(17, 20), time(19, 20))}
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
            msg = f"⏳ 시작까지 {diff.seconds//3600}시간 {(diff.seconds%3600)//60}분 남음"
        elif now <= t_dt_e:
            msg = f"🍴 현재 배식 중! 종료까지 {((t_dt_e-now).seconds%3600)//60}분 남음"
        else:
            msg = "🚩 금일 배식이 종료되었습니다."

st.markdown(f'<div class="msg-box">{msg}</div>', unsafe_allow_html=True)
