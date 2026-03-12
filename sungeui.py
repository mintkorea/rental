import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 모든 표의 너비와 폰트를 강제 고정
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 10px 0; margin-top: 25px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 15px; margin-bottom: 8px; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed !important; min-width: 600px; border: 1px solid #dee2e6; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 8px 2px; font-size: 12px; font-weight: bold; text-align: center; }
    td { border: 1px solid #eee; padding: 8px 4px; font-size: 12px; text-align: center; vertical-align: middle; word-break: break-all; }

    @media only screen and (max-width: 768px) {
        th, td { font-size: 11px !important; padding: 6px 2px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (기존 로직)
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            rows.append({
                '요일': ['월','화','수','목','금','토','일'][target_date.weekday()],
                'full_date': target_date.strftime('%Y-%m-%d'),
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', ''), 
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', ''), 
                '인원': item.get('peopleCount', ''),
                '부서': item.get('mgDeptNm', ''),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 메인 출력 로직
st.sidebar.title("📅 설정")
date_input = st.sidebar.date_input("조회 날짜", value=now_today)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

df = get_data(date_input)

if not df.empty:
    st.markdown(f'<div class="date-header">📅 {date_input} ({df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
    
    for bu in selected_bu:
        bu_df = df[df['건물명'] == bu]
        if not bu_df.empty:
            st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
            
            # HTML 코드를 깔끔하게 한 번에 렌더링 (셸 너비 고정)
            table_html = f"""
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 15%;">장소</th>
                            <th style="width: 15%;">시간</th>
                            <th style="width: 38%;">행사명</th>
                            <th style="width: 8%;">인원</th>
                            <th style="width: 16%;">부서</th>
                            <th style="width: 8%;">상태</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for _, r in bu_df.iterrows():
                table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
            
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("조회된 데이터가 없습니다.")
