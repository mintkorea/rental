import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="대관 통합 조회", layout="wide")

# 2. 데이터 수집 (브라우저 우회 헤더 추가)
@st.cache_data(ttl=5)
def get_raw_data_secure(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    
    # 실제 브라우저처럼 보이게 하는 헤더 정보 [중요]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        
        # 응답이 비어있는지 확인
        if not res.text.strip():
            return "empty"
            
        # 응답이 JSON 형식이 맞는지 확인
        try:
            data_json = res.json()
            data_list = data_json.get('res', [])
            return pd.DataFrame(data_list)
        except:
            # JSON이 아니면 서버가 차단 메시지(HTML)를 보낸 것임
            return "html_error"
            
    except Exception as e:
        return f"error: {str(e)}"

# 3. 메인 화면 UI
st.title("🏫 성의교정 데이터 통신 테스트")

KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST).date()

with st.sidebar:
    s_day = st.date_input("시작일", value=today)
    e_day = st.date_input("종료일", value=today + timedelta(days=7))

# 실행 결과 출력
result = get_raw_data_secure(s_day, e_day)

if isinstance(result, pd.DataFrame):
    if not result.empty:
        st.success(f"✅ 성공! {len(result)}건의 데이터를 가져왔습니다.")
        st.dataframe(result, use_container_width=True)
    else:
        st.warning("데이터는 정상 연결되었으나, 해당 기간에 대관 내역이 없습니다.")
elif result == "empty":
    st.error("서버에서 빈 응답을 보냈습니다. (서버 점검 중일 수 있음)")
elif result == "html_error":
    st.error("❌ 서버 차단 발생: 서버가 데이터 대신 에러 페이지를 보냈습니다. 잠시 후 다시 시도해 주세요.")
else:
    st.error(f"통신 실패: {result}")
