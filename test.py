import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 줌 기능 (관리자 필수 지시)
st.set_page_config(page_title="성의교정 실시간 대관 현황", layout="wide")
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">', unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일: 여백 제거 및 버튼 강조
st.markdown("""
<style>
    /* 상단 여백 제거 */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; }
    .main-title { font-size: 1.8rem !important; font-weight: 800; color: #1e3a5f; text-align: center; margin: 0 0 10px 0; }
    
    /* 버튼 및 헤더 스타일 */
    .date-header { background: #4a4a4a; color: white; padding: 10px; border-radius: 6px; margin: 10px 0; font-weight: 700; font-size: 1rem; text-align: center; }
    .bu-row { display: flex; align-items: center; justify-content: space-between; margin-top: 15px; border-bottom: 2px solid #1e3a5f; padding-bottom: 5px; }
    .bu-header { font-size: 1.1rem !important; font-weight: 800; color: #1e3a5f; }
    
    /* 모바일 레이아웃 그리드 */
    .event-shell { border-bottom: 1px solid #eee; padding: 10px 0; }
    .row-main { display: grid; grid-template-columns: 5.2fr 3.5fr 1.3fr; align-items: center; gap: 5px; width: 100%; }
    .col-place { font-weight: 700; color: #1e3a5f; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .col-time { font-size: 11px; color: #e74c3c; font-weight: 700; text-align: center; }
    .col-status { font-size: 11px; font-weight: 900; text-align: right; color: #27ae60; }
    .row-sub { font-size: 10.5px; color: #7f8c8d; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return "{0}조".format(['A', 'B', 'C'][diff % 3])

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            if start_date <= s_dt <= end_date:
                if not allowed or str(s_dt.isoweekday()) in allowed:
                    rows.append({
                        'full_date': s_dt.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': "{0}~{1}".format(item.get('startTime', ''), item.get('endTime', '')),
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '부스': str(item.get('boothCount', '0')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def create_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('현황')
        cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'shrink': True})
        for i in range(100): worksheet.set_row(i, 35) # 행 높이 35 고수
        df.to_excel(writer, index=False, sheet_name='현황')
    return output.getvalue()

# --- 메인 UI 시작 ---
st.markdown('<div class="main-title">🏢 실시간 대관 현황</div>', unsafe_allow_html=True)

# 1. 기간 검색 및 모드 선택 (상단 여백 없이 배치)
c1, c2, c3 = st.columns([1.5, 1.5, 1])
with c1: start_d = st.date_input("시작일", value=now_today)
with c2: end_d = st.date_input("종료일", value=now_today)
with c3: view_mode = st.radio("보기 모드", ["모바일", "PC"], horizontal=True)

df = get_data(start_d, end_d)

# 2. 엑셀 다운로드 (메인 상단 배치)
if not df.empty:
    st.download_button("📊 조회 결과 엑셀 다운로드", data=create_excel(df), 
                       file_name=f"대관현황_{start_d}_{end_d}.xlsx", use_container_width=True)

# 3. 결과 출력
if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-header">🗓️ {d_str} | {get_shift(datetime.strptime(d_str, "%Y-%m-%d").date())}</div>', unsafe_allow_html=True)
        for bu in BUILDING_ORDER:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-row"><span class="bu-header">🏢 {bu}</span></div>', unsafe_allow_html=True)
                if view_mode == "PC":
                    st.table(b_df[['장소', '시간', '행사명', '부서', '부스', '상태']])
                else:
                    for _, row in b_df.iterrows():
                        st.markdown(f"""
                        <div class="event-shell">
                            <div class="row-main">
                                <div class="col-place">📍 {row['장소']}</div>
                                <div class="col-time">🕒 {row['시간']}</div>
                                <div class="col-status">{row['상태']}</div>
                            </div>
                            <div class="row-sub">📄 {row['행사명']} ({row['부서']}, {row['인원']}명, 부스 {row['부스']}개)</div>
                        </div>
                        """, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
