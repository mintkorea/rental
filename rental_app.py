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

# 2. CSS: 다크모드 호환성 및 제목 디자인
st.markdown("""
<style>
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; margin-bottom: 30px; }
    .date-header { 
        font-size: 20px !important; font-weight: 800; color: #007BFF; 
        padding: 10px 0; margin-top: 40px; border-bottom: 3px solid #007BFF; 
    }
    .building-header { 
        font-size: 17px !important; font-weight: 700; margin: 20px 0 10px 0; 
        border-left: 6px solid #007BFF; padding-left: 12px; 
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 (보안 헤더 포함)
@st.cache_data(ttl=60)
def get_clean_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            rows.append({
                '날짜': item.get('startDt'),
                '요일': ['월','화','수','목','금','토','일'][datetime.strptime(item['startDt'], '%Y-%m-%d').weekday()],
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', ''), 
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', ''), 
                '부서': item.get('mgDeptNm', ''),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. PDF 생성 함수 (한글 폰트 없을 시 영문으로 안전하게 생성)
def create_pdf_fixed(df, selected_bu):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf" # GitHub에 파일이 있어야 함
    has_font = os.path.exists(font_path)
    if has_font:
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=12)
    else:
        pdf.set_font("Arial", size=12)

    for date_val in sorted(df['날짜'].unique()):
        pdf.add_page()
        date_df = df[df['날짜'] == date_val]
        title = f"Rental Status - {date_val}" if not has_font else f"대관 현황 - {date_val}"
        pdf.cell(0, 10, title, ln=True, align='C')
        
        for bu in selected_bu:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            pdf.ln(5)
            pdf.cell(0, 10, f"* {bu}", ln=True)
            # 표 간략화 출력
            for _, r in bu_df.iterrows():
                pdf.set_font("Arial" if not has_font else "Nanum", size=9)
                pdf.cell(0, 8, f"  [{r['시간']}] {r['장소']} - {r['행사명'][:30]}", ln=True)
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 5. 메인 로직
with st.sidebar:
    st.header("⚙️ 설정")
    s_day = st.date_input("시작일", value=now_today)
    e_day = st.date_input("종료일", value=s_day + timedelta(days=7))
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_clean_data(s_day, e_day)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not df.empty:
    # PDF 다운로드 버튼
    try:
        pdf_bytes = create_pdf_fixed(df, sel_bu)
        st.sidebar.download_button("📥 PDF 다운로드", data=pdf_bytes, file_name="rental_list.pdf", mime="application/pdf")
    except Exception as e:
        st.sidebar.error("PDF 준비 중...")

    # 화면 출력
    for date in sorted(df['날짜'].unique()):
        day_df = df[df['날짜'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                # 왼쪽 인덱스(숫자)를 숨기고 다크모드에 최적화된 표 출력
                st.dataframe(
                    bu_df[['장소', '시간', '행사명', '부서', '상태']], 
                    hide_index=True, 
                    use_container_width=True
                )
else:
    st.info("조회된 대관 내역이 없습니다.")
