import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정 및 오늘 날짜
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 한글 폰트 다운로드 (PDF용)
@st.cache_data
def get_font_file():
    # 구글 폰트 서버에서 나눔고딕 Regular 다운로드
    url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    response = requests.get(url)
    return response.content

# 3. PDF 생성 함수 (한글 폰트 등록 포함)
def create_pdf(df, title_text):
    font_data = get_font_file()
    font_path = "NanumGothic.ttf"
    
    # 임시 파일로 폰트 저장
    with open(font_path, "wb") as f:
        f.write(font_data)

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    # 한글 폰트 등록
    pdf.add_font("Nanum", "", font_path)
    pdf.set_font("Nanum", size=16)
    
    # 타이틀
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)
    
    # 헤더 설정
    pdf.set_font("Nanum", size=10)
    pdf.set_fill_color(240, 240, 240)
    cols = ["날짜", "건물명", "장소", "시간", "행사명", "상태"]
    widths = [20, 35, 45, 40, 110, 25]
    
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 10, col, border=1, align='C', fill=True)
    pdf.ln()
    
    # 데이터 행 추가
    pdf.set_font("Nanum", size=9)
    for _, row in df.iterrows():
        pdf.cell(widths[0], 8, str(row['날짜']), border=1, align='C')
        pdf.cell(widths[1], 8, str(row['건물명']), border=1, align='C')
        pdf.cell(widths[2], 8, str(row['장소'])[:18], border=1, align='C')
        pdf.cell(widths[3], 8, str(row['시간']), border=1, align='C')
        pdf.cell(widths[4], 8, str(row['행사명'])[:45], border=1) # 행사명은 길어서 조절
        pdf.cell(widths[5], 8, str(row['상태']), border=1, align='C')
        pdf.ln()
        
    return pdf.output()

# --- [이하 데이터 조회 및 화면 출력 로직은 이전과 동일] ---

# (중략: get_processed_data 함수 및 화면 UI 코드)

# 4. 저장 버튼 섹션 (검색 결과가 있을 때만 활성화)
if 'all_df' in locals() and not all_df.empty:
    # 현재 화면에 필터링된 데이터만 추출
    filtered_data = []
    for bu in selected_bu:
        tmp = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        if not tmp.empty:
            filtered_data.append(tmp)
            
    if filtered_data:
        final_df = pd.concat(filtered_data).drop(columns=['raw_date', 'raw_time'])
        
        st.sidebar.markdown("---")
        # 엑셀 다운로드
        output_ex = BytesIO()
        with pd.ExcelWriter(output_ex, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        st.sidebar.download_button("📥 엑셀로 저장", output_ex.getvalue(), f"rental_{start_selected}.xlsx")
        
        # PDF 다운로드
        try:
            pdf_bytes = create_pdf(final_df, f"성의교정 대관 현황 ({start_selected})")
            st.sidebar.download_button(
                label="📄 PDF로 저장",
                data=bytes(pdf_bytes),
                file_name=f"rental_{start_selected}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.sidebar.error("PDF 생성 중 한글 폰트 로드 실패. 엑셀을 이용해 주세요.")
