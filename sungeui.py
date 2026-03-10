import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
import os
from fpdf import FPDF

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대 기준 오늘 날짜 (2026-03-10)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정 (레이아웃 최적화)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 20px; }
    .building-header { font-size: 19px !important; font-weight: 700; color: #2E5077; margin-top: 25px; }
    .custom-table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 13px; padding: 10px 2px; border: 1px solid #333; }
    .custom-table td { border: 1px solid #eee; padding: 8px 4px !important; font-size: 13px; vertical-align: middle; line-height: 1.4; text-align: center; }
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }
    @media (max-width: 768px) {
        .pc-time { display: none !important; }
        .mobile-time { display: block !important; font-size: 10px; font-weight: bold; line-height: 1.1; }
        .custom-table td { font-size: 11px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 필터
st.sidebar.header("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("조회 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 처리 로직 (요일 필터링 포함)
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
                    current_weekday = str(curr.weekday() + 1)
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (current_weekday in allow_days):
                        rows.append({
                            'raw_date': curr,
                            'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''),
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''),
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=['raw_date', 'raw_time', '건물명'])
        return df
    except: return pd.DataFrame()

all_df = get_data(start_selected, end_selected)

# 5. 화면 출력
date_range = f"{start_selected}" if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({date_range})</div>', unsafe_allow_html=True)

excel_data_list = []
for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    bu_df = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)] if not all_df.empty else pd.DataFrame()
    
    if not bu_df.empty:
        excel_data_list.append(bu_df)
        html = '<table class="custom-table"><thead><tr><th>날짜</th><th>시간</th><th>장소</th><th>행사명</th><th>부서</th><th>상태</th></tr></thead><tbody>'
        for _, r in bu_df.iterrows():
            st_t, en_t = r['시간'].split('~')[0].strip(), r['시간'].split('~')[1].strip()
            time_td = f'<div class="pc-time">{r["시간"]}</div><div class="mobile-time">{st_t}<br>{en_t}</div>'
            html += f'<tr><td>{r["날짜"][5:]}</td><td>{time_td}</td><td>{r["장소"]}</td><td style="text-align:left; padding-left:8px;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#999; font-size:12px; margin-left:10px;">내역 없음</p>', unsafe_allow_html=True)

# 6. PDF 생성 함수 (오류 최소화 버전)
def create_pdf_simple(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Rental Status Report", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    widths = [25, 40, 45, 40, 75, 45, 15]
    cols = ["Date", "Building", "Place", "Time", "Event", "Dept", "Status"]
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 10, col, border=1, align='C')
    pdf.ln()
    
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        # 한글 깨짐 방지를 위해 PDF 내부 데이터는 영어/숫자 위주로 먼저 테스트 권장
        # 실제 한글 적용은 .ttf 폰트 파일 업로드 후 가능합니다.
        pdf.cell(widths[0], 8, str(row['날짜']), border=1)
        pdf.cell(widths[1], 8, "Building", border=1) # 한글 필드 대신 임시 텍스트
        pdf.cell(widths[2], 8, "Place", border=1)
        pdf.cell(widths[3], 8, str(row['시간']), border=1)
        pdf.cell(widths[4], 8, "Event Name", border=1)
        pdf.cell(widths[5], 8, "Dept", border=1)
        pdf.cell(widths[6], 8, str(row['상태']), border=1)
        pdf.ln()
    return pdf.output()

# 7. 사이드바 저장 버튼
if excel_data_list:
    final_df = pd.concat(excel_data_list).drop(columns=['raw_date', 'raw_time'])
    st.sidebar.markdown("---")
    
    # 엑셀은 한글이 아주 잘 나옵니다.
    out_ex = BytesIO()
    with pd.ExcelWriter(out_ex, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", out_ex.getvalue(), f"rental_{start_selected}.xlsx")
    
    # PDF는 시스템 폰트 문제로 하얀 화면의 원인이 될 수 있어 try-except로 보호
    try:
        pdf_out = create_pdf_simple(final_df)
        st.sidebar.download_button("📄 PDF 저장 (Beta)", pdf_out, f"rental_{start_selected}.pdf")
    except:
        st.sidebar.warning("PDF 기능은 서버 환경 설정 중입니다.")
