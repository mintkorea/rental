import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 텍스트 가독성 및 줌 최적화 CSS
st.markdown("""
<style>
    /* 줌을 막는 모든 요소를 제거하고 텍스트 가독성 강조 */
    .rent-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 10px;
        background-color: #f9f9f9;
        font-size: 16px; /* 모바일에서 보기 좋게 크게 설정 */
    }
    .rent-time { color: #d63384; font-weight: bold; font-size: 17px; }
    .rent-place { color: #007bff; font-weight: bold; }
    .rent-event { font-size: 18px; font-weight: 800; margin: 5px 0; }
    .rent-dept { color: #666; font-size: 14px; }
    .day-header { font-size: 20px; font-weight: bold; border-left: 5px solid #2e5077; padding-left: 10px; margin: 20px 0 10px 0; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (성공했던 로직 동일 유지)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'w_num': curr.weekday(),
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', ''), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', ''), 
                        '부서': item.get('mgDeptNm', ''),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 4. 화면 출력 (표 대신 카드/리스트 방식)
s_date = st.sidebar.date_input("시작일", now_today)
e_date = st.sidebar.date_input("종료일", s_date + timedelta(days=7))
target_bu = st.sidebar.multiselect("건물 선택", BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(s_date, e_date)

st.title("🏫 성의교정 대관 현황")

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        st.markdown(f'<div class="day-header">📅 {date} ({day_df.iloc[0]["요일"]})</div>', unsafe_allow_html=True)
        
        for bu in target_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.subheader(f"🏢 {bu}")
                for _, r in bu_df.iterrows():
                    # 표가 아닌 텍스트 기반 카드로 출력하여 줌(확대)을 자유롭게 만듦
                    st.markdown(f"""
                    <div class="rent-card">
                        <span class="rent-time">⏱ {r['시간']}</span> | <span class="rent-place">📍 {r['장소']}</span>
                        <div class="rent-event">🏷 {r['행사명']}</div>
                        <div class="rent-dept">👤 {r['부서']} ({r['상태']})</div>
                    </div>
                    """, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
