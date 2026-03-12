# 2. CSS 설정 (셀 넓이 수치 적용)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 5px; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 10px 0; margin-top: 30px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 15px; margin-bottom: 5px; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 8px 4px; font-size: 13px; font-weight: bold; text-align: center; }
    td { border: 1px solid #eee; padding: 8px 6px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }
    
    /* 셸 너비 숫자 대치 */
    .col-place { width: 15%; }
    .col-time { width: 15%; }
    .col-event { width: 40%; }
    .col-people { width: 7%; }
    .col-dept { width: 15%; }
    .col-status { width: 8%; }
</style>
""", unsafe_allow_html=True)
