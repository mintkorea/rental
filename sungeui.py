import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

# 1. 페이지 설정: PC에서도 너무 퍼지지 않게 centered로 변경
st.set_page_config(page_title="성의교정 대관 현황", layout="centered", initial_sidebar_state="expanded")

# 2. 스타일 시트: 모바일에서 표를 숨기고 카드 형태로 강제 변환
st.markdown("""
    <style>
    /* 모바일 가독성: 표를 리스트 형태로 변환하는 느낌 부여 */
    [data-testid="stTable"] { font-size: 14px; width: 100%; }
    th { background-color: #f0f2f6 !important; }
    /* 행사명이 길어도 무조건 아래로 줄바꿈 */
    td { white-space: normal !important; word-break: break-all !important; vertical-align: middle !important; }
    </style>
    """, unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

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
            # allowDay 요일 필터링 (기간 대관 대응)
            allow_days = str(item.get('allowDay', ''))
            if allow_days and allow_days != 'None' and str(target_weekday) not in allow_days:
                continue
            
            rows.append({
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '_tm': item.get('startTime', '00:00')
            })
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        return df.sort_values(by=['b_idx', '_tm'])
    except: return pd.DataFrame()

# 3. 사이드바 (날짜/건물 필터)
with st.sidebar:
    st.header("🔍 조회 설정")
    date_in = st.date_input("날짜 선택", value=now_today)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 메인 화면
st.header(f"🗓️ {date_in.strftime('%m/%d')} 대관 내역")

df = get_data(date_in)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    
    for b_name in BUILDING_ORDER:
        if b_name in sel_bu:
            b_data = f_df[f_df['건물명'] == b_name]
            
            # 건물명 강조
            st.markdown(f"#### 📍 {b_name}")
            
            if not b_data.empty:
                # [스크롤 해결 핵심] st.dataframe 대신 st.table 사용
                # st.table은 너비에 맞춰 텍스트를 자동으로 줄바꿈(Wrap)하며, 
                # 화면을 벗어나는 가로 스크롤을 원천 차단합니다.
                display_df = b_data[['장소', '시간', '행사명']].copy()
                st.table(display_df)
            else:
                st.info(f"조회된 {b_name} 대관 내역이 없습니다.")
else:
    st.warning("선택한 날짜에 전체 대관 데이터가 없습니다.")
