import streamlit as st
from datetime import datetime

# 1. 페이지 설정 및 성의교정 테마 (Deep Green) 적용
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

st.markdown("""
    <style>
    /* 전체 배경색 (연한 그레이) */
    .main { background-color: #F9FAFB; }
    
    /* 카드 기본 스타일 (화이트, 그림자, 둥근 모서리) */
    .menu-card {
        background-color: white;
        padding: 24px;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        border: 1px solid #E5E7EB;
        transition: all 0.3s ease;
    }
    
    /* 현재 시간대 카드 강조 (딥 그린 테두리, 연한 그린 배경) */
    .focus-card {
        border: 2px solid #2E7D32 !important;
        background-color: #F1F8E9;
        transform: translateY(-3px); /* 살짝 떠오르는 효과 */
        box-shadow: 0 6px 20px rgba(46, 125, 50, 0.15);
    }
    
    /* 카드 헤더 (아이콘 + 타이틀) */
    .card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 18px;
        border-bottom: 1px solid #E5E7EB;
        padding-bottom: 10px;
    }
    
    /* 타이틀 폰트 */
    .card-title {
        font-size: 1.4rem;
        font-weight: 700;
        color: #111827;
        margin: 0;
    }
    
    /* 메뉴 텍스트 폰트 (가독성 중시) */
    .menu-text {
        font-size: 1.1rem;
        color: #4B5563;
        line-height: 1.8;
        white-space: pre-wrap; /* 줄바꿈 유지 */
    }
    
    /* '추천' 배지 스타일 */
    .badge {
        background-color: #2E7D32;
        color: white;
        padding: 4px 10px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: bold;
        margin-left: auto; /* 오른쪽 끝 배치 */
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 시간 및 요일 데이터 계산
now = datetime.now()
current_hour = now.hour
is_lunch_time = current_hour < 14  # 오후 2시 기준

# 요일 표시 (테스트용으로 오늘 요일 고정)
days = ["월", "화", "수", "목", "금", "토", "일"]
today_str = days[now.weekday()]

# 3. 테스트용 식단 데이터 (보류 중인 AI 기능 대신 노출)
# 실제 앱에서는 이 부분이 AI 분석 결과나 DB 데이터로 대체됩니다.
menu = {
    "중식": "• 수제 등심 돈까스 & 브라운 소스\n• 고소한 크림 스프\n• 오리엔탈 드레싱 가든 샐러드\n• 포기김치",
    "석식": "• 매콤 달콤 제육볶음밥\n• 맑은 콩나물국\n• 계란후라이 (완숙)\n• 깍두기"
}

# 4. 메인 UI 구성
st.title("🍱 성의교정 스마트 식단")
st.markdown(f"#### 📅 오늘은 **{today_str}요일**입니다.")
st.write("바쁜 일과 속, 오늘 당신의 에너지를 책임질 식단을 확인하세요.")

st.divider()

# 5. 카드 레이아웃 구성 (2열 배분)
col1, col2 = st.columns(2)

with col1:
    # 중식 카드 (오전~점심시간 강조)
    # 현재 시간이 14시 이전이면 'focus-card' 클래스를 추가하여 강조합니다.
    focus_class = "focus-card" if is_lunch_time else ""
    badge_html = '<span class="badge">추천 🍴</span>' if is_lunch_time else ""
    
    st.markdown(f"""
        <div class="menu-card {focus_class}">
            <div class="card-header">
                <span style="font-size: 1.8rem;">🍴</span>
                <h3 class="card-title">중식</h3>
                {badge_html}
            </div>
            <p class="menu-text">{menu['중식']}</p>
        </div>
    """, unsafe_allow_html=True)

with col2:
    # 석식 카드 (오후~저녁시간 강조)
    # 현재 시간이 14시 이후이면 강조합니다. 배지 색상을 주황색 계열로 차별화합니다.
    focus_class = "focus-card" if not is_lunch_time else ""
    badge_html = '<span class="badge" style="background-color: #F57C00;">추천 🌙</span>' if not is_lunch_time else ""
    
    st.markdown(f"""
        <div class="menu-card {focus_class}">
            <div class="card-header">
                <span style="font-size: 1.8rem;">🌙</span>
                <h3 class="card-title">석식</h3>
                {badge_html}
            </div>
            <p class="menu-text">{menu['석식']}</p>
        </div>
    """, unsafe_allow_html=True)

# 6. 하단 안내 (보류된 기능 표시)
st.divider()
st.caption("※ 위 식단은 테스트 데이터입니다. 실제 AI 분석 기능은 현재 점검 중입니다.")
