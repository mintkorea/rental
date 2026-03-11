import streamlit as st
from datetime import datetime

# 1. 페이지 설정 (가장 먼저 실행)
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

# 2. 디자인 적용 (카드 스타일)
st.markdown("""
    <style>
    .menu-card { 
        padding: 20px; border-radius: 15px; border-left: 8px solid #4CAF50; 
        background-color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
        margin-bottom: 20px; min-height: 150px;
    }
    .focus-card { 
        border-left-color: #FF5252 !important; 
        background-color: #FFF8F8; 
        box-shadow: 0 6px 15px rgba(255, 82, 82, 0.2);
    }
    h3 { margin-top: 0; color: #333; }
    p { font-size: 1.1rem; color: #555; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# 3. 테스트용 데이터 정의
def get_test_data():
    return {
        "월": {"중식": "수제 돈까스, 스프, 샐러드", "석식": "매콤 제육볶음밥, 미역국"},
        "화": {"중식": "진한 사골순댓국, 깍두기", "석식": "안동찜닭, 당면사리"},
        "수": {"중식": "특식: 해물쟁반짜장, 탕수육", "석식": "순두부찌개, 계란말이"},
        "목": {"중식": "소불고기 덮밥, 겉절이", "석식": "고등어구이, 된장찌개"},
        "금": {"중식": "치킨마요, 미니우동", "석식": "얼큰 부대찌개, 라면사리"}
    }

# [핵심] 앱 실행 즉시 데이터가 없으면 무조건 테스트 데이터를 집어넣습니다.
if 'menu_data' not in st.session_state or st.session_state['menu_data'] is None:
    st.session_state['menu_data'] = get_test_data()

# 4. 날짜 및 시간 설정
now = datetime.now()
days = ["월", "화", "수", "목", "금", "토", "일"]
today_idx = now.weekday()
today_str = days[today_idx]
current_hour = now.hour

# 5. 메인 화면 구성
st.title("🍱 성의교정 실시간 식단")
st.write(f"📅 오늘은 **{today_str}요일**입니다. (현재 시간: {current_hour}시)")

# 6. 식단 표시 섹션 (업로드 버튼보다 위에 배치하여 바로 보이게 함)
st.divider()

# 요일 선택 박스 (기본값은 오늘 요일)
# 주말(토,일)일 경우 월요일(0)을 기본값으로 보여줍니다.
selected_day = st.selectbox("📅 다른 요일 식단 보기", days[:5], index=today_idx if today_idx < 5 else 0)
menu = st.session_state['menu_data'].get(selected_day, {"중식": "데이터 없음", "석식": "데이터 없음"})

col1, col2 = st.columns(2)

# 오후 2시(14시) 이전이면 점심 강조, 이후면 저녁 강조
is_lunch_time = current_hour < 14

with col1:
    # 오늘 날짜이고 점심 시간일 때 강조
    is_focus = (is_lunch_time and selected_day == today_str)
    card_class = "menu-card focus-card" if is_focus else "menu-card"
    st.markdown(f"""<div class="{card_class}">
        <h3>🍴 중식 {'<span style="color:#FF5252;">⭐</span>' if is_focus else ''}</h3>
        <hr>
        <p>{menu['중식']}</p>
    </div>""", unsafe_allow_html=True)

with col2:
    # 오늘 날짜이고 저녁 시간일 때 강조
    is_focus = (not is_lunch_time and selected_day == today_str)
    card_class = "menu-card focus-card" if is_focus else "menu-card"
    st.markdown(f"""<div class="{card_class}">
        <h3>🌙 석식 {'<span style="color:#FF5252;">⭐</span>' if is_focus else ''}</h3>
        <hr>
        <p>{menu['석식']}</p>
    </div>""", unsafe_allow_html=True)

# 7. 하단 업로드 섹션 (필요할 때만 열어서 사용)
st.divider()
with st.expander("📷 새로운 식단표 사진 업로드하기 (AI 분석)"):
    st.info("현재 API 권한 확인 중입니다. 테스트 데이터를 통해 UI를 확인해 주세요.")
    uploaded_file = st.file_uploader("이미지 선택", type=['png', 'jpg', 'jpeg'])
    if uploaded_file and st.button("🚀 이미지 분석 (현재 비활성)"):
        st.warning("API 연결이 필요합니다. 테스트 데이터를 사용 중입니다.")

# 8. 개발자용 사이드바 테스트 도구
with st.sidebar:
    st.header("⚙️ 테스트 도구")
    # 슬라이더를 움직여서 밤 시간으로 바꾸면 '석식' 카드가 강조되는지 확인할 수 있습니다.
    virtual_hour = st.slider("가상 시간 설정", 0, 23, current_hour)
    if virtual_hour != current_hour:
        # 가상 시간을 선택하면 즉시 반영되도록 로직 수정 가능
        st.info(f"설정된 시간: {virtual_hour}시")
