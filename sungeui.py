import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정 (세로 모드 극한 압축 및 줌 최적화)
st.markdown("""
<style>
    /* 줌을 해도 표가 깨지지 않고 자연스럽게 확대되도록 설정 */
    html, body { min-width: 100%; overflow-x: auto; }
    
    .main-title { font-size: 14px !important; font-weight: 800; text-align: center; margin-bottom: 5px; }
    .date-header { font-size: 10.5px !important; font-weight: bold; background-color: #f0f2f6; padding: 2px 5px; border-left: 3px solid #2e5077; margin-top: 8px; }
    .bu-header { font-size: 10px !important; font-weight: bold; margin: 4px 0 1px 0; border-left: 2px solid #2e5077; padding-left: 5px; }
    
    /* 테이블 컨테이너: 내부 스크롤을 끄고 브라우저 줌에 맡김 */
    .t-container { width: 100%; overflow: visible !important; }
    
    /* [핵심] 테이블 폭 조정: 세로 모드 대응을 위해 최소 폭을 400px로 낮춤 */
    table { width: 100%; border-collapse: collapse; min-width: 400px; table-layout: fixed; border: 1px solid #dee2e6; }
    th, td { border: 1px solid #dee2e6; padding: 2px 1px !important; font-size: 9px !important; line-height: 1.1; word-break: break-all; text-align: center; vertical-align: middle; }
    th { background-color: #f8f9fa; font-weight: bold; height: 18px; }
    
    /* [최종 너비 배분] 세로 모드에서 스크롤을 줄이기 위한 비율 */
    .w-place { width: 16%; }    /* 장소 */
    .w-time  { width: 13%; }    /* 시간 (두 줄 방지를 위해 최소한의 폭 확보) */
    .w-event { width: 44%; }    /* 행사명 (가장 넓게) */
    .w-count { width: 7%; }     /* 인원 */
    .w-dept  { width: 13%; }    /* 부서 (축소) */
    .w-stat  { width: 7%; }     /* 상태 */
    
    .left { text-align: left !important; padding-left: 3px !important; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (정제 및 필터링)
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
            def clean(t):
                if not t: return ""
                return str(t).replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;").replace('"', "&quot;").strip()
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
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

# 4. UI 구성
s_day = st.sidebar.date_input("시작", value=now_today)
e_day = st.sidebar.date_input("종료", value=s_day)
selected_bu = st.sidebar.multiselect("건물", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_clean_data(s_day, e_day)

# 5. 메인 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

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
                    table_html = f"""<div class="t-container"><table><thead><tr>
                        <th class="w-place">장소</th><th class="w-time">시간</th><th class="w-event">행사명</th>
                        <th class="w-count">인원</th><th class="w-dept">부서</th><th class="w-stat">상태</th>
                        </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    table_html += "</tbody></table></div>"
                    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("내역 없음")
