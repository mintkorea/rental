# 4. PDF 생성 함수 (수정됨)
def create_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else:
        pdf.set_font("Arial", size=10)

    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        weekday_str = date_df.iloc[0]['요일']
        pdf.set_font("Nanum", size=16) if os.path.exists(font_path) else pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val} {weekday_str}요일)", ln=True, align='C')
        
        for bu in date_df['건물명'].unique():
            bu_df = date_df[date_df['건물명'] == bu]
            pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 10, f"■ {bu}", ln=True)
            pdf.set_text_color(0)
            pdf.set_fill_color(240, 240, 240)
            cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 15), ("부서", 45), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()
            for _, row in bu_df.iterrows():
                pdf.cell(40, 9, str(row['장소'])[:18], border=1, align='C')
                pdf.cell(35, 9, str(row['시간']), border=1, align='C')
                pdf.cell(115, 9, " " + str(row['행사명'])[:45], border=1, align='L')
                pdf.cell(15, 9, str(row['인원']), border=1, align='C')
                pdf.cell(45, 9, str(row['부서'])[:15], border=1, align='C')
                pdf.cell(15, 9, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(5)
    
    # 이 부분이 핵심 수정 사항입니다.
    return pdf.output(dest='S') 

# 5. 메인 UI 내 다운로드 버튼 부분
if not filtered_df.empty:
    with st.sidebar:
        if st.button("📄 PDF 생성 및 준비"):
            try:
                # 함수에서 이미 bytes/bytearray를 반환함
                pdf_bytes = create_pdf(filtered_df)
                st.download_button(
                    label="📥 PDF 다운로드",
                    data=pdf_bytes,
                    file_name=f"rental_{start_selected}.pdf",
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF 생성 오류: {e}")
