import streamlit as st
from datetime import datetime

# 1. 페이지 설정 및 디자인(CSS)
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

st.markdown("""
    <style>
    /* 메인 배경 및 폰트 */
    .main { background-color: #F8F9FA; }
    
    /* 카드 디자인 */
    .menu-card {
        background-color: white;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.06);
        margin-bottom: 20px;
        border: 1px solid #E5E7EB;
        transition: transform 0.2s ease;
    }
    
    /* 현재 시간대 강조 (딥 그린) */
    .focus-card {
        border: 2px solid #2E7D32 !important;
        background-color: #F1F8E9;
        transform: translateY(-3px);
    }
    
    .card-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
    }
    
    .card-title {
        font-size: 1.3rem;
        font-weight: 700;
        color: #111827;
        margin: 0;
    }
    
    .menu-text {
        font-size: 1.1rem;
        color: #4B5563;
        line-height: 1.7;
    }
    
    .badge {
        background-color: #2E7D32;
        color: white;
        padding: 2px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: auto;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 날짜 및 시간 계산
now = datetime.now()
days = ["월", "화", "수", "목", "금", "토", "일"]
today_idx = now.weekday()
today_str = days[today_idx]
current_hour = now.hour

# 3. 고정 식단 데이터 (테스트용)
# 나중에 이 데이터를 사용자님이 직접 수정할 수 있게 바꿀 예정입니다.
menu_db = {
    "월": {"중식": "돈까스, 스프, 샐러드", "석식": "김치볶음밥, 계란후라이"},
    "화": {"중식": "제육볶음, 쌈채소", "석식": "잔치국수, 만두"},
    "수": {"중식": "짜장면, 탕수육", "석식": "된장찌개, 고등어구이"},
    "목": {"중식": "비빔밥, 미역국", "석식": "부대찌개, 라면사리"},
    "금": {"중식": "카레라이스, 우동", "석식": "순두부찌개, 제육"},
}

# 4. 상단 헤더
st.title("🍱 성의교정 식단 대시보드")
st.write(f"오늘은 **{today_str}요일**입니다. 현재 시간은 **{current_hour}시**입니다.")

# 5. 요일 선택기
selected_day = st.segmented_control(
    "요일 선택", days[:5], default=today_str if today_idx < 5 else "월"
)

# 6. 식단 카드 출력
st.divider()
menu = menu_db.get(selected_day, menu_db["월"])
is_lunch_focus = current_hour < 14 and selected_day == today_str

col1, col2 = st.columns(2)

with col1:
    # 중식 카드
    style = "menu-card focus-card" if is_lunch_focus else "menu-card"
    badge = '<span class="badge">NOW</span>' if is_lunch_focus else ""
    st.markdown(f"""
        <div class="{style}">
            <div class="card-header">
                <span>🍴</span>
                <h3 class="card-title">중식</h3>
                {badge}
            </div>
            <p class="menu-text">{menu['중식']}</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    # 석식 카드
    is_dinner_focus = current_hour >= 14 and selected_day == today_str
    style = "menu-card focus-card" if is_dinner_focus else "menu-card"
    badge = '<span class="badge" style="background-color:#F57C00;">NOW</span>' if is_dinner_focus else ""
    st.markdown(f"""
        <div class="{style}">
            <div class="card-header">
                <span>🌙</span>
                <h3 class="card-title">석식</h3>
                {badge}
            </div>
            <p class="menu-text">{menu['석식']}</p>
        </div>
    """, unsafe_allow_html=True)

st.divider()
st.info("💡 요일 버튼을 클릭하면 해당 요일의 식단을 확인할 수 있습니다.")
