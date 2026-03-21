import streamlit as st
import pandas as pd
import requests
import io
from datetime import datetime

# 1. 건물별 입주 현황 데이터 (보내주신 사진 기반 구조화)
BUILDING_INFO = {
    "성의회관": {
        "14F": "게스트하우스 (포스텍 기숙사, 학교관리용)",
        "11F": "효도서관 (24시간 출입문 폐쇄)",
        "4F": "학생휴계실, 강의실(421, 422호), 의학교육지원팀",
        "2F": "마리아홀, 성당, 교목실, 학생상담센터",
        "B1-B2": "주차장, 기계실, 창고"
    },
    "의생명산업연구원": {
        "1F": "물품보관실, 대학원 강의실(1002, 1003), 세포배양실",
        "2F": "정보전략팀 서버실, 세포생산 B/A구역, 박경호 교수실",
        "4F": "감염내과, 내분비내과, 혈액내과, 세포조직공학연구소",
        "별관": "가톨릭국제술기교육센터(5F), 한센병연구소(1F)"
    },
    "옴니버스 파크": {
        "의과대학(A동)": "8F(교수실), 4F(연구기술지원팀), 1F(대강의실, 푸드코트)",
        "연구동(B동)": "3F(초저온냉동고실), 1F(한미약품제재연구소)",
        "간호대학(C동)": "8F(게스트하우스), 4F(간호대학장실, 조교실)"
    }
}

def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# 2. CSS 스타일 (가이드라인 준수: 촘촘한 간격 및 최상단 배치용)
st.markdown("""
<style>
    .main-title { font-size: 24px; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 10px; }
    .building-header { font-size: 18px; font-weight: bold; color: #2E5077; border-bottom: 2px solid #2E5077; padding-bottom: 5px; margin-top: 20px; }
    .info-row { font-size: 14px; line-height: 1.4; color: #333; padding: 2px 0; }
    .floor-label { font-weight: bold; color: #1E3A5F; min-width: 50px; display: inline-block; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 및 입주 현황</div>', unsafe_allow_html=True)

# 3. [가이드라인] 엑셀 다운로드 최상단 배치
# (get_data로 가져온 df_raw가 있다고 가정)
if 'df_raw' in locals() and not df_raw.empty:
    st.download_button(label="📥 현재 날짜 대관 엑셀 다운로드", data=to_excel(df_raw), 
                       file_name=f"대관현황_{datetime.now().strftime('%Y%m%d')}.xlsx", use_container_width=True)

# 4. [가이드라인] 대관 정보 출력 (중복 차단 로직 포함)
# (기존 대관 출력 반복문 실행 시 아래 조건 사용)
# bu_df = df_raw[df_raw['buNm'].str.replace(" ", "") == selected_bu.replace(" ", "")]

# 5. [신규] 건물별 입주 현황 섹션 (사진 데이터 반영)
st.markdown('<div class="building-header">🏢 건물별 입주 현황 (상세)</div>', unsafe_allow_html=True)
selected_b = st.selectbox("현황을 확인할 건물을 선택하세요", list(BUILDING_INFO.keys()))

with st.container():
    for floor, desc in BUILDING_INFO[selected_b].items():
        st.markdown(f'<div class="info-row"><span class="floor-label">[{floor}]</span> {desc}</div>', unsafe_allow_html=True)

# 6. [가이드라인] 하단 고정 정보
with st.expander("🔗 자주 찾는 링크 및 지침", expanded=False):
    st.markdown('<div class="info-row">• 강의실(421, 422, 521, 522호) 주중 오전 개방</div>', unsafe_allow_html=True)
    st.markdown('<a href="https://www.onsafe.co.kr" style="text-decoration:none; color:#1E3A5F;">• 👮 경비직무 교육 (온세이프)</a>', unsafe_allow_html=True)
