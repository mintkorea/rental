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

# 2. 3교대 근무조 로직
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    shifts = ['A', 'B', 'C']
    return f"{shifts[diff % 3]}조"

# 3. 데이터 수집 로직 (기간 전체 수집 후 요일별 전개)
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
            
            allow_day_raw = str(item.get('allowDay', '')).lower()
            allowed_days = [d.strip() for d in allow_day_raw.replace(' ', '').split(',') if d.strip().isdigit()] if allow_day_raw != 'none' else []
            
            curr = s_dt
            while curr <= e_dt:
                # 선택한 기간 내에 포함되는 날짜만 추출
                if start_date <= curr <= end_date:
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '요일': ['','월','화','수','목','금','토','일'][curr.isoweekday()],
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')) if item.get('peopleCount') else '0',
                            '부스': str(item.get('boothCount', '0')) if item.get('boothCount') else '0',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 엑셀 생성 (날짜별 그룹화 반영)
def create_formatted_excel(df, start_date, end_date, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 서식 설정 (폰트 11)
        title_fmt = workbook.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter'})
        date_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter'})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#EBF1F8', 'border': 1, 'valign': 'vcenter'})
        hdr_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 11})
        cnt_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11})

        worksheet.merge_range('A1:G1', "성의교정 대관 현황 보고서", title_fmt)
        worksheet.set_row(0, 40)
        
        curr_row = 2
        # 데이터가 있는 날짜별로 루프
        dates = sorted(df['full_date'].unique()) if not df.empty else [start_date.strftime('%Y-%m-%d')]
        
        for d_str in dates:
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            shift = get_shift(d_obj)
            wd = ['','월','화','수','목','금','토','일'][d_obj.isoweekday()]
            
            # 날짜 헤더
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} ({wd}) | 근무조: {shift}", date_hdr_fmt)
            worksheet.set_row(curr_row, 30)
            curr_row += 1
            
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    bu_df = df[(df['full_date'] == d_str) & (df['건물명'] == bu)] if not df.empty else pd.DataFrame()
                    
                    worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                    worksheet.set_row(curr_row, 28)
                    curr_row += 1
                    
                    headers = ['장소', '시간', '행사명', '부서', '인원', '부스', '상태']
                    for col_num, h in enumerate(headers):
                        worksheet.write(curr_row, col_num, h, hdr_fmt)
                    worksheet.set_row(curr_row, 25)
                    curr_row += 1
                    
                    if not bu_df.empty:
                        for _, row in bu_df.iterrows():
                            worksheet.write(curr_row, 0, row['장소'], cell_fmt)
                            worksheet.write(curr_row, 1, row['시간'], cnt_fmt)
                            worksheet.write(curr_row, 2, row['행사명'], cell_fmt)
                            worksheet.write(curr_row, 3, row['부서'], cell_fmt)
                            worksheet.write(curr_row, 4, row['인원'], cnt_fmt)
                            worksheet.write(curr_row, 5, row['부스'], cnt_fmt)
                            worksheet.write(curr_row, 6, row['상태'], cnt_fmt)
                            worksheet.set_row(curr_row, 35)
                            curr_row += 1
                    else:
                        worksheet.merge_range(curr_row, 0, curr_row, 6, "대관 내역 없음", cnt_fmt)
                        worksheet.set_row(curr_row, 35)
                        curr_row += 1
                    curr_row += 1
            curr_row += 1

        worksheet.set_column('A:A', 25); worksheet.set_column('B:B', 16); worksheet.set_column('C:C', 50)
        worksheet.set_column('D:D', 22); worksheet.set_column('E:G', 10)
    return output.getvalue()

# 5. 메인 UI
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date) # 시작일 기준으로 기본값 설정
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)
    st.write("---")

df = get_data(s_date, e_date)

st.markdown(f'<h2 style="border-bottom:3px solid #1E3A5F; padding-bottom:10px;">🏫 성의교정 대관 현황 ({s_date} ~ {e_date})</h2>', unsafe_allow_html=True)

if not df.empty:
    with st.sidebar:
        excel_data = create_formatted_excel(df, s_date, e_date, sel_bu)
        st.download_button("📥 기간 전체 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}_{e_date}.xlsx", use_container_width=True)

    # 화면 출력: 날짜별로 그룹화
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        wd_idx = d_obj.isoweekday()
        color = 'blue' if wd_idx == 6 else 'red' if wd_idx == 7 else '#333'
        wd_name = ['','월','화','수','목','금','토','일'][wd_idx]
        
        st.markdown(f"""<div style="background-color:#f1f3f5; padding:10px; border-radius:5px; margin-top:30px;">
            <h3 style="margin:0; color:{color};">📅 {d_str} ({wd_name}요일) | 근무조: {get_shift(d_obj)}</h3>
        </div>""", unsafe_allow_html=True)
        
        for b in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'] == b)]
            st.markdown(f"#### 📍 {b}")
            if not b_df.empty:
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True)
            else:
                st.info("대관 내역이 없습니다.")
else:
    st.info("선택한 기간에 조회된 내역이 없습니다.")
