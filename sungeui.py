import streamlit as st
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

# 2. 디자인 (CSS)
st.markdown("""
    <style>
    .menu-card { padding: 20px; border-radius: 15px; border-left: 6px solid #4CAF50; 
                background-color: white; box-shadow: 0 4px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .focus-card { border-left-color: #ff4b4b !important; background-color: #fff5f5; }
    </style>
    """, unsafe_allow_html=True)

# 3. 테스트 데이터 (앱을 켜자마자 보이게 하려면 이 데이터를 미리 넣어둬야 합니다)
def get_initial_data():
    return {
        "월": {"중식": "돈까스, 스프", "석식": "김치볶음밥"},
        "화": {"중식": "제육볶음, 쌈", "석식": "잔치국수"},
        "수": {"중식": "짜장면, 탕수육", "석식": "된장찌개"},
        "목": {"중식": "비빔밥, 미역국", "석식": "고등어구이"},
        "금": {"중식": "카레라이스", "석식": "부대찌개"}
    }

# 앱 시작 시 데이터가 없으면 자동으로 테스트 데이터 주입
if 'menu_data' not in st.session_state or st.session_state['menu_data'] is None:
    st.session_state['menu_data'] = get_initial_data()

# 4. 시간 및 요일 설정
now = datetime.now()
days = ["월", "화", "수", "목", "금", "토", "일"]
today_idx = now.weekday()
today_str = days[today_idx]
current_hour = now.hour

# 5. UI 상단
st.title("🍱 성의교정 실시간 식단")
st.write(f"오늘은 **{today_str}요일**입니다. (현재 시간: {current_hour}시)")

# 6. 식단 표시 (이 부분이 이제 무조건 실행됩니다)
selected_day = st.selectbox("요일을 선택하세요", days[:5], index=today_idx if today_idx < 5 else 0)
menu = st.session_state['menu_data'].get(selected_day, {})

st.divider()

col1, col2 = st.columns(2)

# 점심/저녁 시간대별 자동 강조 로직
is_lunch_time = current_hour < 14

with col1:
    # 오늘 날짜이고 점심 시간일 때만 강조
    highlight = "focus-card" if (is_lunch_time and selected_day == today_str) else ""
    st.markdown(f"""<div class="menu-card {highlight}">
        <h3>🍴 중식 {'⭐' if highlight else ''}</h3>
        <p>{menu.get('중식', '정보 없음')}</p>
    </div>""", unsafe_allow_html=True)

with col2:
    # 오늘 날짜이고 저녁 시간일 때만 강조
    highlight = "focus-card" if (not is_lunch_time and selected_day == today_str) else ""
    st.markdown(f"""<div class="menu-card {highlight}">
        <h3>🌙 석식 {'⭐' if highlight else ''}</h3>
        <p>{menu.get('석식', '정보 없음')}</p>
    </div>""", unsafe_allow_html=True)

# 7. 하단 (나중에 쓸 AI 기능)
with st.expander("📷 식단표 사진으로 업데이트하기"):
    st.info("현재 API 점검 중입니다. 테스트 데이터를 확인해 주세요.")
    uploaded_file = st.file_uploader("이미지 선택", type=['png', 'jpg', 'jpeg'])
