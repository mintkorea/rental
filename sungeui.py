import streamlit as st
from datetime import datetime

# 1. 페이지 설정 (가장 상단에 위치)
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

# 2. 디자인 (CSS) - 1번 카드형 레이아웃
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .menu-card {
        background-color: white;
        padding: 24px;
        border-radius: 18px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 20px;
        border-left: 8px solid #e0e0e0;
    }
    /* 강조 스타일: 딥 그린 */
    .focus-card {
        border-left-color: #2E7D32 !important;
        background-color: #f1f8e9;
    }
    .card-title {
        font-size: 1.4rem;
        font-weight: bold;
        color: #333;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
    }
    .menu-content {
        font-size: 1.1rem;
        color: #444;
        line-height: 1.6;
    }
    .highlight-tag {
        background-color: #2E7D32;
        color: white;
        font-size: 0.7rem;
        padding: 2px 8px;
        border-radius: 10px;
        margin-left: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 3. 데이터 설정
now = datetime.now()
days = ["월", "화", "수", "목", "금", "토", "일"]
today_idx = now.weekday()
today_str = days[today_idx]
current_hour = now.hour

# 기본 식단 데이터
menu_db = {
    "월": {"중식": "수제돈까스, 크림스프, 양배추샐러드", "석식": "매콤제육덮밥, 콩나물국"},
    "화": {"중식": "우거지국밥, 고등어구이, 겉절이", "석식": "데리야끼치킨밥, 단무지무침"},
    "수": {"중식": "해물짜장면, 미니탕수육, 짜사이", "석식": "부대찌개, 라면사리, 공기밥"},
    "목": {"중식": "소불고기덮밥, 미역국, 깍두기", "석식": "순두부찌개, 계란말이, 김"},
    "금": {"중식": "카레라이스, 가라아게, 우동국물", "석식": "닭갈비비빔밥, 유부장국"}
}

# 4. 메인 화면 출력
st.title("🍱 성의교정 스마트 식단")
st.write(f"📅 오늘은 **{today_str}요일**입니다. (현재 시간: {current_hour}시)")

# 요일 선택 (selectbox가 가장 오류가 적습니다)
selected_day = st.selectbox("요일을 선택하세요", days[:5], index=today_idx if today_idx < 5 else 0)

st.divider()

# 5. 카드 레이아웃 구성
menu = menu_db.get(selected_day, menu_db["월"])

# 점심(14시 이전) / 저녁(14시 이후) 판단
is_lunch_time = current_hour < 14
# 선택한 요일이 오늘일 때만 강조 표시
is_today = (selected_day == today_str)

col1, col2 = st.columns(2)

with col1:
    is_focus = is_today and is_lunch_time
    style = "menu-card focus-card" if is_focus else "menu-card"
    tag = '<span class="highlight-tag">지금 메뉴</span>' if is_focus else ""
    st.markdown(f"""
        <div class="{style}">
            <div class="card-title">🍴 중식 {tag}</div>
            <div class="menu-content">{menu['중식']}</div>
        </div>
    """, unsafe_allow_html=True)

with col2:
    is_focus = is_today and not is_lunch_time
    style = "menu-card focus-card" if is_focus else "menu-card"
    tag = '<span class="highlight-tag" style="background-color:#F57C00;">지금 메뉴</span>' if is_focus else ""
    st.markdown(f"""
        <div class="{style}">
            <div class="card-title">🌙 석식 {tag}</div>
            <div class="menu-content">{menu['석식']}</div>
        </div>
    """, unsafe_allow_html=True)

st.divider()
st.caption("※ 이 앱은 현재 시간과 요일에 맞춰 식단을 자동으로 추천합니다.")
