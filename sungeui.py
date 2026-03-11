# 1. 상단 UI: 건물 선택 및 기간/요일 설정
st.subheader("🏢 시설 대관 조회 설정")

col1, col2 = st.columns([1, 1])
with col1:
    selected_building = st.selectbox("건물 선택", BUILDING_ORDER)
    # 날짜 범위 선택
    date_range = st.date_input("대관 기간 설정", [now_today, now_today + timedelta(days=7)])

with col2:
    # 핵심: allowDay (요일 필터)
    # 사용자가 보고 싶은 요일만 체크
    target_days = st.multiselect(
        "표출할 요일 선택 (allowDay)",
        ["월", "화", "수", "목", "금", "토", "일"],
        default=["월", "화", "수", "목", "금"]
    )

# 2. 필터링 