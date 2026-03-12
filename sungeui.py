import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정 (인쇄 시 높이 제한 완전 해제 및 스크롤 제거)
st.markdown("""
<style>
    /* 웹 화면 가독성 */
    table { width: 100% !important; border-collapse: collapse; table-layout: fixed; border: 1px solid #dee2e6; margin-bottom: 30px; }
    th { background-color: #f8f9fa !important; font-weight: 800; text-align: center !important; height: 38px; border: 1px solid #dee2e6 !important; font-size: 14px; }
    td { border: 1px solid #dee2e6; padding: 10px 4px !important; text-align: center; vertical-align: middle; font-size: 13px; line-height: 1.4; }
    .date-header { font-size: 16px; font-weight: bold; background-color: #f0f2f6; padding: 10px; border-left: 5px solid #2e5077; margin-top: 30px; }
    .bu-header { font-size: 15px; font-weight: bold; margin: 15px 0 5px 0; padding-left: 8px; border-left: 3px solid #2e5077; }
    .left { text-align: left !important; padding-left: 10px !important; }

    /* [핵심] 인쇄 시 1페이지만 나오는 문제 해결 전용 설정 */
    @media print {
        /* 모든 부모 컨테이너의 스크롤 및 높이 제한 해제 */
        html, body, [data-testid="stAppViewContainer"], [data-testid="stMainViewContainer"], .main, .block-container, [data-testid="stVerticalBlock"] {
            display: block !important;
            height: auto !important;
            overflow: visible !important;
            position: static !important;
        }

        /* 인쇄 시 제외 요소 */
        [data-testid="stSidebar"], header, footer, .stButton { display: none !important; }

        /* 테이블 끊김 방지 */
        table { page-break-inside: auto !important; width: 100% !important; }
        tr { page-break-inside: avoid !important; page-break-after: auto !important; }
        thead { display: table-header-group !important; }

        /* 인쇄 폰트 및 배경색 */
        th, td { border: 1px solid #000 !important; color: black !important; font-size: 10pt !important; }
        .date-header, .bu-header { background-color: #eee !important; -webkit-print-color-adjust: exact; border: 1px solid #000 !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 로직 (기간 필터 포함)
@st.cache_data(ttl=60)
def get_clean_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            item_start = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_end = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = max(s_date, item_start)
            last = min(e_date, item_end)
            while curr <= last:
                def clean(t): return str(t).replace("<", "&lt;").replace(">", "&gt;").strip() if t else ""
                rows.append({
                    'full_date': curr.strftime('%Y-%m-%d'),
                    '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                    '건물명': clean(item.get('buNm', '')),
                    '장소': clean(item.get('placeNm', '')),
                    '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                    '행사명': clean(item.get('eventNm', '')),
                    '인원': clean(item.get('peopleCount', '')),
                    '부서': clean(item.get('mgDeptNm', '')),
                    '상태': '확정' if item.get('status') == 'Y' else '대기'
                })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates()
    except: return pd.DataFrame()

# 4. 사이드바
with st.sidebar:
    st.header("⚙️ 필터")
    s_day = st.date_input("시작일", value=now_today)
    e_day = st.date_input("종료일", value=s_day + timedelta(days=2))
    selected_bu = st.multiselect("건물", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

# 5. 메인 출력
df = get_clean_data(s_day, e_day)
st.markdown('<h1 style="text-align:center; font-size:22px;">🏫 성의교정 대관 현황</h1>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(selected_bu)]
    for d in sorted(f_df['full_date'].unique()):
        day_df = f_df[f_df['full_date'] == d]
        st.markdown(f'<div class="date-header">📅 {d} ({day_df.iloc[0]["요일"]})</div>', unsafe_allow_html=True)
        for bu in BUILDING_ORDER:
            if bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                    table_html = f"<table><thead><tr><th style='width:16%;'>장소</th><th style='width:13%;'>시간</th><th style='width:41%;'>행사명</th><th style='width:7%;'>인원</th><th style='width:16%;'>부서</th><th style='width:7%;'>상태</th></tr></thead><tbody>"
                    for _, r in bu_df.iterrows():
                        table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    table_html += "</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
