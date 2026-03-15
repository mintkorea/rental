import streamlit as st
import pandas as pd
import requests
import io

# [가이드라인] 디자인 통일 및 불필요한 간격 제거
st.markdown("""
<style>
    .main-title { font-size: 24px; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 5px; }
    .building-header { font-size: 18px; font-weight: bold; color: #2E5077; border-bottom: 2px solid #2E5077; padding-bottom: 5px; margin-top: 15px; }
    .event-card { border: 1px solid #E0E0E0; border-left: 5px solid #2E5077; padding: 12px; border-radius: 5px; margin-bottom: 10px; background-color: #ffffff; }
    
    /* 고정 정보(강의실/링크) 전용: 시스템 로직과 별개로 디자인만 촘촘하게 */
    .static-info { font-size: 14px; font-weight: bold; color: #333; line-height: 1.4 !important; margin-bottom: 2px; }
    .static-link { display: block; text-decoration: none; color: #1E3A5F !important; padding: 1px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

# [가이드라인] 1. 엑셀 버튼: 타이틀 바로 아래 배치
# (df_raw 데이터 로드 로직 생략)
st.download_button(label="📥 현재 날짜 대관 엑셀 다운로드", data=io.BytesIO().getvalue(), use_container_width=True)

# [가이드라인] 2. 데이터 추출: 중복 노출 차단 (Exact Match)
# bu_df = df_raw[df_raw['buNm'].str.replace(" ", "") == selected_bu.replace(" ", "")]

# [가이드라인] 3. 시스템과 상관없는 고정 정보 (하단 배치)
st.markdown('<div class="building-header">🔓 강의실 개방 지침 (참고용)</div>', unsafe_allow_html=True)
st.markdown('<div class="static-info">• 421, 422, 521, 522호 (주중 오전 개방)</div>', unsafe_allow_html=True)

st.markdown('<div class="building-header">🔗 자주 찾는 홈페이지</div>', unsafe_allow_html=True)
st.markdown('''
    <a href="https://songeui.catholic.ac.kr/..." class="static-link"><span class="static-info">• 🏫 대관신청 현황</span></a>
    <a href="https://www.onsafe.co.kr" class="static-link"><span class="static-info">• 👮 경비직무 교육 (온세이프)</span></a>
''', unsafe_allow_html=True)
