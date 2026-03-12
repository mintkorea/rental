import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (가로 여백 최소화)
st.set_page_config(page_title="대관 현황", layout="centered") 

# 모바일 가독성을 위한 커스텀 스타일 (표 내부 줄바꿈 허용)
st.markdown("""
    <style>
    ._container_1p1n3_1 { padding: 0.5rem; }
    [data-testid="stDataFrame"] { width: 100% !important; }
    td { white-space: normal !important; word-break: break-all !important; }
    </style>
    """, unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 수집 및 allowDay 필터링
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        target_weekday = target_date.isoweekday() 

        for item in raw:
            # allowDay 체크 (요일 필터링)
            allow_days = str(item.get('allowDay', ''))
            if allow_days and allow_days != 'None' and str(target_weekday) not in allow_days:
                continue

            rows.append({
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '인원': f"{item.get('peopleCount', '0')}명",
                '상태': '확정' if item.get('status') == 'Y' else '대기',
                '_tm': item.get('startTime', '00:00')
            })
        
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        return df.sort_values(by=['b_idx', '_tm'])
    except: return pd.DataFrame()

# 3. 화면 구성
st.title(f"📅 {now_today.strftime('%m/%d')} 대관")

date_in = st.date_input("날짜 변경", value=now_today)
df = get_data(date_in)

if not df.empty:
    for b_name in BUILDING_ORDER:
        b_data = df[df['건물명'] == b_name]
        
        st.markdown(f"#### 📍 {b_name}")
        
        if not b_data.empty:
            # [좌우 스크롤 방지 핵심] 
            # 1. '장소'를 위로 빼고 '시간/행사명/인원'만 표에 남기거나,
            # 2. 모바일 너비에 맞춰 핵심 3개 열만 노출
            display_df = b_data[['장소', '시간', '행사명']] 
            
            # st.table은 스크롤 없이 모든 텍스트를 줄바꿈해서 보여줍니다.
            st.table(display_df) 
        else:
            st.caption("대관 내역 없음")
else:
    st.info("조회된 데이터가 없습니다.")
