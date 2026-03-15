import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 설정 및 고정값
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏢", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 셸 디자인용 CSS (모바일에서 한 행에 장소, 시간, 상태 통합)
st.markdown("""
<style>
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 5px; background: white; }
    .row-main { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
    .col-place { flex: 5; font-size: 15px; font-weight: 700; color: #1e3a5f; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .col-time { flex: 3.5; font-size: 14px; color: #d9534f; font-weight: bold; text-align: center; }
    .col-status { flex: 1.5; font-size: 13px; font-weight: bold; text-align: right; }
    .row-sub { font-size: 13px; color: #666; margin-top: 6px; }
</style>
""", unsafe_allow_html=True)

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

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
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '부스': str(item.get('boothCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 엑셀 생성 (사용자님 소스 로직 100% 반영)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('대관현황')
        worksheet.set_landscape()
        date_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'shrink': True})
        center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'shrink': True})

        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write(curr_row, 0, r['장소'], left_fmt)
                            worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt)
                            worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['인원'], center_fmt)
                            worksheet.write(curr_row, 5, r['부스'], center_fmt)
                            worksheet.write(curr_row, 6, r['상태'], center_fmt)
                            curr_row += 1
                        curr_row += 1
        worksheet.set_column('A:A', 20); worksheet.set_column('B:B', 12); worksheet.set_column('C:C', 35); worksheet.set_column('D:D', 18); worksheet.set_column('E:G', 7)
    return output.getvalue()

# 4. 사이드바 및 데이터 로드
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

# 5. 메인 UI 및 셸 디자인 출력
st.title("🏢 성의교정 실시간 대관 현황")

if not df.empty:
    with st.sidebar:
        excel_data = create_formatted_excel(df, sel_bu)
        st.download_button("📥 엑셀 파일 받기", data=excel_data, file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div style="background-color:#333; color:white; padding:10px; border-radius:5px; margin-top:25px;">'
                    f'🗓️ {d_str} | 근무조: {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f"<h4 style='margin-top:15px; color:#1e3a5f;'>🏢 {bu}</h4>", unsafe_allow_html=True)
                for _, row in b_df.iterrows():
                    st_color = "#28a745" if row['상태'] == "확정" else "#d9534f"
                    # [셸 디자인 적용] 장소, 시간, 상태 한 행에 출력
                    st.markdown(f"""
                    <div class="event-shell">
                        <div class="row-main">
                            <div class="col-place">📍 {row['장소']}</div>
                            <div class="col-time">🕒 {row['시간']}</div>
                            <div class="col-status" style="color:{st_color};">{row['상태']}</div>
                        </div>
                        <div class="row-sub">📄 {row['행사명']} ({row['부서']}, {row['인원']}명)</div>
                    </div>""", unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
