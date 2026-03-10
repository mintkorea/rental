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

# 한국 시간대(KST) 기준 오늘 날짜
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 폰트 다운로드 함수 (PDF 한글 깨짐 방지)
@st.cache_data
def download_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        response = requests.get(font_url)
        with open(font_path, "wb") as f:
            f.write(response.content)
    return font_path

# 3. PDF 생성 클래스 (fpdf2 기반)
class MyPDF(FPDF):
    def header(self):
        if hasattr(self, 'title_text'):
            self.set_font("Nanum", "B", 16)
            self.cell(0, 10, self.title_text, ln=True, align="C")
            self.ln(5)

# PDF 생성 메인 함수
def generate_pdf(df, title):
    font_path = download_font()
    pdf = MyPDF(orientation="L", unit="mm", format="A4")
    pdf.title_text = title
    
    # 폰트 등록 (한글 지원)
    pdf.add_font("Nanum", "", font_path)
    pdf.add_font("Nanum", "B", font_path) # Bold 대용
    pdf.set_font("Nanum", size=10)
    pdf.add_page()

    # 테이블 헤더
    cols = ["날짜", "건물명", "장소", "시간", "행사명", "부서", "상태"]
    widths = [25, 35, 45, 40, 75, 45, 15]
    
    pdf.set_fill_color(200, 200, 200)
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 10, col, border=1, align="C", fill=True)
    pdf.ln()

    # 데이터 행
    pdf.set_font("Nanum", size=9)
    for _, row in df.iterrows():
        pdf.cell(widths[0], 8, str(row['날짜']), border=1, align="C")
        pdf.cell(widths[1], 8, str(row['건물명']), border=1, align="C")
        pdf.cell(widths[2], 8, str(row['장소'])[:18], border=1, align="C")
        pdf.cell(widths[3], 8, str(row['시간']), border=1, align="C")
        pdf.cell(widths[4], 8, str(row['행사명'])[:30], border=1)
        pdf.cell(widths[5], 8, str(row['부서'])[:15], border=1, align="C")
        pdf.cell(widths[6], 8, str(row['상태']), border=1, align="C")
        pdf.ln()
    
    return pdf.output()

# --- [4~5 데이터 로직 및 화면 출력 부분은 이전과 동일하게 유지] ---
# (중략: get_processed_data 함수 및 화면 테이블 출력 코드)

# 6. 사이드바 저장 버튼 영역
if 'all_df' in locals() and not all_df.empty:
    filtered_list = []
    for bu in selected_bu:
        tmp = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        if not tmp.empty:
            filtered_list.append(tmp)
            
    if filtered_list:
        final_df = pd.concat(filtered_list).drop(columns=['raw_date', 'raw_time'])
        
        st.sidebar.markdown("---")
        # 엑셀 다운로드
        output_ex = BytesIO()
        with pd.ExcelWriter(output_ex, engine='openpyxl') as writer:
            final_df.to_excel(writer, index=False)
        st.sidebar.download_button("📥 엑셀 저장", output_ex.getvalue(), f"rental_{start_selected}.xlsx")
        
        # PDF 다운로드 (개선 버전)
        try:
            pdf_output = generate_pdf(final_df, f"성의교정 대관 현황 ({start_selected})")
            st.sidebar.download_button(
                label="📄 PDF 저장 (한글지원)",
                data=bytes(pdf_output),
                file_name=f"rental_{start_selected}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.sidebar.error(f"PDF 생성 오류: {e}")
