import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 20px; color: #1E3A5F; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 12px 0; margin-top: 35px; border-bottom: 2px solid #2E5077; }
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 20px; margin-bottom: 8px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 12px 4px; font-size: 13px; font-weight: bold; text-align: center; }
    td { border: 1px solid #eee; padding: 12px 8px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-word; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res.raise_for_status()
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = []
            if allow_day_raw and allow_day_raw.lower() != 'none':
                allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. PDF 생성 함수 (겹침 현상 해결 버전)
def create_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else: pdf.set_font("Arial", size=10)

    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        weekday_str = date_df.iloc[0]['요일']
        pdf.set_font("Nanum", size=16) if os.path.exists(font_path) else pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val} {weekday_str}요일)", ln=True, align='C')
        
        for bu in date_df['건물명'].unique():
            bu_df = date_df[date_df['건물명'] == bu]
            pdf.set_text_color(46, 80, 119)
            pdf.set_font("Nanum", size=12) if os.path.exists(font_path) else pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"■ {bu}", ln=True)
            
            pdf.set_text_color(0)
            pdf.set_fill_color(240, 240, 240)
            cols = [("장소", 35), ("시간", 35), ("행사명", 125), ("인원", 15), ("부서", 50), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()
            
            pdf.set_font("Nanum", size=9) if os.path.exists(font_path) else pdf.set_font("Arial", size=9)
            for _, row in bu_df.iterrows():
                # 줄바꿈 높이 계산 (행사명 125mm 너비 기준)
                line_h = 7
                # 실제 출력 전 텍스트 높이 측정
                test_pdf = FPDF(orientation='L', unit='mm', format='A4')
                test_pdf.add_page()
                if os.path.exists(font_path): test_pdf.add_font("Nanum", "", font_path, uni=True); test_pdf.set_font("Nanum", size=9)
                
                prev_y = test_pdf.get_y()
                test_pdf.multi_cell(125, line_h, str(row['행사명']))
                row_h = max(10, test_pdf.get_y() - prev_y) # 최소 높이 10mm
                
                # 실제 출력
                cur_x, cur_y = pdf.get_x(), pdf.get_y()
                
                # 1~2열 (장소, 시간)
                pdf.cell(35, row_h, str(row['장소']), border=1, align='C')
                pdf.cell(35, row_h, str(row['시간']), border=1, align='C')
                
                # 3열 (행사명 - MultiCell 처리)
                evt_x, evt_y = pdf.get_x(), pdf.get_y()
                pdf.rect(evt_x, evt_y, 125, row_h) # 테두리 먼저 그리기
                pdf.multi_cell(125, line_h, " " + str(row['행사명']), border=0, align='L')
                
                # 4~6열 (인원, 부서, 상태 - 좌표 복구 후 출력)
                pdf.set_xy(evt_x + 125, evt_y)
                pdf.cell(15, row_h, str(row['인원']), border=1, align='C')
                pdf.cell(50, row_h, str(row['부서']), border=1, align='C')
                pdf.cell(15, row_h, str(row['상태']), border=1, align='C')
                
                pdf.set_y(evt_y + row_h) # 다음 행 위치 강제 지정
            pdf.ln(5)
    return bytes(pdf.output(dest='S'))

# 5. 메인 UI
st.sidebar.title("📅 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

raw_df = get_data(start_selected, end_selected)

if not raw_df.empty:
    filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)].copy()
    filtered_df['건물명'] = pd.Categorical(filtered_df['filtered_df' if 'filtered_df' in globals() else '건물명'], categories=BUILDING_ORDER, ordered=True)
    filtered_df = filtered_df.sort_values(by=['full_date', '건물명', '시간'])

    if not filtered_df.empty:
        with st.sidebar:
            # 💡 [해결] None 문자열 표출 방지: if문 내부에서 바로 생성/다운로드 처리
            if st.button("📄 PDF 생성 및 준비"):
                pdf_data = create_pdf(filtered_df)
                st.download_button("📥 PDF 다운로드", data=pdf_data, file_name=f"rental_{start_selected}.pdf", mime="application/pdf")

        st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
        for date in sorted(filtered_df['full_date'].unique()):
            day_df = filtered_df[filtered_df['full_date'] == date]
            st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
            for bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                    header_html = '<table><thead><tr><th style="width:15%;">장소</th><th style="width:15%;">시간</th><th style="width:40%;">행사명</th><th style="width:7%;">인원</th><th style="width:15%;">부서</th><th style="width:8%;">상태</th></tr></thead><tbody>'
                    rows_html = "".join([f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in bu_df.iterrows()])
                    st.markdown(header_html + rows_html + "</tbody></table>", unsafe_allow_html=True)
    else: st.info("선택한 건물에 내역이 없습니다.")
else: st.info("조회된 내역이 없습니다.")
