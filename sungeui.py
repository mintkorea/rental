# 3. 기간 대관 및 요일 선택 UI
st.subheader("🗓️ 기간 대관 설정")

col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작일", now_today)
    end_date = st.date_input("종료일", now_today + timedelta(days=7))

with col2:
    # 요일 선택 (다중 선택 가능)
    target_days = st.multiselect(
        "반복할 요일 선택",
        ["월", "화", "수", "목", "금", "토", "일"],
        default=["월", "화", "수", "목", "금"]
    )

# 4. 요일 적용 로직 (핵심 복구 구간)
def get_selected_dates(start, end, weekdays):
    """
    선택된 기간 내에서 특정 요일에 해당하는 날짜 리스트 반환
    """
    day_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    selected_indices = [day_map[d] for d in weekdays]
    
    date_list = []
    curr = start
    while curr <= end:
        if curr.weekday() in selected_indices:
            date_list.append(curr)
        curr += timedelta(days=1)
    return date_list

# 버튼 클릭 시 실행
if st.button("기간 대관 일정 생성"):
    if not target_days:
        st.warning("최소 하나 이상의 요일을 선택해주세요.")
    else:
        final_dates = get_selected_dates(start_date, end_date, target_days)
        
        if final_dates:
            st.success(f"총 {len(final_dates)}개의 날짜가 추출되었습니다.")
            
            # 추출된 날짜를 데이터프레임으로 변환 (예시)
            df_dates = pd.DataFrame({
                "날짜": [d.strftime("%Y-%m-%d") for d in final_dates],
                "요일": [target_days[["월","화","수","목","금","토","일"].index(d.weekday())] for d in final_dates] # 인덱스 역산
            })
            
            # 모바일 가독성을 위해 넓게 표시
            st.dataframe(df_dates, use_container_width=True)
            
            # 이후 이 final_dates 리스트를 API 요청이나 DB 저장 로직에 전달하시면 됩니다.
        else:
            st.error("해당 기간 내에 선택하신 요일이 없습니다.")
