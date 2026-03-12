import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정: 사이드바를 항상 펼쳐진 상태로 고정 (initial_sidebar_state="expanded")
st.set_page_config(
    page_title="대관 현황", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 모바일용 강제 스타일: 표의 인덱스 열을 숨기고 텍스트 줄바꿈 강제
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 200px; max-width: 250px; }
    .stDataFrame { width: 100%; }
    /* 표 내부의 긴 텍스트 자동 줄바꿈 */
    div[data-testid="stExpander"] div[role="listitem"] { font_size: 14px; }
    </style>
    """, unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 수집 (allowDay 요일 필터링 적용)
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

# 3. 사이드바 구성 (모바일에서도 바로 보이게 배치)
with st.sidebar:
    st.header("⚙️ 설정")
    date_in = st.date_input("조회 날짜", value=now_today)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    st.write("---")
    st.caption("왼쪽 위 '>>' 화살표를 누르면 이 창을 닫을 수 있습니다.")

# 4. 메인 화면 구성
st.title(f"🗓️ {date_in.strftime('%m/%d')} 대관 내역")

df = get_data(date_in)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    for b_name in BUILDING_ORDER:
        if b_name in sel_bu:
            b_data = f_df[f_df['건물명'] == b_name]
            st.markdown(f"#### 📍 {b_name}")
            if not b_data.empty:
                # [좌우 스크롤 해결] hide_index=True로 왼쪽 숫자 제거
                # 장소/시간/행사명만 딱 맞게 노출
                st.dataframe(
                    b_data[['장소', '시간', '행사명']], 
                    use_container_width=True, 
                    hide_index=True
                )
            else:
                st.caption("대관 내역 없음")
else:
    st.warning("조회된 데이터가 없습니다.")
