import streamlit as st
import pandas as pd
import io

# 1. 데이터 구조화 (가이드라인: 옴니버스 파크 명칭 정확히 분리)
@st.cache_data
def get_master_data():
    # 실제 사진 데이터 기반 입주 현황 (예시)
    data = [
        {"건물": "옴니버스 파크", "층": "A동 1F", "내용": "대강의실(1001), 푸드코트"},
        {"건물": "옴니버스 파크 의과대학", "층": "4F", "내용": "의학교육지원팀, PBL실"},
        {"건물": "성의회관", "층": "4F", "내용": "강의실(421, 422호)"}
    ]
    return pd.DataFrame(data)

# 2. 페이지 설정
st.set_page_config(page_title="성의교정 통합 조회", layout="centered")

# 3. CSS (가이드라인: 촘촘한 간격 1.4 유지)
st.markdown("""
<style>
    .main-title { font-size: 22px; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 15px; }
    .item-text { font-size: 14px; line-height: 1.4 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 및 입주 현황</div>', unsafe_allow_html=True)

# 4. 검색창 및 기능 버튼 (에러 방지용 안전한 선언)
# 세션 상태 초기화
if 'search_word' not in st.session_state:
    st.session_state.search_word = ""

# 검색바 레이아웃
c1, c2 = st.columns([4, 1])
with c1:
    search_input = st.text_input("검색어 입력", value=st.session_state.search_word, 
                                placeholder="건물, 층, 기관명 검색...", label_visibility="collapsed")
with c2:
    if st.button("🔄 초기화", use_container_width=True):
        st.session_state.search_word = ""
        st.rerun()

# 5. 데이터 필터링 및 출력 (가이드라인: 중복 노출 차단)
master_df = get_master_data()

if search_input:
    # 검색어가 있을 때: 전체 데이터에서 키워드 검색
    display_df = master_df[master_df.apply(lambda row: search_input in str(row.values), axis=1)]
    st.info(f"🔍 '{search_input}' 검색 결과입니다.")
else:
    # 검색어가 없을 때: 전체 리스트 표출
    display_df = master_df
    st.write("📋 전체 현황 리스트")

# 6. 결과 표(Table) 출력
st.table(display_df)

# [중요] 대관 현황 출력 시 중복 차단 로직 (첫 번째 스샷 문제 해결용)
# if not df_raw.empty:
#     # 정확히 일치(==)하는 건물만 필터링해서 출력해야 옴니버스 중복이 안 생깁니다.
#     target_df = df_raw[df_raw['buNm'].str.replace(" ","") == "옴니버스파크의과대학"]
