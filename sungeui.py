import streamlit as st
from datetime import datetime
import pandas as pd

# 1. 페이지 설정 및 스타일
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

# CSS를 활용한 디자인 개선
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #4CAF50; color: white; }
    .menu-card { padding: 20px; border-radius: 15px; border-left: 5px solid #4CAF50; background-color: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. 현재 시간 및 요일 계산
now = datetime.now()
days = ["월", "화", "수", "목", "금", "토", "일"]
today_idx = now.weekday()
today_str = days[today_idx]
current_hour = now.hour

# 3. 메인 헤더
st.title("🍱 성의교정 실시간 식단 매니저")
st.subheader(f"📅 오늘은 {now.strftime('%m월 %d일')} ({today_str}요일)")

# 4. 시간대별 자동 큐레이션 로직
# 오전 00시 ~ 오후 2시: 중식 강조
# 오후 2시 ~ 오후 12시: 석식 강조
if current_hour < 14:
    recommendation = "🍴 지금은 **점심 메뉴**가 궁금하시겠네요!"
    focus_menu = "중식"
else:
    recommendation = "🌙 지금은 **저녁 메뉴**를 확인할 시간입니다."
    focus_menu = "석식"

st.info(recommendation)

# 5. 임시 데이터 (AI 분석 보류 동안 사용)
# 분석 기능이 완성되면 st.session_state['menu_data']에서 읽어오게 됩니다.
if 'menu_data' not in st.session_state:
    # 테스트용 샘플 데이터
    st.session_state['menu_data'] = {
        "월": {"중식": "돈까스, 스프, 샐러드", "석식": "김치찌개, 계란말이"},
        "화": {"중식": "비빔밥, 된장국", "석식": "제육볶음, 쌈채소"},
        "수": {"중식": "짜장면, 탕수육", "석식": "볶음밥, 짬뽕국물"},
        "목": {"중식": "육개장, 석박지", "석식": "고등어구이, 된장찌개"},
        "금": {"중식": "카레라이스, 우동", "석식": "부대찌개, 라면사리"}
    }

# 6. 식단 표시 UI
st.divider()

# 요일 선택 (기본값은 오늘 요일)
selected_day = st.selectbox("다른 요일 식단 보기", days[:5], index=today_idx if today_idx < 5 else 0)

# 선택된 요일의 데이터 가져오기
day_menu = st.session_state['menu_data'].get(selected_day, {"중식": "정보 없음", "석식": "정보 없음"})

col1, col2 = st.columns(2)

with col1:
    # 현재 시간대에 따라 테두리 색상 등으로 강조 가능
    is_lunch_time = (focus_menu == "중식" and selected_day == today_str)
    title_suffix = " ⭐" if is_lunch_time else ""
    st.markdown(f"""<div class="menu-card">
        <h3>🍴 중식{title_suffix}</h3>
        <p>{day_menu['중식']}</p>
    </div>""", unsafe_allow_html=True)

with col2:
    is_dinner_time = (focus_menu == "석식" and selected_day == today_str)
    title_suffix = " ⭐" if is_dinner_time else ""
    st.markdown(f"""<div class="menu-card" style="border-left-color: #ff4b4b;">
        <h3>🌙 석식{title_suffix}</h3>
        <p>{day_menu['석식']}</p>
    </div>""", unsafe_allow_html=True)

# 7. 하단 유틸리티 (보류 중인 이미지 업로드 기능을 하단으로 배치)
with st.expander("📷 식단표 이미지 업데이트 (AI 분석)"):
    st.write("나중에 모델 권한 문제가 해결되면 이 기능을 다시 활성화합니다.")
    uploaded_file = st.file_uploader("새로운 식단표 업로드", type=['png', 'jpg', 'jpeg'])
    if st.button("이미지 분석 시도"):
        st.warning("현재 모델 권한 확인 중입니다. 잠시 후 시도해 주세요.")
