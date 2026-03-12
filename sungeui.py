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

# 2. CSS 설정 (PDF 인쇄 시 전체 내용 노출 및 헤더 정렬)
st.markdown("""
<style>
    /* 웹 화면 스타일 */
    table { width: 100% !important; border-collapse: collapse; table-layout: fixed; border: 1px solid #dee2e6; margin-bottom: 20px; }
    th { 
        background-color: #f8f9fa !important; font-weight: 800 !important; height: 38px; 
        font-size: clamp(10px, 1.2vw, 14px) !important; text-align: center !important; 
        vertical-align: middle !important; border: 1px solid #dee2e6 !important; 
    }
    td { 
        border: 1px solid #dee2e6; padding: 10px 4px !important; 
        font-size: clamp(9.5px, 1.1vw, 13px) !important; line-height: 1.4; 
        word-break: break-all; text-align: center; vertical-align: middle; 
    }
    .date-header { font-size: clamp(12px, 1.5vw, 16px) !important; font-weight: bold; background-color: #f0f2f6; padding: 10px; border-left: 5px solid #2e5077; margin-top: 25px; }
    .bu-header { font-size: clamp(11px, 1.3vw, 15px) !important; font-weight: bold; margin: 15px 0 5px 0; padding-left: 8px; border-left: 3px solid #2e5077; }
    .left { text-align: left !important; padding-left: 10px !important; }

    /* [핵심] PDF 및 인쇄 시 1페이지만 나오는 현상 방지 설정 */
    @media print {
        /* 1. 스트림릿 기본 레이아웃 제한 해제 */
        [data-testid="stAppViewContainer"], [data-testid="stMainViewContainer"], .main, .block-container {
            display: block !important;
            overflow: visible !important;
            height: auto !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        
        /* 2. 사이드바 및 불필요한 요소 숨기기 */
        [data-testid="stSidebar"], header, footer, .stButton, .no-print { 
            display: none !important; 
        }

        /* 3. 테이블 페이지 끊김 방지 */
        table { 
            page-break-inside: auto !important; 
            width: 100% !important; 
            border: 1px solid #000 !important;
        }
        tr { page-break-inside: avoid !important; page-break-after: auto !important; }
        thead { display: table-header-group !important; } /* 페이지마다 헤더 반복 */
        
        /* 4. 인쇄 전용 가독성 설정 */
        th, td { border: 1px solid #000 !important; color: black !important; font-size: 10pt !important; padding: 6px 4px !important; }
        .date-header, .bu-header { background-color: #e9ecef !important; -webkit-print-color-adjust: exact; border: 1px solid #000 !important; margin-top: 15px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 필터 로직
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
    st.title("🔎 조회 필터")
    s_day = st.date_input("시작일", value=now_today)
    e_day = st.date_input("종료일", value=s_day + timedelta(days=2))
    selected_bu = st.multiselect("건물", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)
    st.markdown("---")
    st.info("💡 **전체 내용 인쇄 방법**\n\n1. `Ctrl + P`를 누릅니다.\n2. 설정에서 **'배경 그래픽'**을 체크하세요.\n3. 대상에서 **'PDF로 저장'**을 선택하면 모든 페이지가 저장됩니다.")

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
    st.info("내역이 없습니다.")
