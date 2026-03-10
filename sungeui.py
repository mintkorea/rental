import streamlit as st
import pandas as pd
from datetime import datetime
from reportlab.pdfgen import canvas
# ... 필요한 라이브러리 (ReportLab 등)

def generate_pdf(data, report_date):
    # PDF 전용 디자인: 군더더기 없이 깔끔한 표 중심
    file_name = f"rental_report_{report_date}.pdf"
    c = canvas.Canvas(file_name)
    
    # 1. 제목 설정 (요청하신 형식)
    title = f"성의교정 대관 현황 ({report_date})"
    c.setFont("MalgunGothic", 16) # 한글 폰트 설정 필요
    c.drawString(100, 800, title)
    
    # 2. PDF 전용 데이터 구성 (홈페이지보다 간결하게)
    # 예: [건물, 호실, 시간, 행사명] 등 핵심 정보만 추출
    y_pos = 750
    for idx, row in data.iterrows():
        text = f"{row['건물']} | {row['호실']} | {row['시간']} | {row['행사명']}"
        c.setFont("MalgunGothic", 10)
        c.drawString(50, y_pos, text)
        y_pos -= 20
        if y_pos < 50: # 페이지 넘김 처리
            c.showPage()
            y_pos = 800
            
    c.save()
    return file_name

# --- 메인 화면 ---
st.title("시설 대관 현황 모니터링")

# 날짜 선택 (오늘 날짜 기본값, 기간 설정 가능하도록 복구)
col1, col2 = st.columns(2)
with col1:
    start_date = st.date_input("시작일", value=datetime.today())
with col2:
    end_date = st.date_input("종료일", value=datetime.today())

# 데이터 필터링 로직
filtered_df = get_rental_data(start_date, end_date) # 기존 데이터 로드 함수

if not filtered_df.empty:
    # A. 홈페이지 출력 (상세 정보 포함)
    st.subheader("🖥️ 웹 화면 상세 현황")
    st.dataframe(filtered_df, use_container_width=True) # 필터, 상세 비고 포함
    
    # B. PDF 다운로드 버튼
    st.divider()
    report_date_str = start_date.strftime('%Y-%m-%d')
    if start_date != end_date:
        report_date_str = f"{start_date} ~ {end_date}"
        
    pdf_file = generate_pdf(filtered_df, report_date_str)
    
    with open(pdf_file, "rb") as f:
        st.download_button(
            label="📄 PDF 리포트 다운로드",
            data=f,
            file_name=pdf_file,
            mime="application/pdf"
        )
else:
    st.warning("선택하신 기간에 대관 데이터가 없습니다.")
