# --- 1. 사이드바 설정 (변수 정의가 먼저 되어야 함) ---
with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("모드", ["모바일", "PC"], horizontal=True)

# --- 2. 메인 화면 타이틀 ---
st.markdown('<div class="main-title"><span>📋</span> 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

# --- 3. 데이터 가져오기 (s_date, e_date가 정의된 후 호출!) ---
df = get_data(s_date, e_date)

# --- 4. 이후 데이터 표시 로직 ---
if not df.empty:
    # (... 기존 코드 ...)
