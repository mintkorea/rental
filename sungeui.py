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

# 2. CSS 설정 (헤더 중앙 정렬 및 PDF 출력 최적화)
st.markdown("""
<style>
    /* [수정] 셸 헤더 중앙 정렬 및 테이블 스타일 */
    table { width: 100% !important; border-collapse: collapse; table-layout: fixed; border: 1px solid #dee2e6; }
    
    th { 
        background-color: #f8f9fa !important; 
        font-weight: 800 !important; 
        height: 38px; 
        font-size: clamp(10px, 1.2vw, 14px) !important;
        text-align: center !important; /* [핵심] 헤더 중앙 정렬 */
        vertical-align: middle !important;
        border: 1px solid #dee2e6 !important;
    }
    
    td { 
        border: 1px solid #dee2e6; 
        padding: 10px 4px !important; 
        font-size: clamp(9.5px, 1.1vw, 13px) !important;
        line-height: 1.4; 
        word-break: break-all; 
        text-align: center; 
        vertical-align: middle; 
    }
    
    .date-header { font-size: clamp(12px, 1.5vw, 16px) !important; font-weight: bold; background-color: #f0f2f6; padding: 10px; border-left: 5px solid #2e5077; margin-top: 25px; }
    .bu-header { font-size: clamp(11px, 1.3vw, 15px) !important; font-weight: bold; margin: 15px 0 5px 0; padding-left: 8px; border-left: 3px solid #2e5077; }
    .left { text-align: left !important; padding-left: 10px !important; }

    /* [추가] PDF 및 브라우저 인쇄 최적화 설정 */
    @media print {
        @page { size: A4 landscape; margin: 1cm; }
        /* 사이드바, 버튼, 헤더 등 인쇄 제외 요소 */
        [data-testid="stSidebar"], .stButton, header, footer, .no-print { display: none !important; }
        [data-testid="stAppViewContainer"] { padding: 0 !important; }
        
        /* 인쇄 시 폰트 및 배경색 강제 적용 */
        table { font-size: 10pt !important; width: 100% !important; border: 1px solid #000 !important; }
        th { background-color: #f0f0f0 !important; -webkit-print-color-adjust: exact; color: black !important; border: 1px solid #000 !important; }
        td { padding: 6px 4px !important; border: 1px solid #000 !important; color: black !important; }
        .date-header, .bu-header { background-color: #e9ecef !important; -webkit-print-color-adjust: exact; border: 1px solid #ccc !important; padding: 5px !important; margin-top: 10px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 기간 필터 (동일 유지)
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
                def clean(t):
                    if not t: return ""
                    return str(t).replace("<", "&lt;").replace(">", "&gt;").replace("'", "&#39;").replace('"', "&quot;").strip()
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
    st.title("🔎 대관 조회")
    s_day = st.date_input("조회 시작일", value=now_today)
    e_day = st.date_input("조회 종료일", value=s_day + timedelta(days=2))
    selected_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)
    st.markdown("---")
    st.warning("⚠️ **PDF 저장 안내**\n\n브라우저 우측 상단 메뉴에서 **인쇄(Print)**를 누른 후, 대상을 **'PDF로 저장'**으로 선택해 주세요.")

# 5. 메인 출력
df = get_clean_data(s_day, e_day)
st.markdown('<h1 style="text-align:center; font-size:24px;">🏫 성의교정 대관 현황</h1>', unsafe_allow_html=True)

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
                    table_html = f"""<table>
                        <thead><tr>
                        <th style="width:16%;">장소</th><th style="width:13%;">시간</th><th style="width:41%;">행사명</th>
                        <th style="width:7%;">인원</th><th style="width:16%;">부서</th><th style="width:7%;">상태</th>
                        </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    table_html += "</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
