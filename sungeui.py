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

# 2. CSS 설정 (반응형 폰트 및 상하 여백 대폭 확대)
st.markdown("""
<style>
    /* 1. PC/모바일 반응형 기본 폰트 크기 설정 */
    html { font-size: 16px; } 
    
    /* 2. 테이블 가독성 강화 (상하 여백 및 폰트) */
    table { width: 100% !important; border-collapse: collapse; table-layout: fixed; border: 1px solid #dee2e6; }
    
    th { 
        background-color: #f8f9fa; font-weight: bold; 
        height: 35px; /* 헤더 높이 확대 */
        font-size: clamp(10px, 1.2vw, 14px) !important; /* PC에선 크게, 모바일에선 작게 자동조절 */
    }
    
    td { 
        border: 1px solid #dee2e6; 
        padding: 10px 4px !important; /* [수정] 상하 여백을 10px로 대폭 확대 */
        font-size: clamp(9.5px, 1.1vw, 13px) !important; /* PC 화면에서 폰트 크기 자동 확대 */
        line-height: 1.4; 
        word-break: break-all; 
        text-align: center; 
        vertical-align: middle; 
    }
    
    /* 날짜 및 건물 구분선 가독성 */
    .date-header { font-size: clamp(12px, 1.5vw, 16px) !important; font-weight: bold; background-color: #f0f2f6; padding: 8px 12px; border-left: 5px solid #2e5077; margin-top: 20px; }
    .bu-header { font-size: clamp(11px, 1.3vw, 15px) !important; font-weight: bold; margin: 12px 0 5px 0; padding-left: 8px; border-left: 3px solid #2e5077; }
    .left { text-align: left !important; padding-left: 8px !important; }

    /* 3. PDF 및 인쇄 전용 설정 (인쇄 시 폰트 강제 확대) */
    @media print {
        @page { size: A4 landscape; margin: 1cm; }
        [data-testid="stSidebar"], .stButton, .no-print { display: none !important; }
        table { font-size: 11pt !important; width: 100% !important; }
        th, td { padding: 8px 4px !important; border: 1px solid #000 !important; }
        .date-header, .bu-header { background-color: #eee !important; -webkit-print-color-adjust: exact; }
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
    st.title("⚙️ 필터 설정")
    s_day = st.date_input("조회 시작일", value=now_today)
    e_day = st.date_input("조회 종료일", value=s_day + timedelta(days=2))
    selected_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)
    st.markdown("---")
    st.info("💡 **PC 가독성 팁**\n\n화면이 너무 작다면 `Ctrl` + `+` 키를 눌러 브라우저를 확대해 보세요. 표가 깨지지 않고 함께 커집니다.")

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
                    table_html = f"""<table><thead><tr>
                        <th style="width:16%;">장소</th><th style="width:13%;">시간</th><th style="width:41%;">행사명</th>
                        <th style="width:7%;">인원</th><th style="width:16%;">부서</th><th style="width:7%;">상태</th>
                        </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    table_html += "</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다. 기간이나 건물을 다시 설정해 주세요.")
