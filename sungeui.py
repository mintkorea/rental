import streamlit as st
from datetime import datetime

# 1. 기존의 모든 상태를 무시하고 페이지 설정
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

# 2. 강제로 디자인 CSS 주입 (이미지 업로드 버튼보다 우선 순위)
st.markdown("""
    <style>
    /* 배경 및 카드 스타일 */
    .main { background-color: #F8F9FA; }
    .menu-card {
        background-color: white;
        padding: 25px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        margin-bottom: 20px;
        border-left: 8px solid #2E7D32; /* 딥 그린 강조 */
    }
    .focus-card {
        border-left-color: #D32F2F !important; /* 강조 시 빨간색 테두리 */
        background-color: #FFF8F8;
    }
    .card-title { font-size: 1.3rem; font-weight: bold; color: #333; margin-bottom: 10px; }
    .menu-content { font-size: 1.1rem; color: #555; line-height: 1.6; }
    </style>
    """, unsafe_allow_html=True)

# 3. 화면 구성 (디자인을 업로드 버튼보다 무조건 위에 배치)
st.title("🍱 성의교정 실시간 식단")

# 테스트용 식단 데이터
test_menu = {
    "중식": "수제 돈까스, 스프, 가든 샐러드",
    "석식": "제육볶음밥, 콩나물국, 계란후라이"
}

st.subheader("오늘의 추천 메뉴")

# 현재 시간에 따른 카드 노출 (오후 2시 기준)
now = datetime.now()
is_lunch = now.hour < 14

col1, col2 = st.columns(2)

with col1:
    style = "menu-card focus-card" if is_lunch else "menu-card"
    st.markdown(f"""
        <div class="{style}">
            <div class="card-title">🍴 중식 {'(추천)' if is_lunch else ''}</div>
            <div class="menu-content">{test_menu['중식']}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    style = "menu-card focus-card" if not is_lunch else "menu-card"
    st.markdown(f"""
        <div class="{style}">
            <div class="card-title">🌙 석식 {'(추천)' if not is_lunch else ''}</div>
            <div class="menu-content">{test_menu['석식']}</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()

# 4. 이미지 업로드 부분은 맨 아래로 이동
with st.expander("📷 식단표 새로 올리기"):
    st.file_uploader("이미지를 선택하세요", type=['png', 'jpg', 'jpeg'])
