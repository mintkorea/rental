import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 스타일
st.markdown("""
<style>
    .report-header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
    th { text-align: center !important; background-color: #f8f9fa; }
    td { vertical-align: middle !important; }
</style>
""", unsafe_allow_html=True)

# 3. 3교대 근무조 로직
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    shifts = ['A', 'B', 'C']
    return f"{shifts[diff % 3]}조"

# 4. 데이터 로드 로직
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        current_wd = target_date.isoweekday()
        for item in raw:
            if not item.get('startDt'): continue
            allow_day_raw = str(item.get('allowDay', ''))
            if allow_day_raw and allow_day_raw.lower() != 'none':
                allowed_days = [d.strip() for d in allow_day_raw.split(',') if d.strip().isdigit()]
                if str(current_wd) not in allowed_days: continue
            rows.append({
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '부서': item.get('mgDeptNm', '') or '-',
                '인원': item.get('peopleCount', '') or '-',
                '부스': str(item.get('boothCount', '0')),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 5. 각 건물별 독립된 표로 구성된 엑셀 생성
def create_building_wise_excel(df, target_date, shift_name, selected_buildings):
    output = io.BytesIO()
    date_str = target_date.strftime("%Y. %m. %d")
    wd_name = ['','월','화','수','목','금','토','일'][target_date.isoweekday()]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 서식 설정
        title_fmt = workbook.add_format({'bold': True, 'font_size': 14})
        info_fmt = workbook.add_format({'font_size': 11})
        bu_name_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'font_color': '#1E3A5F', 'bg_color': '#EBF1F8'})
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True})
        center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        # 상단 제목 및 근무조
        worksheet.write('A1', f"성의교정 대관 현황", title_fmt)
        worksheet.write('A2', f"일자: {date_str}({wd_name})  |  근무조: {shift_name}", info_fmt)
        
        curr_row = 3
        
        for bu in BUILDING_ORDER:
            if bu in selected_buildings:
                bu_df = df[df['건물명'] == bu]
                
                # 건물명 타이틀
                worksheet.merge_range(curr_row, 0, curr_row, 6, f" 📍 {bu}", bu_name_fmt)
                curr_row += 1
                
                # 표 헤더 (장소부터 시작)
                headers = ['장소', '시간', '행사명', '부서', '인원', '부스', '상태']
                for col_num, header in enumerate(headers):
                    worksheet.write(curr_row, col_num, header, header_fmt)
                curr_row += 1
                
                if not bu_df.empty:
                    for _, row in bu_df.iterrows():
                        # 데이터 쓰기 및 정렬
                        worksheet.write(curr_row, 0, row['장소'], cell_fmt)
                        worksheet.write(curr_row, 1, row['시간'], center_fmt)
                        worksheet.write(curr_row, 2, row['행사명'], cell_fmt)
                        worksheet.write(curr_row, 3, row['부서'], cell_fmt)
                        worksheet.write(curr_row, 4, row['인원'], center_fmt)
                        worksheet.write(curr_row, 5, row['부스'], center_fmt)
                        worksheet.write(curr_row, 6, row['상태'], center_fmt)
                        curr_row += 1
                else:
                    worksheet.merge_range(curr_row, 0, curr_row, 6, "대관 내역이 없습니다.", cell_fmt)
                    curr_row += 1
                
                curr_row += 1 # 건물 간 간격
        
        # 열 너비 최적화 (장소/행사명은 넓게, 나머지는 좁게)
        worksheet.set_column('A:A', 25) # 장소
        worksheet.set_column('B:B', 15) # 시간 (좁게)
        worksheet.set_column('C:C', 45) # 행사명 (넓게)
        worksheet.set_column('D:D', 20) # 부서
        worksheet.set_column('E:G', 8)  # 인원, 부스, 상태 (매우 좁게)

    return output.getvalue()

# 6. 메인 로직
s_date = st.sidebar.date_input("조회일", value=now_today)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_data(s_date)
shift_info = get_shift(s_date)

# 요일 색상 설정 (화면용)
wd_idx = s_date.isoweekday()
wd_names = ['','월','화','수','목','금','토','일']
color_wd = f"<span style='color:{'blue' if wd_idx==6 else 'red' if wd_idx==7 else 'black'}'>{wd_names[wd_idx]}</span>"

st.markdown(f"""
    <div class="report-header">
        <h2 style='margin-bottom:5px;'>성의교정 대관 현황</h2>
        <p style='font-size:1.1rem; color:#555;'>{s_date.strftime("%Y. %m. %d")}({color_wd}) &nbsp; | &nbsp; 근무조 : {shift_info}</p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)].copy()
    with st.sidebar:
        st.write("---")
        excel_data = create_building_wise_excel(f_df, s_date, shift_info, sel_bu)
        st.download_button("📥 보고서 양식 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for b in sel_bu:
        b_df = f_df[f_df['건물명'] == b]
        st.markdown(f"#### 📍 {b}")
        if not b_df.empty:
            st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True,
                column_config={"시간": st.column_config.TextColumn(width="small"), "인원": st.column_config.TextColumn(width="min"), "부스": st.column_config.TextColumn(width="min"), "상태": st.column_config.TextColumn(width="min")})
        else:
            st.info("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
