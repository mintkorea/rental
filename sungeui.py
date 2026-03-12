import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 인쇄를 위한 초강력 CSS (모든 컨테이너 해제)
st.markdown("""
<style>
    /* 웹 화면 스타일 */
    .report-table { width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 30px; }
    .report-table th { background-color: #f2f2f2; border: 1px solid #aaa; padding: 8px; text-align: center; }
    .report-table td { border: 1px solid #aaa; padding: 8px; text-align: center; }
    .day-title { font-size: 18px; font-weight: bold; background: #e3e3e3; padding: 10px; margin-top: 20px; border: 1px solid #aaa; }
    .bu-title { font-size: 15px; font-weight: bold; padding: 5px; margin-top: 10px; border-left: 5px solid #2e5077; }

    /* [핵심] 인쇄 시 1페이지 제한 해제 */
    @media print {
        html, body, .stApp, .main, .block-container, [data-testid="stVerticalBlock"] {
            display: block !important;
            height: auto !important;
            overflow: visible !important;
        }
        [data-testid="stSidebar"], header, .stButton { display: none !important; } /* 인쇄 시 제외 */
        
        .report-table { page-break-inside: auto; }
        .report-table tr { page-break-inside: avoid; page-break-after: auto; }
        .day-title { page-break-after: avoid; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 로직
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
            s, e = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = max(s_date, s)
            while curr <= min(e_date, e):
                rows.append({
                    '날짜': curr.strftime('%Y-%m-%d'),
                    '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                    '건물': item.get('buNm', '').strip(),
                    '장소': item.get('placeNm', '').strip(),
                    '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                    '행사명': item.get('eventNm', '').strip(),
                    '인원': item.get('peopleCount', ''),
                    '부서': item.get('mgDeptNm', ''),
                    '상태': '확정' if item.get('status') == 'Y' else '대기'
                })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates()
    except: return pd.DataFrame()

# 4. 사이드바 제어
with st.sidebar:
    st.title("🔎 필터")
    s_day = st.date_input("시작일", value=now_today)
    e_day = st.date_input("종료일", value=s_day + timedelta(days=2))
    buildings = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
    selected = st.multiselect("건물 선택", options=buildings, default=["성의회관", "의생명산업연구원"])

# 5. 본문 출력 (인쇄 최적화 HTML 방식)
df = get_data(s_day, e_day)
st.markdown(f'<h1 style="text-align:center;">🏫 성의교정 대관 현황 ({s_day} ~ {e_day})</h1>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물'].isin(selected)]
    for d in sorted(f_df['날짜'].unique()):
        day_df = f_df[f_df['날짜'] == d]
        st.markdown(f'<div class="day-title">📅 {d} ({day_df.iloc[0]["요일"]})</div>', unsafe_allow_html=True)
        
        for bu in buildings:
            bu_df = day_df[day_df['건물'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="bu-title">🏢 {bu}</div>', unsafe_allow_html=True)
                html = '<table class="report-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>인원</th><th>부서</th><th>상태</th></tr></thead><tbody>'
                for _, r in bu_df.iterrows():
                    html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                html += "</tbody></table>"
                st.markdown(html, unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
