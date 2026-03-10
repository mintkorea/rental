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

# 2. 건물 리스트 순서 고정
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 3. CSS (홈페이지 깨짐 방지 및 디자인)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .building-header { font-size: 20px !important; font-weight: 700; color: #2E5077; margin-top: 35px; border-left: 5px solid #2E5077; padding-left: 10px; }
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
    .custom-table th { background-color: #444; color: white; padding: 10px; border: 1px solid #333; }
    .custom-table td { border: 1px solid #eee; padding: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 (peopleCount 포함)
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
            rows.append({
                '날짜': datetime.strptime(item['startDt'], '%Y-%m-%d').strftime('%m-%d'),
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', ''), 
                '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                '행사명': item.get('eventNm', ''), 
                '인원': item.get('peopleCount', '-'),
                '부서': item.get('mgDeptNm', ''),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['날짜', '건물명'])
        return df
    except: return pd.DataFrame()

# 5. PDF 생성 (인코딩 오류 수정 버전)
def create_pdf(df, title_text):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else:
        return None

    pdf.add_page()
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    # 테이블 헤더 설정 (인원 포함)
    cols = [("장소", 40), ("시간", 40), ("행사명", 90), ("인원", 15), ("부서", 50), ("상태", 20)]
    pdf.set_fill_color(220, 220, 220)
    pdf.set_font("Nanum", size=11)
    for txt, width in cols:
        pdf.cell(width, 10, txt, border=1, align='C', fill=True)
    pdf.ln()

    # 데이터 입력
    pdf.set_font("Nanum", size=10)
    for _, row in df.iterrows():
        pdf.cell(40, 10, str(row['장소']), border=1, align='C')
        pdf.cell(40, 10, str(row['시간']), border=1, align='C')
        pdf.cell(90, 10, str(row['행사명']), border=1, align='L')
        pdf.cell(15, 10, str(row['인원']), border=1, align='C')
        pdf.cell(50, 10, str(row['부서']), border=1, align='C')
        pdf.cell(20, 10, str(row['상태']), border=1, align='C')
        pdf.ln()
    
    # 🌟 인코딩 에러 방지를 위해 bytearray로 직접 처리 🌟
    return pdf.output()

# --- 사이드바 및 실행 ---
st.sidebar.title("🔍 대관 조회 필터")
all_df = get_data(now_today, now_today)

if st.sidebar.button("📄 PDF 생성하기"):
    if not all_df.empty:
        try:
            pdf_output = create_pdf(all_df, f"성의교정 대관 현황 ({now_today})")
            if pdf_output:
                st.sidebar.download_button(
                    label="📥 PDF 다운로드",
                    data=bytes(pdf_output), # bytearray를 bytes로 변환하여 안전하게 전송
                    file_name=f"rental_{now_today}.pdf",
                    mime="application/pdf"
                )
            else:
                st.sidebar.error("폰트 파일을 찾을 수 없습니다.")
        except Exception as e:
            st.sidebar.error(f"PDF 생성 중 오류 발생: {e}")
    else:
        st.sidebar.warning("조회된 데이터가 없습니다.")

# 메인 화면 렌더링 (홈페이지 형태)
st.markdown(f"### 🏫 성의교정 대관 현황 ({now_today})")
for bu in BUILDING_ORDER:
    bu_df = all_df[all_df['건물명'] == bu] if not all_df.empty else pd.DataFrame()
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not bu_df.empty:
        st.table(bu_df[['장소', '시간', '행사명', '부서', '상태']]) # 인원은 PDF에 포함, 화면은 깔끔하게 유지
    else:
        st.write("대관 내역이 없습니다.")
