import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정 (줌 활성화 + 폰트/셸 사이즈 축소)
st.markdown("""
<style>
    /* 전체 줌 허용 */
    html, body { min-width: 100%; overflow-x: auto; }
    
    /* 타이틀 및 헤더 사이즈 축소 */
    .main-title { font-size: 18px !important; font-weight: 800; text-align: center; margin-bottom: 10px; }
    .date-header { font-size: 14px !important; font-weight: bold; background-color: #f0f2f6; padding: 5px 10px; border-left: 4px solid #2e5077; margin-top: 15px; }
    .bu-header { font-size: 13px !important; font-weight: bold; margin: 8px 0 3px 0; border-left: 3px solid #2e5077; padding-left: 8px; }
    
    /* 테이블 컨테이너: 가로 스크롤 및 세로 자동 확장 */
    .t-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 15px; }
    
    /* 테이블 스타일: 폰트 및 셸 간격 최소화 */
    table { width: 100%; border-collapse: collapse; min-width: 700px; table-layout: fixed; }
    th, td { border: 1px solid #dee2e6; padding: 4px 2px !important; font-size: 11px !important; line-height: 1.2; word-break: break-all; }
    th { background-color: #f8f9fa; font-weight: bold; height: 25px; }
    
    /* 열 너비 최적화 */
    .w-p { width: 110px; } /* 장소 */
    .w-t { width: 80px; }  /* 시간 */
    .w-e { width: auto; }   /* 행사명 */
    .w-c { width: 35px; }  /* 인원 */
    .w-d { width: 90px; }  /* 부서 */
    .w-s { width: 45px; }  /* 상태 */
    
    .left { text-align: left !important; padding-left: 5px !important; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 정제 (기간 필터링 유지)
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
                return str(t).replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;").replace('"', "&quot;").replace("\n", " ").strip()

            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
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

# 4. 사이드바 UI
st.sidebar.title("📅 설정")
s_day = st.sidebar.date_input("시작일", value=now_today)
e_day = st.sidebar.date_input("종료일", value=s_day)
selected_bu = st.sidebar.multiselect("건물", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_clean_data(s_day, e_day)

# 5. 메인 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(selected_bu)]
    if not f_df.empty:
        for d in sorted(f_df['full_date'].unique()):
            day_df = f_df[f_df['full_date'] == d]
            st.markdown(f'<div class="date-header">📅 {d} ({day_df.iloc[0]["요일"]})</div>', unsafe_allow_html=True)
            
            for bu in BUILDING_ORDER:
                if bu in selected_bu:
                    bu_df = day_df[day_df['건물명'] == bu]
                    if not bu_df.empty:
                        st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                        
                        table_html = """<div class="t-container"><table><thead><tr>
                            <th class="w-p">장소</th><th class="w-t">시간</th><th class="w-e">행사명</th>
                            <th class="w-c">인원</th><th class="w-d">부서</th><th class="w-s">상태</th>
                            </tr></thead><tbody>"""
                        for _, r in bu_df.iterrows():
                            table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                        table_html += "</tbody></table></div>"
                        
                        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.info("선택한 건물의 데이터가 없습니다.")
else:
    st.info("내역이 없습니다.")
