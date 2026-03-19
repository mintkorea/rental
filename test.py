from streamlit_option_menu import option_menu
import streamlit as st

selected = option_menu(
    menu_title=None, # 제목 없음
    options=["홈", "일정", "연락처", "설정"], 
    icons=["house", "calendar", "person-rolodex", "gear"], 
    menu_icon="cast", 
    default_index=0, 
    orientation="horizontal",
)

if selected == "홈":
    st.write("홈 화면입니다.")
# ... 선택된 메뉴에 따른 로직
