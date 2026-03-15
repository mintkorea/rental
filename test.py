import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

# 화면 노출 표 디자인 (디자인 일관성 유지)
st.markdown("""
    <style>
    [data-testid="stDataFrame"] th { background-color: #f8f9fa !important; text-align: center !important; }
    [data-testid="stDataFrame"] td { 
        padding-left: 10px !important; 
        padding-right: 10px !important; 
        vertical-align: middle !important;
        height: auto !important; /* 높이 35px 해제 */
    }
    </style>
""", unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

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
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
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

# 4. 엑셀 생성 (편집용지 여백 10mm 설정)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        worksheet.set_landscape() # 가로 출력
        
        # [핵심] 편집용지 여백 설정 (단위: 인치, 0.39인치 ≒ 10mm)
        margin_val = 0.39 
        worksheet.set_margins(left=margin_val, right=margin_val, top=margin_val, bottom=margin_val)
        worksheet.set_header('', {'margin': 0})
        worksheet.set_footer('', {'margin': 0})

        # 서식 정의
        date_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'indent': 1})
        left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'shrink': True, 'indent': 1})
        center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'shrink': True})

        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    bu_clean = bu.replace(" ", "")
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu_clean)]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35) # 엑셀은 35 유지
                            worksheet.write(curr_row, 0, r['장소'], left_fmt)
                            worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt)
                            worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['인원'], center_fmt)
                            worksheet.write(curr_row, 5, r['부스'], center_fmt)
                            worksheet.write(curr_row, 6, r['상태'], center_fmt)
                            curr_row += 1
                        curr_row += 1

        # 열 너비 설정 (시간 셀 너비 +2 반영)
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 14) # 12 -> 14
        worksheet.set_column('C:C', 35)
        worksheet.set_column('D:D', 18)
        worksheet.set_column('E:G', 8)
        
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
        excel_data = create_formatted_excel(df, sel_bu)
        st.download_button("📥 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div style="background-color:#f1f3f5; padding:10px; border-radius:5px; margin-top:30px;">'
                    f'<h3>📅 {d_str} | 근무조: {get_shift(d_obj)}</h3></div>', unsafe_allow_html=True)
        for bu in sel_bu:
            bu_clean = bu.replace(" ", "")
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu_clean)]
            st.markdown(f"#### 📍 {bu}")
            if not b_df.empty:
                t_df = b_df[b_df['is_period'] == False]
                p_df = b_df[b_df['is_period'] == True]
                if not t_df.empty:
                    st.write("**📌 당일 대관**")
                    st.dataframe(t_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True)
                if not p_df.empty:
                    st.write("**🗓️ 기간 대관**")
                    st.dataframe(p_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True)
            else:
                st.info(f"{bu} 대관 내역이 없습니다.")
else:
    st.info("조회된 날짜 범위 내에 대관 내역이 없습니다.")
