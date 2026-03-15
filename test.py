import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 사이드바 상시 확장
st.set_page_config(page_title="성의교정 실시간 대관 현황", page_icon="🏢", layout="wide", initial_sidebar_state="expanded")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일 (가이드라인 반영: 타이틀 2.8rem, 1줄 그리드 나열)
style_html = """
<style>
    .main-title {{ font-size: 2.8rem !important; font-weight: 900; color: #1e3a5f; text-align: center; margin: 25px 0; line-height: 1.1; }}
    .bu-header {{ font-size: 1.2rem !important; font-weight: 800; color: #1e3a5f; }}
    .bu-badge {{ font-size: 11px; background: #e1e8f0; padding: 2px 8px; border-radius: 10px; font-weight: bold; }}
    .event-shell {{ border-bottom: 1px solid #eee; padding: 12px 0; }}
    .row-main {{ display: grid; grid-template-columns: 5.5fr 3.2fr 1.3fr; align-items: center; gap: 4px; width: 100%; }}
    .col-place {{ font-weight: 700; color: #1e3a5f; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .col-time {{ font-size: 11px; color: #d9534f; font-weight: 600; text-align: center; white-space: nowrap; }}
    .col-status {{ font-size: 11.5px; font-weight: 800; text-align: right; white-space: nowrap; }}
    .row-sub {{ font-size: 11.5px; color: #555; margin-top: 5px; line-height: 1.4; }}
</style>
"""
st.markdown(style_html, unsafe_allow_html=True)

# 3. 로직 함수 (보내주신 소스 기준)
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
            allowed_days = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': "{0}~{1}".format(item.get('startTime', ''), item.get('endTime', '')),
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

# 4. 엑셀 생성 (보내주신 높이 35 서식 완벽 반영)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('대관현황')
        worksheet.set_landscape()
        date_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'shrink': True})
        center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'shrink': True})

        curr_row = 0
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, "📅 {0} | 근무조: {1}".format(d_str, get_shift(d_obj)), date_hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, "  📍 {0}".format(bu), bu_fmt)
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

# 5. UI 출력
with st.sidebar:
    st.header("🔍 조회 설정")
    view_mode = st.radio("📺 보기 모드", ["PC 모드", "모바일(세로)"], index=1)
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)
if not df.empty:
    with st.sidebar:
        excel_data = create_formatted_excel(df, sel_bu)
        st.download_button("📥 엑셀 다운로드", data=excel_data, file_name="대관현황_{0}.xlsx".format(s_date), use_container_width=True)

st.markdown('<div class="main-title">🏢 성의교정 실시간<br>대관 현황</div>', unsafe_allow_html=True)

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        st.markdown('<div style="background:#444; color:white; padding:8px 12px; border-radius:5px; margin-top:20px; font-weight:bold;">🗓️ {0} | {1}</div>'.format(d_str, get_shift(datetime.strptime(d_str, '%Y-%m-%d').date())), unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown('<div style="display:flex; align-items:center; justify-content:space-between; border-bottom:2.5px solid #1e3a5f; margin:18px 0 6px 0;"><span class="bu-header">🏢 {0}</span><span class="bu-badge">총 {1}건</span></div>'.format(bu, len(b_df)), unsafe_allow_html=True)
                if view_mode == "모바일(세로)":
                    for _, row in b_df.iterrows():
                        color = "#28a745" if row['상태'] == "확정" else "#d9534f"
                        p_font = "14px" if len(row['장소']) <= 10 else ("12px" if len(row['장소']) <= 14 else "10.5px")
                        st.markdown("""<div class="event-shell"><div class="row-main"><div class="col-place" style="font-size:{0};">📍 {1}</div><div class="col-time">🕒 {2}</div><div class="col-status" style="color:{3};">{4}</div></div><div class="row-sub">📄 {5} ({6}, {7}명, 부스 {8}개)</div></div>""".format(p_font, row['장소'], row['시간'], color, row['상태'], row['행사명'], row['부서'], row['인원'], row['부스']), unsafe_allow_html=True)
                else:
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True)
else:
    st.info("조회된 날짜에 대관 내역이 없습니다.")
