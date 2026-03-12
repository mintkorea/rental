import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 초기 설정 (다크모드 방지 및 레이아웃)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. 웹 화면 CSS (PC 가독성 및 컬러 강화)
st.markdown("""
<style>
    /* 다크모드에서도 배경을 밝게 유지 */
    .stApp { background-color: #ffffff; color: #000000; }
    .main-title { font-size: 26px !important; font-weight: 800; text-align: center; margin-bottom: 25px; color: #1E3A5F; }
    /* 요일 표시 헤더 컬러링 */
    .date-header { 
        font-size: 18px !important; font-weight: 800; color: white; 
        background-color: #2E5077; padding: 10px 15px; margin-top: 30px; 
        border-radius: 5px; display: flex; justify-content: space-between;
    }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; margin-bottom: 10px; border-left: 6px solid #2E5077; padding-left: 12px; color: #333; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; border: 1px solid #ddd; }
    th { background-color: #f2f5f8; border: 1px solid #ccc; padding: 12px; font-size: 14px; color: #333; }
    td { border: 1px solid #eee; padding: 12px; font-size: 14px; vertical-align: middle; color: #333; }
    .no-data { text-align: center; padding: 50px; font-size: 18px; color: #ff4b4b; font-weight: bold; border: 2px dashed #ff4b4b; border-radius: 10px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 (에러 방어 로직 강화)
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
            # None 문자열 처리 강화
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': str(item.get('placeNm', '')), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': str(item.get('eventNm', '')), 
                            '인원': str(item.get('peopleCount', '') or '-'),
                            '부서': str(item.get('mgDeptNm', '') or '-'),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except Exception: return pd.DataFrame()

# 4. PDF 생성 (동적 폰트 및 정렬 최적화)
def create_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path): pdf.add_font("Nanum", "", font_path, uni=True)
    
    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=18)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val})", ln=True, align='C')
        
        for bu in date_df['건물명'].unique():
            bu_df = date_df[date_df['건물명'] == bu]
            pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=14)
            pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 12, f"■ {bu}", ln=True)
            
            pdf.set_text_color(0)
            pdf.set_fill_color(240, 240, 240)
            cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 15), ("부서", 50), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()
            
            for _, row in bu_df.iterrows():
                base_font_size = 11
                line_height = 6
                event_txt = " " + str(row['행사명'])
                
                # 폰트 축소 로직 (최대 2줄)
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=base_font_size)
                while len(pdf.multi_cell(115, line_height, event_txt, split_only=True)) > 2 and base_font_size > 7:
                    base_font_size -= 0.5
                    pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=base_font_size)
                
                nb_lines = len(pdf.multi_cell(115, line_height, event_txt, split_only=True))
                row_h = max(12, nb_lines * line_height + 2)
                v_offset = (row_h - (nb_lines * line_height)) / 2
                
                x, y = pdf.get_x(), pdf.get_y()
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=10)
                pdf.cell(40, row_h, " " + str(row['장소']), border=1, align='L')
                pdf.cell(35, row_h, str(row['시간']), border=1, align='C')
                
                cur_x = pdf.get_x()
                pdf.rect(cur_x, y, 115, row_h)
                pdf.set_xy(cur_x, y + v_offset)
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=base_font_size)
                pdf.multi_cell(115, line_height, event_txt, border=0, align='L')
                
                pdf.set_xy(cur_x + 115, y)
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=10)
                pdf.cell(15, row_h, str(row['인원']), border=1, align='C')
                pdf.cell(50, row_h, " " + str(row['부서']), border=1, align='L')
                pdf.cell(15, row_h, str(row['상태']), border=1, align='C')
                pdf.ln(row_h)
            pdf.ln(5)
    return bytes(pdf.output(dest='S'))

# 5. 실행부
with st.sidebar:
    st.title("📅 대관 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)
    
    # None 방지를 위해 컨테이너 사용
    btn_container = st.container()

df = get_data(s_date, e_date)

st.markdown('<div class="main-title">🏫 성의교정 대관 조회 시스템</div>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)].copy()
    if not f_df.empty:
        f_df['건물명'] = pd.Categorical(f_df['건물명'], categories=BUILDING_ORDER, ordered=True)
        f_df = f_df.sort_values(by=['full_date', '건물명', '시간'])

        with btn_container:
            if st.button("📄 PDF 생성"):
                pdf_data = create_pdf(f_df)
                st.download_button("📥 PDF 다운로드", data=pdf_data, file_name=f"rental_{s_date}.pdf", mime="application/pdf")
        
        for date in sorted(f_df['full_date'].unique()):
            d_df = f_df[f_df['full_date'] == date]
            st.markdown(f'<div class="date-header"><span>📅 {date}</span><span>({d_df.iloc[0]["요일"]}요일)</span></div>', unsafe_allow_html=True)
            for b in sel_bu:
                b_df = d_df[d_df['건물명'] == b]
                if not b_df.empty:
                    st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                    table_html = "<table><thead><tr><th style='width:15%'>장소</th><th style='width:15%'>시간</th><th style='width:40%'>행사명</th><th style='width:7%'>인원</th><th style='width:15%'>부서</th><th style='width:8%'>상태</th></tr></thead><tbody>"
                    for _, r in b_df.iterrows():
                        table_html += f"<tr><td style='text-align:left'>{r['장소']}</td><td style='text-align:center'>{r['시간']}</td><td style='text-align:left'>{r['행사명']}</td><td style='text-align:center'>{r['인원']}</td><td style='text-align:left'>{r['부서']}</td><td style='text-align:center'>{r['상태']}</td></tr>"
                    st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">조회된 내역이 없습니다. (건물 필터를 확인해주세요)</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="no-data">해당 기간에 조회된 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
