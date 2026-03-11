import streamlit as st

# 1. 디자인 정의 (카드 스타일)
st.markdown("""
    <style>
    .card {
        padding: 20px; border-radius: 15px; border: 2px solid #2E7D32;
        background-color: #F1F8E9; margin-bottom: 20px;
    }
    .title { font-weight: bold; font-size: 1.2rem; color: #2E7D32; }
    </style>
    """, unsafe_allow_html=True)

# 2. 화면 출력 (무조건 실행됨)
st.title("🍱 성의교정 식단")

# 중식 카드
st.markdown('<div class="card"><p class="title">🍴 중식 (오늘의 추천)</p><p>돈까스, 스프, 샐러드</p></div>', unsafe_allow_html=True)

# 석식 카드
st.markdown('<div class="card" style="border-color:#ddd; background-color:white;"><p class="title" style="color:#666;">🌙 석식</p><p>제육볶음, 쌈채소</p></div>', unsafe_allow_html=True)
