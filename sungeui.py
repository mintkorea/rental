import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF # PDF 생성을 위한 라이브러리 추가

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대(KST) 기준 오늘 날짜
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정 (레이아웃 및 시간 중복 방지)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 20px; }
    .building-header { font-size: 19px !important; font-weight: 700; color: #2E5077; margin-top: 25px; }
    .custom-table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 13px; padding: 10px 2px; }
    .custom-table td { border: 1px solid #eee; padding: 8px 4px !important; font-size: 13px; vertical-align: middle; line-height: 1.4; }
    
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }
    .t-center { text-align: center !important; }
    .t-left { text-align: left !important; padding-left: 8px !important; }

    .w-date { width: 8%; }
    .w-time { width: 12%; }
    .w-place { width: 18%; }
    .w-event { width: 37%; }
    .w-dept { width: 17%; }
    .w-status { width: 8%; }

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

# 4. 데이터 로직 (요일 필터링 포함)
@st.cache_data(ttl=60)
def get_processed_data(s_date, e_date):
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

all_df = get_processed_data(start_selected, end_selected)

# 5. 화면 출력 및 데이터 수집
date_range = f"{start_selected}" if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({date_range})</div>', unsafe_allow_html=True)

excel_data_list = []

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not all_df.empty:
        bu_df = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        if not bu_df.empty:
            excel_data_list.append(bu_df)
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="w-date">날짜</th><th class="w-time">시간</th><th class="w-place">장소</th>'
            html += '<th class="w-event">행사명</th><th class="w-dept">부서</th><th class="w-status">상태</th>'
            html += '</tr></thead><tbody>'
            for _, r in bu_df.iterrows():
                start_t, end_t = r['시간'].split('~')[0].strip(), r['시간'].split('~')[1].strip()
                time_html = f'<div class="pc-time">{r["시간"]}</div><div class="mobile-time">{start_t}<br>{end_t}</div>'
                html += f'<tr><td class="w-date t-center">{r["날짜"][5:]}</td>'
                html += f'<td class="w-time t-center">{time_html}</td>'
                html += f'<td class="w-place t-center">{r["장소"]}</td>'
                html += f'<td class="w-event t-left">{r["행사명"]}</td>'
                html += f'<td class="w-dept t-center">{r["부서"]}</td>'
                html += f'<td class="w-status t-center">{r["상태"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; font-size:12px; margin-left:10px;">내역 없음</p>', unsafe_allow_html=True)

# 6. PDF 생성 함수
def create_pdf(df, title):
    pdf = FPDF(orientation='L', unit='mm', format='A4') # 가로 모드
    pdf.add_page()
    # 한글 폰트 지원을 위해 폰트 경로 설정이 필요할 수 있습니다. 
    # 여기서는 기본 폰트를 사용하나, 실제 한글 출력을 위해선 .ttf 폰트 등록이 필요합니다.
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, title, ln=True, align='C')
    pdf.ln(10)
    
    # 헤더 설정
    pdf.set_font("Arial", 'B', 10)
    cols = ['Date', 'Building', 'Place', 'Time', 'Event', 'Dept', 'Status']
    col_widths = [20, 30, 40, 35, 80, 40, 20]
    
    for i in range(len(cols)):
        pdf.cell(col_widths[i], 10, cols[i], border=1, align='C')
    pdf.ln()
    
    # 데이터 행 추가
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        # 데이터가 너무 길 경우 자동 줄바꿈 대신 잘림 방지를 위해 간략화 처리
        pdf.cell(col_widths[0], 8, row['날짜'][5:], border=1, align='C')
        pdf.cell(col_widths[1], 8, row['건물명'][:10], border=1, align='C')
        pdf.cell(col_widths[2], 8, row['장소'][:15], border=1, align='C')
        pdf.cell(col_widths[3], 8, row['시간'], border=1, align='C')
        pdf.cell(col_widths[4], 8, row['행사명'][:30], border=1)
        pdf.cell(col_widths[5], 8, row['부서'][:15], border=1, align='C')
        pdf.cell(col_widths[6], 8, row['상태'], border=1, align='C')
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# 7. 사이드바 저장 버튼
if excel_data_list:
    final_df = pd.concat(excel_data_list).drop(columns=['raw_date', 'raw_time'])
    st.sidebar.markdown("---")
    
    # 엑셀 저장
    output_excel = BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False, sheet_name='Rental_Status')
    st.sidebar.download_button("📥 엑셀로 저장", output_excel.getvalue(), f"rental_{start_selected}.xlsx")
    
    # PDF 저장 (참고: fpdf는 한글 폰트(ttf) 파일이 서버에 있어야 한글이 깨지지 않습니다.)
    try:
        pdf_bytes = create_pdf(final_df, f"Rental Status ({date_range})")
        st.sidebar.download_button("📄 PDF로 저장", pdf_bytes, f"rental_{start_selected}.pdf")
    except Exception as e:
        st.sidebar.warning("PDF 생성 중 오류가 발생했습니다. (폰트 설정 확인 필요)")
