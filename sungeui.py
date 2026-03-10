import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 및 시간 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정 (레이아웃 복구 및 시간 중복 방지)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 24px !important; font-weight: 800; color: #002D56; margin-bottom: 20px; }
    .building-header { font-size: 18px !important; font-weight: 700; color: #2E5077; margin-top: 30px; }
    .custom-table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; margin-bottom: 20px; }
    .custom-table th { background-color: #f8f9fa !important; color: #333 !important; font-size: 13px; padding: 10px 2px; border: 1px solid #dee2e6; }
    .custom-table td { border: 1px solid #dee2e6; padding: 8px 4px !important; font-size: 13px; vertical-align: middle; line-height: 1.4; text-align: center; }
    
    /* [해결] 시간 중복 노출 방지 */
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }
    @media (max-width: 768px) {
        .pc-time { display: none !important; }
        .mobile-time { display: block !important; font-size: 11px; font-weight: bold; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (요일 필터링 반영)
@st.cache_data(ttl=60)
def get_rental_data(s_date, e_date):
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
            # [해결] 요일 정보 파싱 (1:월 ~ 7:일)
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    current_weekday = str(curr.weekday() + 1)
                    # 요일 조건 체크
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (current_weekday in allow_days):
                        rows.append({
                            'raw_date': curr,
                            'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''),
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''),
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        return df.sort_values(by=['raw_date', 'raw_time']) if not df.empty else df
    except: return pd.DataFrame()

# 4. 사이드바 및 조회
st.sidebar.header("🔍 필터")
start_d = st.sidebar.date_input("시작일", value=now_today)
end_d = st.sidebar.date_input("종료일", value=now_today)
BUILDINGS = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDINGS, default=BUILDINGS)

all_df = get_rental_data(start_d, end_d)

# 5. 화면 출력 및 데이터 수집
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({start_d} ~ {end_d})</div>', unsafe_allow_html=True)
excel_list = []

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    bu_df = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)] if not all_df.empty else pd.DataFrame()
    
    if not bu_df.empty:
        excel_list.append(bu_df)
        html = '<table class="custom-table"><thead><tr><th>날짜</th><th>시간</th><th>장소</th><th>행사명</th><th>부서</th><th>상태</th></tr></thead><tbody>'
        for _, r in bu_df.iterrows():
            st_t, en_t = r['시간'].split('~')[0].strip(), r['시간'].split('~')[1].strip()
            time_td = f'<div class="pc-time">{r["시간"]}</div><div class="mobile-time">{st_t}<br>~ {en_t}</div>'
            html += f'<tr><td>{r["날짜"]}</td><td>{time_td}</td><td>{r["장소"]}</td><td style="text-align:left; padding-left:8px;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#999; font-size:12px; margin-left:10px;">내역 없음</p>', unsafe_allow_html=True)

# 6. PDF 생성 (업로드한 나눔고딕 폰트 사용)
def create_pdf(df, title):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # [중요] 업로드한 폰트 파일명을 정확히 입력하세요 (NanumGothic.ttf)
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path)
        pdf.set_font("Nanum", size=16)
    else:
        pdf.set_font("Arial", size=16) # 폰트 없을 시 기본 폰트 (한글 깨짐)

    pdf.add_page()
    pdf.cell(0, 15, title, ln=True, align='C')
    pdf.ln(5)
    
    # 헤더
    pdf.set_font("Nanum", size=10)
    pdf.set_fill_color(230, 230, 230)
    cols = ["날짜", "건물", "장소", "시간", "행사명", "상태"]
    widths = [20, 35, 40, 40, 115, 20]
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 10, col, border=1, align='C', fill=True)
    pdf.ln()
    
    # 데이터
    pdf.set_font("Nanum", size=9)
    for _, row in df.iterrows():
        pdf.cell(widths[0], 9, str(row['날짜']), border=1, align='C')
        pdf.cell(widths[1], 9, str(row['건물명'])[:12], border=1, align='C')
        pdf.cell(widths[2], 9, str(row['장소'])[:15], border=1, align='C')
        pdf.cell(widths[3], 9, str(row['시간']), border=1, align='C')
        pdf.cell(widths[4], 9, str(row['행사명'])[:50], border=1)
        pdf.cell(widths[5], 9, str(row['상태']), border=1, align='C')
        pdf.ln()
    return pdf.output()

# 7. 다운로드 버튼 (화면 결과물 기반)
if excel_list:
    final_df = pd.concat(excel_list).drop(columns=['raw_date', 'raw_time'])
    st.sidebar.markdown("---")
    
    # 엑셀
    out_ex = BytesIO()
    with pd.ExcelWriter(out_ex, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 검색 결과 엑셀 저장", out_ex.getvalue(), f"rental_{start_d}.xlsx")
    
    # PDF
    try:
        pdf_bytes = create_pdf(final_df, f"성의교정 대관 현황 ({start_d})")
        st.sidebar.download_button("📄 검색 결과 PDF 저장", bytes(pdf_bytes), f"rental_{start_d}.pdf", "application/pdf")
    except Exception as e:
        st.sidebar.error(f"PDF 오류: {e}")
