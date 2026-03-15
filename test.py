import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정 및 반응형 커스텀 CSS
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
<style>
    /* 1. 공통 스타일 */
    .stApp { background-color: #f8f9fa; }
    .date-container { background-color: #333; color: white; padding: 10px 15px; border-radius: 8px; margin-top: 25px; margin-bottom: 10px; font-weight: bold; }
    .bu-header { font-size: 16px; font-weight: bold; color: #1e3a5f; padding: 8px 0; border-bottom: 2px solid #1e3a5f; margin: 15px 0 10px 0; }
    .sub-title { font-size: 13px; color: #888; margin-top: 10px; font-weight: bold; }

    /* 2. 세로 모드 전용 (Mobile Portrait) */
    @media (max-width: 600px) {
        .desktop-view { display: none !important; }
        .mobile-view { display: block !important; }
        
        .event-shell { border-bottom: 1px solid #dee2e6; padding: 10px 5px; background-color: white; }
        .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
        .col-place { flex: 5; font-size: 15px; font-weight: bold; color: #222; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .col-time { flex: 3; font-size: 14px; color: #ff4b4b; font-weight: 600; text-align: center; }
        .col-status { flex: 1.5; font-size: 12px; text-align: right; }
        .row-2 { font-size: 14px; color: #555; line-height: 1.4; padding-left: 2px; }
        .badge-y { color: #28a745; font-weight: bold; }
        .badge-n { color: #007bff; font-weight: bold; }
    }

    /* 3. 가로 모드 및 PC 전용 (Landscape / Desktop) */
    @media (min-width: 601px) {
        .mobile-view { display: none !important; }
        .desktop-view { display: block !important; }
        
        /* 폰트 크기 및 셸 여백 조정 */
        .stDataFrame div { font-size: 14px !important; }
        .stDataFrame td, .stDataFrame th { padding: 8px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 2. 근무조 로직 (모바일 소스 이식)
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 3. 데이터 수집 로직 (요일 필터링 포함)
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

# 4. 엑셀 생성 로직 (기존 규격 유지)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        hdr_fmt = workbook.add_format({'bold':True, 'font_size':12, 'bg_color':'#333333', 'font_color':'white', 'align':'center', 'valign':'vcenter', 'border':1})
        bu_fmt = workbook.add_format({'bold':True, 'font_size':11, 'bg_color':'#EBF1F8', 'align':'left', 'valign':'vcenter', 'border':1})
        left_fmt = workbook.add_format({'border':1, 'align':'left', 'valign':'vcenter', 'text_wrap':True, 'shrink':True})
        center_fmt = workbook.add_format({'border':1, 'align':'center', 'valign':'vcenter', 'shrink':True})
        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", hdr_fmt)
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
                            worksheet.write(curr_row, 0, r['장소'], left_fmt); worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt); worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['인원'], center_fmt); worksheet.write(curr_row, 5, r['부스'], center_fmt); worksheet.write(curr_row, 6, r['상태'], center_fmt)
                            curr_row += 1
                        curr_row += 1
        worksheet.set_column('A:A', 20); worksheet.set_column('B:B', 12); worksheet.set_column('C:C', 35); worksheet.set_column('D:D', 18); worksheet.set_column('E:G', 7)
    return output.getvalue()

# 5. 메인 UI
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

if not df.empty:
    with st.sidebar:
        st.download_button("📥 엑셀 다운로드", data=create_formatted_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-container">📅 {d_str} ({["월","화","수","목","금","토","일"][d_obj.weekday()]}) | 근무조: {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            bu_clean = bu.replace(" ", "")
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu_clean)]
            
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                for is_p, title in [(False, "📌 당일 대관"), (True, "🗓️ 기간 대관")]:
                    sub_df = b_df[b_df['is_period'] == is_p]
                    if not sub_df.empty:
                        st.markdown(f'<div class="sub-title">{title}</div>', unsafe_allow_html=True)
                        
                        # --- [세로 모드 뷰: HTML 셸] ---
                        mobile_html = ""
                        for _, row in sub_df.iterrows():
                            s_color = "badge-y" if row['상태'] == '확정' else "badge-n"
                            mobile_html += f"""
                            <div class="event-shell">
                                <div class="row-1">
                                    <div class="col-place">📍 {row['장소']}</div>
                                    <div class="col-time">⏰ {row['시간']}</div>
                                    <div class="col-status"><span class="{s_color}">{row['상태']}</span></div>
                                </div>
                                <div class="row-2">📄 {row['행사명']} ({row['인원']}명)</div>
                            </div>"""
                        st.markdown(f'<div class="mobile-view">{mobile_html}</div>', unsafe_allow_html=True)
                        
                        # --- [가로 모드 뷰: 데이터프레임] ---
                        st.markdown('<div class="desktop-view">', unsafe_allow_html=True)
                        st.dataframe(
                            sub_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], 
                            use_container_width=True, hide_index=True,
                            column_config={"장소": st.column_config.TextColumn(width="medium"), "시간": st.column_config.TextColumn(width="small")}
                        )
                        st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info(f"{bu} 내역 없음")
else:
    st.info("내역 없음")
