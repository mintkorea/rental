import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="대관 통합 조회", layout="wide")

# 2. 데이터 가져오기 (가장 단순한 형태)
@st.cache_data(ttl=5)
def get_raw_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        # 서버에서 받은 원본 데이터 리스트 추출
        data_list = res.json().get('res', [])
        return pd.DataFrame(data_list)
    except Exception as e:
        st.error(f"서버 통신 에러: {e}")
        return pd.DataFrame()

# 3. 메인 화면
st.title("🏫 성의교정 데이터 수집 테스트")

# 사이드바 설정
KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST).date()

with st.sidebar:
    start_date = st.date_input("시작일", value=today)
    end_date = st.date_input("종료일", value=today + timedelta(days=7))

# 실행
raw_df = get_raw_data(start_date, end_date)

if not raw_df.empty:
    st.success(f"총 {len(raw_df)}건의 데이터를 발견했습니다!")
    
    # 가독성을 위해 주요 열만 정리해서 출력
    display_cols = ['startDt', 'buNm', 'placeNm', 'startTime', 'endTime', 'eventNm', 'mgDeptNm']
    # 실제 서버에서 주는 열 이름이 다를 수 있으므로 존재하는 열만 필터링
    actual_cols = [c for c in display_cols if c in raw_df.columns]
    
    st.dataframe(raw_df[actual_cols], use_container_width=True)
    
    # 전체 데이터 구조 확인용 (디버깅)
    with st.expander("서버 응답 원본 데이터 보기"):
        st.write(raw_df)
else:
    st.warning("학교 서버에서 데이터를 하나도 보내주지 않고 있습니다. 날짜 범위를 더 넓혀보세요.")
