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

# 2. CSS 설정 (세로 모드 스크롤 제거 및 가변 폭 적용)
st.markdown("""
<style>
    /* 전체 레이아웃: 가로 스크롤 방지 */
    html, body, [data-testid="stAppViewContainer"] { 
        max-width: 100vw; 
        overflow-x: hidden !important; 
    }
    
    .main-title { font-size: 14px !important; font-weight: 800; text-align: center; margin-bottom: 5px; }
    .date-header { font-size: 10px !important; font-weight: bold; background-color: #f0f2f6; padding: 2px 5px; border-left: 3px solid #2e5077; margin-top: 8px; }
    .bu-header { font-size: 9.5px !important; font-weight: bold; margin: 4px 0 1px 0; border-left: 2px solid #2e5077; padding-left: 4px; }
    
    /* [핵심] 테이블 컨테이너: 화면을 넘지 않도록 강제 설정 */
    .t-container { width: 100% !important; overflow-x: hidden !important; }
    
    /* 테이블 스타일: min-width를 제거하여 화면에 맞게 수축 */
    table { 
        width: 100% !important; 
        border-collapse: collapse; 
        table-layout: fixed; /* 픽셀이 아닌 비율로 작동 */
        border: 1px solid #dee2e6;
    }
    
    th, td { 
        border: 1px solid #dee2e6; 
        padding: 2px 0.5px !important; 
        font-size: 8.5px !important; /* 세로 모드 가독성을 위해 살짝 축소 */
        line-height: 1.1; 
        word-break: break-all; 
        text-align: center; 
        vertical-align: middle; 
    }
    
    th { background-color: #f8f9fa; font-weight: bold; height: 18px; }
    
    /* [최종 비율 배분] 세로 모드 최적화 (총합 100%) */
    .w-place { width: 18%; }    /* 장소 */
    .w-time  { width: 15%; }    /* 시간 (두 줄 방지 마지노선) */
    .w-event { width: 40%; }    /* 행사명 */
    .w-count { width: 6%; }     /* 인원 */
    .w-dept  { width: 15%; }    /* 부서 */
    .w-stat  { width: 6%; }     /* 상태 */
    
    .left { text-align: left !important; padding-left: 2px !important; }

    /* 모바일에서 사이드바 여백 제거 */
    [data-testid="stSidebar"] { min-width: 200px !important; max-width: 250px !important; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (생략 없이 동일 유지)
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

# 4. 필터 및 출력
s_day = st.sidebar.date_input("시작", value=now_today)
e_day = st.sidebar.date_input("종료", value=s_day)
selected_bu = st.sidebar.multiselect("건물", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)
df = get_clean_data(s_day, e_day)

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
