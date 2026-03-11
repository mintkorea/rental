import streamlit as st
from datetime import datetime
import json

# 1. 페이지 설정 및 시각적 요소 (성의교정 아이덴티티 반영)
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

st.markdown("""
    <style>
    .menu-card { padding: 25px; border-radius: 18px; border-left: 6px solid #e0e0e0; 
                background-color: white; box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 25px; transition: 0.3s; }
    .focus-card { border-left-color: #2E7D32 !important; background-color: #f1f8e9; transform: scale(1.02); }
    .time-badge { font-size: 0.8rem; padding: 4px 10px; border-radius: 20px; background-color: #2E7D32; color: white; margin-bottom: 10px; display: inline-block; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바: 테스트 및 시간 제어
with st.sidebar:
    st.header("🛠️ 앱 컨트롤 센터")
    # 404 에러 우회를 위한 테스트 모드
    test_mode = st.toggle("테스트 모드 활성화", value=True, help="켜져 있으면 AI 분석 대신 미리 준비된 데이터를 사용합니다.")
    st.divider()
    # 실시간 UI 변화 확인용 가상 시간 슬라이더
    st.write("🕒 **가상 시간 시뮬레이터**")
    virtual_hour = st.slider("현재 시간 설정(시)", 0, 23, datetime.now().hour)

# 3. 날짜 및 시간 데이터 계산
now = datetime.now()
days = ["월", "화", "수", "목", "금", "토", "일"]
today_idx = now.weekday()
today_str = days[today_idx]

# 오전 0~14시는 중식, 그 이후는 석식 추천
is_lunch_focus = virtual_hour < 14
focus_label = "중식" if is_lunch_focus else "석식"

# 4. 가짜(Mock) 데이터 로직
def get_mock_data():
    return {
        "월": {"중식": "수제돈까스 & 크림스프", "석식": "매콤 제육볶음밥"},
        "화": {"중식": "진한 사골순댓국", "석식": "안동찜닭 & 당면사리"},
        "수": {"중식": "특식: 해물쟁반짜장", "석식": "순두부찌개 & 계란말이"},
        "목": {"중식": "소불고기 덮밥", "석식": "고등어구이 & 된장찌개"},
        "금": {"중식": "치킨마요 & 미니우동", "석식": "얼큰 부대찌개"}
    }

# 5. 메인 UI 구성
st.title("🍱 성의교정 스마트 식단")
st.markdown(f"#### {now.strftime('%m월 %d일')} ({today_str})")

# 시간대별 맞춤 안내 메시지
if is_lunch_focus:
    st.success(f"🍴 지금은 **점심 메뉴**를 확인하기 딱 좋은 시간입니다!")
else:
    st.warning(f"🌙 오늘 저녁엔 무엇을 먹을까요? **석식 메뉴**입니다.")

# 6. 데이터 로드 및 분석 섹션
if 'menu_data' not in st.session_state:
    st.session_state['menu_data'] = None

with st.expander("📷 식단표 업데이트 (이미지 분석)", expanded=not st.session_state['menu_data']):
    uploaded_file = st.file_uploader("주간 식단표 이미지를 선택하세요", type=['png', 'jpg', 'jpeg'])
    if uploaded_file and st.button("🚀 분석 시작"):
        if test_mode:
            st.session_state['menu_data'] = get_mock_data()
            st.success("테스트용 주간 식단이 로드되었습니다!")
        else:
            st.error("현재 모델(gemini-1.5-flash) 권한 승인 대기 중입니다. 테스트 모드를 활용해 주세요.")

# 7. 식단 표시 (데이터가 있을 때만 실행)
if st.session_state['menu_data']:
    st.divider()
    
    # 요일 선택 필터 (기본값은 오늘 요일)
    selected_day = st.radio("보고 싶은 요일을 선택하세요", days[:5], index=today_idx if today_idx < 5 else 0, horizontal=True)
    menu = st.session_state['menu_data'].get(selected_day, {})

    col1, col2 = st.columns(2)

    with col1:
        # 중식 카드 강조 조건: 추천 시간대이고 선택된 요일이 오늘일 때
        is_highlight = is_lunch_focus and selected_day == today_str
        card_style = "menu-card focus-card" if is_highlight else "menu-card"
        badge = '<div class="time-badge">NOW 🍴</div>' if is_highlight else ""
        
        st.markdown(f"""
            <div class="{card_style}">
                {badge}
                <h3>중식 메뉴</h3>
                <hr>
                <p style="font-size: 1.1rem;">{menu.get('중식', '식단 정보가 없습니다.')}</p>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # 석식 카드 강조 조건
        is_highlight = not is_lunch_focus and selected_day == today_str
        card_style = "menu-card focus-card" if is_highlight else "menu-card"
        badge = '<div class="time-badge" style="background-color: #D32F2F;">NOW 🌙</div>' if is_highlight else ""
        
        st.markdown(f"""
            <div class="{card_style}">
                {badge}
                <h3>석식 메뉴</h3>
                <hr>
                <p style="font-size: 1.1rem;">{menu.get('석식', '식단 정보가 없습니다.')}</p>
            </div>
        """, unsafe_allow_html=True)
