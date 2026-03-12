# 폰트 에러 방지를 위해 fpdf2를 사용하므로 임포트 경로 주의
from fpdf import FPDF 

st.markdown("""
<style>
    /* 날짜 헤더: 간격을 100px로 벌려 수정 확인 */
    .date-header { 
        margin-top: 100px !important; 
        border-bottom: 5px solid #FF4B4B !important; /* 선 색상을 빨간색으로 변경하여 확인 */
    }
    /* 테이블 테두리 강제 부여 */
    td, th { border: 2px solid #808080 !important; }
</style>
""", unsafe_allow_html=True)
