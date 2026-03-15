import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 줌(Zoom) 기능 활성화
st.set_page_config(page_title="성의교정 실시간 대관 현황", layout="wide")
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">', unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일: 레이아웃 최적화
st.markdown("""
<style>
    .main-title { font-size: 2rem !important; font-weight: 800; color: #1e3a5f; text-align: center; margin-bottom: 10px; }
    .date-header { background: #4a4a4a; color: white; padding: 10px; border-radius: 6px; margin: 20px 0 10px 0; font-weight: 700; font-size: 1.1rem; text-align: center; }
    .bu-row { display: flex; align-items: center; justify-content: space-between; margin-top: 20px; border-bottom: 2px solid #1e3a5f; padding-bottom: 5px; }
    .bu-header { font-size: 1.15rem !important; font-weight: 800; color: #1e3a5f; }
    .bu-badge { font-size: 10px; background: #f0f2f6; padding: 2px 8px; border-radius: 10px; font-weight: bold; }
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 0; }
    .row-main { display: grid; grid-template-columns: 5fr 3.5fr 1.5fr; align-items: center; gap: 5px; width: 100%; }
    .col-place { font-weight: 800; color: #1e3a5f; font-size: 14px; }
    .col-time { font-size: 11.5px; color: #e74c3c; font-weight: 700; text-align: center; }
    .col-status { font-size: 12px; font-weight: 900; text-align: right; color: #27ae60; }
    .row-sub { font-size: 11px; color: #7f8c8d; margin-top: 5px; line-height: 1.4; }
    div.stDownloadButton > button { width: 100% !important; background-color: #1e3a5f !important; color: white !important; font-weight: bold; }
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
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': "{0}~{1}".format(item.get('startTime', ''), item.get('endTime', '')),
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '부스': str(item.get('boothCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('대관현황')
        cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'shrink': True})
        hdr_fmt = workbook.add_format({'bold': True, 'bg_color': '#333333', 'font_color': 'white', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        curr_row = 0
        for d_str in sorted(df['full_date'].unique()):
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(datetime.strptime(d_str, '%Y-%m-%d').date())}", hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", cell_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            for c, val in enumerate([r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['부스'], r['상태']]):
                                worksheet.write(curr_row, c, val, cell_fmt)
                            curr_row += 1
    return output.getvalue()

# 4. 메인 화면 구성
st.markdown('<div class="main-title">🏢 실시간 대관 현황</div>', unsafe_allow_html=True)

# 기간 검색 기능 배치
col1, col2 = st.columns(2)
with col1:
    start_d = st.date_input("조회 시작일", value=now_today)
with col2:
    end_d = st.date_input("조회 종료일", value=now_today)

df = get_data(start_d, end_d)

# 엑셀 다운로드 버튼을 메인 상단에 배치
if not df.empty:
    st.download_button(
        label="📊 조회 결과 엑셀 파일 다운로드",
        data=create_formatted_excel(df, BUILDING_ORDER),
        file_name=f"대관현황_{start_d}_{end_d}.xlsx",
        use_container_width=True
    )

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-header">🗓️ {d_str} | {get_shift(datetime.strptime(d_str, "%Y-%m-%d").date())}</div>', unsafe_allow_html=True)
        for bu in BUILDING_ORDER:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-row"><span class="bu-header">🏢 {bu}</span><span class="bu-badge">총 {len(b_df)}건</span></div>', unsafe_allow_html=True)
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
    st.info("선택한 기간에 등록된 대관 내역이 없습니다.")
