import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원", "옴니버스 파크"]

# 2. 다크모드 완벽 대응 CSS (고정 색상을 제거하고 테두리 강조)
st.markdown("""
<style>
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .date-header { 
        font-size: 20px !important; font-weight: 800; 
        color: #007BFF; padding: 10px 0; margin-top: 40px; 
        border-bottom: 3px solid #007BFF; 
    }
    .building-header { 
        font-size: 17px !important; font-weight: 700; 
        margin-top: 20px; margin-bottom: 10px; 
        border-left: 6px solid #007BFF; padding-left: 12px; 
    }
    /* 테이블: 다크모드에서도 선명하도록 테두리 색상 조정 */
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; color: inherit; }
    th { background-color: rgba(128, 128, 128, 0.1); border: 2px solid #555; padding: 10px; font-weight: bold; }
    td { border: 1px solid #777; padding: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 (보안 헤더 및 요일 필터 포함)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            # 요일 필터링 로직
            allowed = [int(d.strip()) for d in str(item['allowDay']).split(',') if d.strip()] if item.get('allowDay') else []
            s_ptr, e_ptr = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_ptr
            while curr <= e_ptr:
                if s_date <= curr <= e_date:
                    if not allowed or (curr.weekday() + 1) in allowed:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', ''),
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 4. PDF 생성 함수 (폰트 에러 방지 포함)
def create_pdf(df, selected_bu):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # GitHub에 NanumGothic.ttf 파일을 함께 올리셔야 한글이 깨지지 않습니다.
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else:
        pdf.set_font("Arial", size=10) # 폰트 없을 시 기본 폰트 사용

    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=16)
        pdf.cell(0, 15, f"Rental Status ({date_val})", ln=True, align='C')
        
        for bu in selected_bu:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            pdf.set_font("Nanum" if os.path.exists(font_path) else "Arial", size=12)
            pdf.cell(0, 10, f"* {bu}", ln=True)
            # 테이블 헤더 및 데이터 생략 (길이 조절 필요)
            pdf.ln(5)
    return pdf.output(dest='S').encode('latin1')

# 5. 메인 UI 및 실행
st.sidebar.title("📅 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected + timedelta(days=7))
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    # PDF 다운로드 버튼 (사이드바)
    try:
        pdf_data = create_pdf(all_df, selected_bu)
        st.sidebar.download_button("📥 PDF로 저장", data=pdf_data, file_name="rental.pdf", mime="application/pdf")
    except:
        st.sidebar.warning("PDF 생성 모듈 확인 중...")

    # 화면 출력
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                # 가독성을 위해 표준 표 사용 (다크모드 호환성 최고)
                st.table(bu_df[['장소', '시간', '행사명', '부서', '상태']])
else:
    st.info("조회된 내역이 없습니다. 날짜를 확인해 주세요.")
