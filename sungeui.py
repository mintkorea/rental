import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io
from fpdf import FPDF
import os

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 스타일
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 20px; color: #1E3A5F; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 12px 0; margin-top: 35px; border-bottom: 2px solid #2E5077; }
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 20px; margin-bottom: 8px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; font-size: 13px; text-align: center; }
    td { border: 1px solid #eee; padding: 10px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }
    .no-data-text { color: #d9534f; font-size: 13px; padding: 10px; background-color: #fffafa; border: 1px solid #ffe3e3; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 요일 필터링 (원본 로직 유지)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '', 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '', 
                            '인원': str(item.get('peopleCount', '')) if item.get('peopleCount') else '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. PDF 생성 함수 (순서 고정 및 표 깨짐 방지 버전)
def create_pdf(df, selected_bu):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.set_auto_page_break(auto=True, margin=15)
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else: pdf.set_font("Arial", size=10)

    dates = sorted(df['날짜'].unique()) if not df.empty else [now_today.strftime('%Y-%m-%d')]
    for date_val in dates:
        pdf.add_page()
        date_df = df[df['날짜'] == date_val] if not df.empty else pd.DataFrame()
        d_obj = datetime.strptime(date_val, '%Y-%m-%d')
        w_str = ['월','화','수','목','금','토','일'][d_obj.weekday()]
        
        pdf.set_font("Nanum", size=16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val} {w_str}요일)", ln=True, align='C')
        
        for bu in [b for b in BUILDING_ORDER if b in selected_bu]:
            bu_df = date_df[date_df['건물명'] == bu] if not date_df.empty else pd.DataFrame()
            pdf.set_text_color(46, 80, 119)
            pdf.set_font("Nanum", size=12)
            pdf.cell(0, 10, f"■ {bu}", ln=True)
            pdf.set_text_color(0)
            
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Nanum", size=9)
            cols = [("장소", 40), ("시간", 35), ("행사명", 110), ("인원", 15), ("부서", 55), ("상태", 20)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()
            
            if bu_df.empty:
                pdf.cell(275, 10, "대관 내역이 없습니다.", border=1, align='C')
                pdf.ln(15)
            else:
                for _, row in bu_df.iterrows():
                    line_h = 7
                    event_txt = str(row['행사명'])
                    nb_lines = len(pdf.multi_cell(110, line_h, event_txt, split_only=True))
                    row_h = max(10, nb_lines * line_h)
                    
                    if pdf.get_y() + row_h > 185: pdf.add_page()
                    
                    x, y = pdf.get_x(), pdf.get_y()
                    pdf.cell(40, row_h, str(row['장소']), border=1, align='C')
                    pdf.cell(35, row_h, str(row['시간']), border=1, align='C')
                    cur_x = pdf.get_x()
                    pdf.multi_cell(110, line_h, event_txt, border=1, align='L')
                    pdf.set_xy(cur_x + 110, y)
                    pdf.cell(15, row_h, str(row['인원']), border=1, align='C')
                    pdf.cell(55, row_h, str(row['부서']), border=1, align='C')
                    pdf.cell(20, row_h, str(row['상태']), border=1, align='C')
                    pdf.ln(row_h)
                pdf.ln(5)
    return bytes(pdf.output(dest='S'))

# 5. 엑셀 생성 함수 (자동화 편집 포함)
def create_excel(df):
    output = io.BytesIO()
    try:
        # 라이브러리 체크 및 스타일링은 엑셀 엔진(xlsxwriter) 활용
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='대관현황')
            workbook = writer.book
            worksheet = writer.sheets['대관현황']
            
            # 스타일 설정
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
            cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
            left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
            
            # 헤더 적용
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_fmt)
            
            # 열 너비 및 정렬 설정
            worksheet.set_column('A:E', 15, cell_fmt)
            worksheet.set_column('F:F', 45, left_fmt) # 행사명
            worksheet.set_column('G:I', 15, cell_fmt)
            
        return output.getvalue()
    except Exception as e:
        # 오류 시 기본 엑셀로 반환
        df.to_excel(output, index=False)
        return output.getvalue()

# 6. UI 로직
st.sidebar.title("📅 설정")
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_data(s_date, e_date)

# 사이드바 버튼
if not df.empty:
    filtered_df = df[df['건물명'].isin(sel_bu)]
    # 건물 순서 정렬
    filtered_df['temp_sort'] = filtered_df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
    filtered_df = filtered_df.sort_values(by=['날짜', 'temp_sort', '시간']).drop(columns=['temp_sort'])
    
    with st.sidebar:
        if st.button("📄 PDF 생성"):
            st.download_button("📥 PDF 다운로드", data=create_pdf(filtered_df, sel_bu), file_name=f"rental_{s_date}.pdf")
        
        excel_data = create_excel(filtered_df)
        st.download_button("📥 엑셀 다운로드", data=excel_data, file_name=f"rental_{s_date}.xlsx")

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# 화면 출력 (날짜별 -> 선택한 건물별)
for date in pd.date_range(s_date, e_date).strftime('%Y-%m-%d'):
    d_obj = datetime.strptime(date, '%Y-%m-%d')
    w_str = ['월','화','수','목','금','토','일'][d_obj.weekday()]
    st.markdown(f'<div class="date-header">📅 {date} ({w_str}요일)</div>', unsafe_allow_html=True)
    
    day_df = df[df['날짜'] == date] if not df.empty else pd.DataFrame()
    for b in sel_bu:
        st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
        b_df = day_df[day_df['건물명'] == b] if not day_df.empty else pd.DataFrame()
        if not b_df.empty:
            table_html = "<table><thead><tr><th style='width:15%'>장소</th><th style='width:15%'>시간</th><th style='width:40%'>행사명</th><th style='width:7%'>인원</th><th style='width:15%'>부서</th><th style='width:8%'>상태</th></tr></thead><tbody>"
            for _, r in b_df.iterrows():
                table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
            st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data-text">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
