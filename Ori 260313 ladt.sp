import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
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
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; margin-bottom: 20px; color: #1E3A5F; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 12px 0; margin-top: 35px; border-bottom: 2px solid #2E5077; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; margin-bottom: 8px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; font-size: 14px; text-align: center; }
    td { border: 1px solid #eee; padding: 10px; font-size: 14px; text-align: center; vertical-align: middle; word-break: break-all; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드
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
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            
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

# 4. PDF 생성 (폰트 크기 조절 및 왼쪽 정렬 반영)
def create_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
    
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
            
            # 헤더 (폰트 크게)
            pdf.set_text_color(0)
            pdf.set_fill_color(240, 240, 240)
            cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 15), ("부서", 50), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()
            
            for _, row in bu_df.iterrows():
                # 동적 폰트 및 높이 설정
                base_font_size = 11
                line_height = 6
                event_txt = " " + str(row['행사명'])
                
                # 행사명 길이에 따라 폰트 축소 (최대 2줄 유지)
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=base_font_size)
                while len(pdf.multi_cell(115, line_height, event_txt, split_only=True)) > 2 and base_font_size > 7:
                    base_font_size -= 0.5
                    pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=base_font_size)
                
                nb_lines = len(pdf.multi_cell(115, line_height, event_txt, split_only=True))
                row_h = max(12, nb_lines * line_height + 2)
                v_offset = (row_h - (nb_lines * line_height)) / 2
                
                x, y = pdf.get_x(), pdf.get_y()
                
                # 장소 (왼쪽 정렬)
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=10)
                pdf.cell(40, row_h, " " + str(row['장소']), border=1, align='L')
                # 시간 (중앙)
                pdf.cell(35, row_h, str(row['시간']), border=1, align='C')
                
                # 행사명 (왼쪽 정렬, 세로 중앙)
                cur_x = pdf.get_x()
                pdf.rect(cur_x, y, 115, row_h)
                pdf.set_xy(cur_x, y + v_offset)
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=base_font_size)
                pdf.multi_cell(115, line_height, event_txt, border=0, align='L')
                
                # 인원, 부서(왼쪽), 상태
                pdf.set_xy(cur_x + 115, y)
                pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=10)
                pdf.cell(15, row_h, str(row['인원']), border=1, align='C')
                pdf.cell(50, row_h, " " + str(row['부서']), border=1, align='L')
                pdf.cell(15, row_h, str(row['상태']), border=1, align='C')
                pdf.ln(row_h)
            pdf.ln(5)
    return bytes(pdf.output(dest='S'))

# 5. 메인 UI 및 None 방어 로직
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_data(s_date, e_date)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)].copy()
    if not f_df.empty:
        f_df['건물명'] = pd.Categorical(f_df['건물명'], categories=BUILDING_ORDER, ordered=True)
        f_df = f_df.sort_values(by=['full_date', '건물명', '시간'])

        with st.sidebar:
            # None 표출을 막기 위해 버튼 결과를 변수에 담지 않고 직접 제어
            if st.button("📄 PDF 생성 및 준비"):
                data = create_pdf(f_df)
                st.download_button("📥 PDF 다운로드", data=data, file_name=f"rental_{s_date}.pdf", mime="application/pdf")
        
        st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
        for date in sorted(f_df['full_date'].unique()):
            d_df = f_df[f_df['full_date'] == date]
            st.markdown(f'<div class="date-header">📅 {date} ({d_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
            for b in sel_bu:
                b_df = d_df[d_df['건물명'] == b]
                if not b_df.empty:
                    st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                    table_html = "<table><thead><tr><th style='width:15%'>장소</th><th style='width:15%'>시간</th><th style='width:40%'>행사명</th><th style='width:7%'>인원</th><th style='width:15%'>부서</th><th style='width:8%'>상태</th></tr></thead><tbody>"
                    for _, r in b_df.iterrows():
                        table_html += f"<tr><td style='text-align:left'>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left'>{r['행사명']}</td><td>{r['인원']}</td><td style='text-align:left'>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
    else: st.info("선택한 건물에 내역이 없습니다.")
else: st.info("조회된 내역이 없습니다.")
