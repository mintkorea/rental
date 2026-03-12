import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 가로 스크롤 안내 및 테이블 너비 강제 고정
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 10px 0; margin-top: 25px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 15px; margin-bottom: 5px; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    /* 가로 스크롤 안내 문구 스타일 */
    .scroll-hint { font-size: 11px; color: #888; text-align: right; margin-bottom: 5px; }
    
    /* 테이블 컨테이너: 가로 스크롤 보장 */
    .table-container { 
        width: 100%; 
        overflow-x: auto !important; 
        -webkit-overflow-scrolling: touch; 
        margin-bottom: 20px;
        border: 1px solid #eee;
    }
    
    /* 테이블 너비 고정 (모바일에서도 칸이 줄어들지 않음) */
    table { border-collapse: collapse; table-layout: fixed !important; width: 850px !important; }
    th, td { border: 1px solid #dee2e6; padding: 12px 4px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }
    th { background-color: #f8f9fa; font-weight: bold; position: sticky; top: 0; }

    @media only screen and (max-width: 768px) {
        th, td { font-size: 12px !important; padding: 10px 2px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수
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

# 4. 메인 UI
st.sidebar.title("📅 설정")
date_input = st.sidebar.date_input("조회 날짜", value=now_today)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

df = get_data(date_input)

if not df.empty:
    st.markdown(f'<div class="date-header">📅 {date_input}</div>', unsafe_allow_html=True)
    
    for bu in selected_bu:
        bu_df = df[df['건물명'] == bu]
        if not bu_df.empty:
            st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
            st.markdown('<div class="scroll-hint">옆으로 밀어서 보기 ↔</div>', unsafe_allow_html=True)
            
            # 모든 표의 칸 너비를 픽셀(px)로 고정하여 통일감 부여
            table_html = f"""
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 100px;">장소</th>
                            <th style="width: 130px;">시간</th>
                            <th style="width: 330px;">행사명</th>
                            <th style="width: 60px;">인원</th>
                            <th style="width: 150px;">부서</th>
                            <th style="width: 80px;">상태</th>
                        </tr>
                    </thead>
                    <tbody>
            """
            for _, r in bu_df.iterrows():
                table_html += f"""
                    <tr>
                        <td>{r['장소']}</td>
                        <td>{r['시간']}</td>
                        <td style="text-align: left; padding-left: 8px;">{r['행사명']}</td>
                        <td>{r['인원']}</td>
                        <td>{r['부서']}</td>
                        <td>{r['상태']}</td>
                    </tr>"""
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("조회된 데이터가 없습니다.")
