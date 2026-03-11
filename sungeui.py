import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (반드시 파일 최상단, 다른 st 함수보다 먼저 와야 함)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 기본 변수 설정
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# --- 여기서부터 복구해드린 소스를 넣으세요 ---

# 3. UI 구성
st.subheader("🗓️ 기간 대관 설정")

col1, col2 = st.columns([1, 1]) # PC/모바일 대응 비율
with col1:
    start_date = st.date_input("시작일", now_today)
    end_date = st.date_input("종료일", now_today + timedelta(days=7))

with col2:
    target_days = st.multiselect(
        "반복할 요일 선택",
        ["월", "화", "수", "목", "금", "토", "일"],
        default=["월", "화", "수", "목", "금"]
    )

# 4. 요일 추출 함수
def get_selected_dates(start, end, weekdays):
    day_map = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    selected_indices = [day_map[d] for d in weekdays]
    
    date_list = []
    curr = start
    while curr <= end:
        if curr.weekday() in selected_indices:
            date_list.append(curr)
        curr += timedelta(days=1)
    return date_list

# 실행 버튼
if st.button("추출하기", use_container_width=True): # 모바일 클릭 최적화
    if not target_days:
        st.warning("요일을 선택해주세요.")
    else:
        dates = get_selected_dates(start_date, end_date, target_days)
        st.write(f"추출된 날짜: {len(dates)}개")
        st.dataframe([d.strftime("%Y-%m-%d (%a)") for d in dates], use_container_width=True)
