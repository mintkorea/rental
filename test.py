import streamlit as st
import pandas as pd
import io

# [검증 1] 사진 기반 전수 입주 현황 데이터 (테스트용)
@st.cache_data
def get_master_data():
    data = [
        # 성의회관 (사진 3번 참조)
        {"건물": "성의회관", "층": "14F", "내용": "게스트하우스(1404~1421호), 학교관리용"},
        {"건물": "성의회관", "층": "12F", "내용": "행정지원팀, 연구교수실(1202~1204), 세미나실"},
        {"건물": "성의회관", "층": "4F", "내용": "강의실(421, 422호), 학생휴게실, 의학교육지원팀"},
        {"건물": "성의회관", "층": "2F", "내용": "마리아홀, 성당, 교목실, 학생상담센터"},
        # 의생명산업연구원 (사진 4번 참조)
        {"건물": "의생명산업연구원", "층": "1F", "내용": "대학원 강의실(1002~1004), 물품보관실, 세포배양실"},
        {"건물": "의생명산업연구원", "층": "2F", "내용": "정보전략팀 서버실, 세포생산 A/B구역"},
        {"건물": "의생명산업연구원", "층": "4F", "내용": "감염내과, 내분비내과, 혈액내과, 시과학연구소"},
        {"건물": "의생명산업연구원", "층": "5F", "내용": "류마티스센터, 영상의학교실, 정신과학교실"},
        # 옴니버스 파크 (사진 5번 참조 - 정확한 명칭 분리)
        {"건물": "옴니버스 파크", "층": "A동 1F", "내용": "대강의실(1001), 푸드코트, 루카스바이오"},
        {"건물": "옴니버스 파크", "층": "B동 3F", "내용": "초저온냉동고실, 디지털팜, 진코어"},
        {"건물": "옴니버스 파크", "층": "C동 8F", "내용": "간호대학장실, 조교실, 게스트하우스"},
        {"건물": "옴니버스 파크 의과대학", "층": "8F", "내용": "미생물학교실, 예방의학교실, 의학통계학"},
        {"건물": "옴니버스 파크 간호대학", "층": "5F", "내용": "교수실, 세미나실, 복사실"}
    ]
    return pd.DataFrame(data)

# 페이지 설정 및 CSS (가이드라인 준수)
st.set_page_config(page_title="성의교정 통합 조회", layout="centered")
st.markdown("""
<style>
    .main-title { font-size: 22px; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 10px; }
    .stTable { font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 및 입주 현황</div>', unsafe_allow_html=True)

# [검증 2] 검색 및 초기화 로직
if 'search_query' not in st.session_state:
    st.session_state.search_query = ""

c1, c2 = st.columns([4, 1])
with c1:
    search_input = st.text_input("검색", value=st.session_state.search_query, 
                                placeholder="건물명, 층, 호실 검색...", label_visibility="collapsed")
with c2:
    if st.button("🔄 초기화", use_container_width=True):
        st.session_state.search_query = ""
        st.rerun()

master_df = get_master_data()

# [검증 3] 데이터 필터링 (중복 차단 및 검색)
if search_input:
    # 검색어가 있을 때: 전체 키워드 검색
    display_df = master_df[master_df.apply(lambda row: search_input in str(row.values), axis=1)]
    st.info(f"🔍 '{search_input}' 검색 결과 ({len(display_df)}건)")
else:
    # 검색어가 없을 때: 전체 리스트 (테스트 데이터 전수 노출)
    display_df = master_df
    st.write(f"📋 전체 입주 현황 ({len(display_df)}건)")

# 결과 표 출력
st.table(display_df)

# [가이드라인] 엑셀 다운로드 (MIME 타입 지정으로 .bin 에러 방지)
output = io.BytesIO()
with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
    display_df.to_excel(writer, index=False)
st.download_button(label="📥 현재 화면 엑셀 다운로드", data=output.getvalue(), 
                   file_name="성의교정_현황.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
