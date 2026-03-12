import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 모든 표의 너비를 동일하게 강제 고정
st.markdown("""
<style>
    .main-title { font-size: 22px; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .date-header { font-size: 18px; font-weight: 800; color: #1E3A5F; margin-top: 30px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 15px; font-weight: 700; margin: 15px 0 5px 0; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    /* 테이블 레이아웃 강제 고정 */
    .fixed-table {
        width: 100% !important;
        table-layout: fixed !important; /* 이 설정이 있어야 너비가 고정됩니다 */
        border-collapse: collapse;
        margin-bottom: 10px;
    }
    .fixed-table th, .fixed-table td {
        border: 1px solid #dee2e6;
        padding: 8px 4px;
        text-align: center;
        vertical-align: middle;
        font-size: 12px;
        word-break: break-all; /* 내용이 길면 줄바꿈 */
        overflow: hidden;
    }
    .fixed-table th { background-color: #f8f9fa; font-weight: bold; }

    /* 모바일 대응: 화면이 작아지면 폰트 추가 축소 */
    @media only screen and (max-width: 768px) {
        .fixed-table th, .fixed-table td { font-size: 11px !important; padding: 6px 2px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (기존 로직 동일)
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

# 4. 출력 로직
st.sidebar.title("📅 설정")
date_input = st.sidebar.date_input("조회 날짜", value=now_today)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER[:3])

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

df = get_data(date_input)

if not df.empty:
    st.markdown(f'<div class="date-header">📅 {date_input} ({df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
    
    for bu in selected_bu:
        bu_df = df[df['건물명'] == bu]
        if not bu_df.empty:
            st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
            
            # 각 컬럼의 너비를 %로 고정하여 모든 표를 동일하게 만듦
            html_table = f"""
            <table class="fixed-table">
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
                html_table += f"""
                    <tr>
                        <td>{r['장소']}</td>
                        <td>{r['시간']}</td>
                        <td style="text-align: left; padding-left: 8px;">{r['행사명']}</td>
                        <td>{r['인원']}</td>
                        <td>{r['부서']}</td>
                        <td>{r['상태']}</td>
                    </tr>
                """
            html_table += "</tbody></table>"
            st.write(html_table, unsafe_allow_html=True)
else:
    st.info("조회된 데이터가 없습니다.")
