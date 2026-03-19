import streamlit as st

# 모바일에서도 컬럼을 가로로 유지하는 CSS
st.markdown("""
    <style>
    [data-testid="column"] {
        width: calc(25% - 1rem) !important;  /* 4개 메뉴 기준, 간격 고려 */
        flex: 1 1 calc(25% - 1rem) !important;
        min-width: 0px !important;
    }
    </style>
    """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.button("🏠 홈")
with col2:
    st.button("📅 일정")
with col3:
    st.button("📞 연락")
with col4:
    st.button("⚙️ 설정")
