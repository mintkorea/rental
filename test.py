import streamlit as st

# 탭을 사용하면 모바일에서도 상단 가로 메뉴처럼 작동합니다.
tab1, tab2, tab3, tab4 = st.tabs(["🏠 홈", "📅 일정", "📞 연락망", "⚙️ 설정"])

with tab1:
    st.write("홈 화면 콘텐츠")
with tab2:
    st.write("시설 예약 현황 등 일정 관리")
# ... 나머지 탭 구성
