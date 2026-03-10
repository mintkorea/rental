import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정 및 시간
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 웹 화면 디자인 (d888bc 스타일 유지 + 인원 셀 추가)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 25px; }
    .building-header { font-size: 20px !important; font-weight: 700; color: #2E5077; margin-top: 35px; margin-bottom: 15px; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    .custom-table { width: 100% !important; border-collapse: collapse; margin-bottom: 30px; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 14px; padding: 12px 5px; border: 1px solid #333; }
    .custom-table td { border: 1px solid #eee; padding: 10px 5px !important; font-size: 13px; vertical-align: middle; text-align: center; line-height: 1.5; }
    
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }
    @media (max-width: 768px) {
        .pc-time { display: none !important; }
        .mobile-time { display: block !important; font-size: 11px; font-weight: bold; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 필터
st.sidebar.header("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("조회 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 타이틀 조건부 표출
if start_selected == end_selected:
    display_title = f"성의교정 대관 현황 ({start_selected})"
else:
    display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)

# 5. 데이터 처리 함수 (인원 정보 포함)
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
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (str(curr.weekday()+1) in allow_days):
                        rows.append({
                            'raw_date': curr, 'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%Y-%m-%d'), 
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('extV1', '-'), # 인원 정보 (필드명 확인 필요)
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        return df.sort_values(by=['raw_date', 'raw_time']) if not df.empty else df
    except: return pd.DataFrame()

all_df = get_data(start_selected, end_selected)

# 6. 화면 출력 및 데이터 수집
pdf_data_list = []
for bu in selected_bu:
    bu_df = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)] if not all_df.empty else pd.DataFrame()
    
    if not bu_df.empty:
        # 날짜별로 그룹화하여 출력
        for date, date_df in bu_df.groupby('날짜'):
            st.markdown(f'<div class="building-header">🏢 {bu}({date})</div>', unsafe_allow_html=True)
            pdf_data_list.append((f"{bu}({date})", date_df))
            
            html = '<table class="custom-table"><thead><tr>'
            html += '<th style="width:20%">장소</th><th style="width:15%">시간</th><th style="width:30%">행사명</th>'
            html += '<th style="width:10%">인원</th><th style="width:15%">부서</th><th style="width:10%">상태</th>'
            html += '</tr></thead><tbody>'
            for _, r in date_df.iterrows():
                st_t, en_t = r['시간'].split('~')[0].strip(), r['시간'].split('~')[1].strip()
                time_td = f'<div class="pc-time">{r["시간"]}</div><div class="mobile-time">{st_t}<br>~ {en_t}</div>'
                html += f'<tr><td>{r["장소"]}</td><td>{time_td}</td><td style="text-align:left; padding-left:10px;">{r["행사명"]}</td>'
                html += f'<td>{r["인원"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        st.markdown('<p style="color:#999; font-size:13px; margin-left:15px; margin-bottom:30px;">대관 내역이 없습니다.</p>', unsafe_allow_html=True)

# 7. PDF 생성 함수 (날짜 셀 제거, 인원 셀 추가)
def create_image_style_pdf(content_list, main_title):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf")
    pdf.add_page()
    
    pdf.set_font("Nanum", size=18)
    pdf.cell(0, 15, main_title, ln=True, align='C')
    pdf.ln(5)

    for section_title, df in content_list:
        pdf.set_font("Nanum", size=11)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(0, 10, section_title, ln=True)
        
        pdf.set_font("Nanum", size=10)
        pdf.set_fill_color(220, 220, 220)
        # 헤더: 날짜 제외, 인원 추가
        cols = ["장소", "시간", "행사명", "인원", "부서", "상태"]
        widths = [45, 40, 95, 20, 45, 20]
        for i, col in enumerate(cols):
            pdf.cell(widths[i], 10, col, border=1, align='C', fill=True)
        pdf.ln()
        
        pdf.set_font("Nanum", size=9)
        for _, row in df.iterrows():
            pdf.cell(widths[0], 9, str(row['장소'])[:18], border=1, align='C')
            pdf.cell(widths[1], 9, str(row['시간']), border=1, align='C')
            pdf.cell(widths[2], 9, str(row['행사명'])[:45], border=1)
            pdf.cell(widths[3], 9, str(row['인원']), border=1, align='C')
            pdf.cell(widths[4], 9, str(row['부서'])[:15], border=1, align='C')
            pdf.cell(widths[5], 9, str(row['상태']), border=1, align='C')
            pdf.ln()
        pdf.ln(5)
        
    return pdf.output()

# 8. 저장 버튼
if pdf_data_list:
    st.sidebar.markdown("---")
    try:
        pdf_bytes = create_image_style_pdf(pdf_data_list, display_title)
        st.sidebar.download_button("📄 PDF 리포트 저장", bytes(pdf_bytes), f"rental_{start_selected}.pdf", "application/pdf")
    except Exception as e:
        st.sidebar.error("PDF 생성 중 오류가 발생했습니다.")
