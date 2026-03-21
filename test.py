import streamlit as st
import pandas as pd
import io
from datetime import datetime

# 1. 데이터 구조화 (사진 3, 4, 5번 기반 샘플 데이터 - 실제 전체 데이터로 확장 가능)
@st.cache_data
def get_building_master_data():
    data = [
        {"건물": "성의회관", "층": "14F", "내용": "게스트하우스(1404~1421호), 학교관리(개인사용)"},
        {"건물": "성의회관", "층": "4F", "내용": "강의실(421, 422호), 학생휴게실, 의학교육지원팀"},
        {"건물": "의생명산업연구원", "층": "1F", "내용": "대학원 강의실(1002~1004), 물품보관실, 세포배양실"},
        {"건물": "의생명산업연구원", "층": "4F", "내용": "감염내과, 내분비내과, 혈액내과, 진단검사"},
        {"건물": "옴니버스 파크", "층": "A동 1F", "내용": "대강의실(1001), 푸드코트, 루카스바이오"},
        {"건물": "옴니버스 파크", "층": "C동 8F", "내용": "간호대학장실, 조교실, 게스트하우스"}
    ]
    return pd.DataFrame(data)

# 2. 스타일 및 음성 인식 스크립트
st.markdown("""
<style>
    .main-title { font-size: 24px; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 10px; }
    .stDataFrame { width: 100%; }
    .voice-btn { background-color: #FF4B4B; color: white; border-radius: 5px; padding: 5px 10px; border: none; cursor: pointer; }
</style>
<script>
    function startDictation() {
        if (window.hasOwnProperty('webkitSpeechRecognition')) {
            var recognition = new webkitSpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = "ko-KR";
            recognition.start();
            recognition.onresult = function(e) {
                document.getElementById('search_input').value = e.results[0][0].transcript;
                recognition.stop();
            };
        }
    }
</script>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 대관 및 입주 현황 조회</div>', unsafe_allow_html=True)

# 3. [가이드라인] 엑셀 다운로드 최상단 배치
master_df = get_building_master_data()
st.download_button(label="📥 전체 입주 현황 엑셀 다운로드", data=io.BytesIO().getvalue(), 
                   file_name="입주현황_마스터.xlsx", use_container_width=True)

# 4. 검색 및 음성 입력 기능
st.subheader("🔍 입주 정보 검색")
col1, col2 = st.columns([4, 1])
search_query = col1.text_input("건물, 층 또는 입주명을 입력하세요", key="search_input", label_visibility="collapsed")
if col2.button("🎤 음성"):
    st.components.v1.html("<script>startDictation();</script>", height=0)

# 5. [검색 결과 필터링] 
if search_query:
    filtered_df = master_df[master_df.apply(lambda row: search_query in str(row.values), axis=1)]
else:
    filtered_df = master_df

# 6. 층별 표(Table) 형태 시각화
st.markdown("### 🏢 층별 상세 안내")
st.table(filtered_df) # 또는 st.dataframe(filtered_df, use_container_width=True)

# 7. [가이드라인] 하단 고정 정보 (촘촘한 디자인)
st.markdown("---")
with st.expander("🔗 참고 지침 및 링크", expanded=False):
    st.markdown('<div style="font-size:14px; line-height:1.4;">• 강의실 개방: 421, 422호 등 주중 오전 개방</div>', unsafe_allow_html=True)
    st.markdown('<a href="https://www.onsafe.co.kr" style="font-size:14px; color:#1E3A5F;">• 👮 경비직무 교육 (온세이프)</a>', unsafe_allow_html=True)
