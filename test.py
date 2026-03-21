import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 대관 및 입주 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 15px; }
    .duty-box { background-color: #f8f9fa; border-left: 5px solid #1E3A5F; padding: 12px; margin: 10px 0; border-radius: 5px; border: 1px solid #dee2e6; }
    .duty-text { font-size: 13px; line-height: 1.5; color: #333; }
    .caution { color: #d32f2f; font-weight: bold; }
    /* ... 기존 대관 카드 관련 CSS 유지 ... */
    </style>
""", unsafe_allow_html=True)

# 2. 입주 현황 및 당직 데이터 (사진 텍스트 추출 반영)
@st.cache_data
def get_static_master():
    # 사진 3, 4, 5번 데이터를 기반으로 구성
    occ_data = [
        {"건물": "성의회관", "층": "14F", "내용": "게스트하우스(1404~1410호: 포스텍, 1413~1421호: 학교관리)"},
        {"건물": "성의회관", "층": "12F", "내용": "행정지원팀, 연구교수실, 세미나실, 공동실험실"},
        {"건물": "성의회관", "층": "4F", "내용": "의학교육지원팀, 강의실(421, 422호), 학사지원팀"},
        {"건물": "의생명산업연구원", "층": "1F", "내용": "대학원 강의실(1002~1004), 물품보관실, 세포배양실"},
        {"건물": "의생명산업연구원", "층": "4F", "내용": "감염내과, 내분비내과, 혈액내과, 진단검사"},
        {"건물": "옴니버스 파크(A동)", "층": "1F", "내용": "대강의실(1001), 푸드코트, 루카스바이오"},
        {"건물": "의과대학(A동)", "층": "8F", "내용": "교수실, 미생물학교실, 예방의학교실, 의학통계학"},
        # ... 필요시 추가 데이터 삽입
    ]
    # 사진 8번 당직 데이터
    duty_data = [
        {"일자": "2026-03-21", "성명": "김태남", "연락처": "3147-8262", "행사": "2026 WOUND MEETING"},
        {"일자": "2026-03-22", "성명": "한정욱", "연락처": "3147-8261", "행사": "전북대학교 치과대학 학술대회"},
        {"일자": "2026-03-28", "성명": "한정욱", "연락처": "3147-8261", "행사": "제29차 당뇨병 교육자 연수강좌"},
        {"일자": "2026-03-29", "성명": "김태남", "연락처": "3147-8262", "행사": "제67차 대한천식알레르기학회 교육강좌"}
    ]
    return pd.DataFrame(occ_data), pd.DataFrame(duty_data)

# [기존 get_data, create_excel 함수는 그대로 유지하되, df 정의 시점을 앞으로 당깁니다]

st.markdown('<div class="main-title">🏫 성의교정 대관 및 입주 현황</div>', unsafe_allow_html=True)

# 설정 영역
with st.expander("🔍 설정 및 엑셀 다운로드", expanded=True):
    c1, c2, c3 = st.columns([1.5, 2, 1])
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    # [중요] NameError 방지: df를 컬럼 밖에서 먼저 선언하거나, 컬럼 안에서 명확히 생성
    df = get_data(s_date, e_date) 
    with c2:
        sel_bu = st.multiselect("건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크", "의과대학", "간호대학"], default=["성의회관", "의생명산업연구원"])
    with c3:
        view_mode = st.radio("보기", ["카드", "표"], horizontal=True)
        if not df.empty:
            st.download_button("📥 엑셀 저장", data=create_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

# 메인 출력부
occ_master, duty_master = get_static_master()

if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        
        # 성의회관/의산연 행사 여부 체크
        target_check = day_df[day_df['건물명'].str.contains("성의회관|의생명산업연구원")]
        
        if not target_check.empty:
            st.markdown(f'<div class="date-bar">📅 {d_str}</div>', unsafe_allow_html=True)
            for bu in sel_bu:
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                # 대관 리스트 출력 (기존 로직)
                # ...
                
                # [반영] 의산연 출력 직후 당직 안내
                if bu == "의생명산업연구원":
                    today_duty = duty_master[duty_master['일자'] == d_str]
                    if not today_duty.empty:
                        d_row = today_duty.iloc[0]
                        st.markdown(f"""
                            <div class="duty-box">
                                <div class="duty-title">📅 의학교육지원팀 당직근무 안내 (마리아홀)</div>
                                <div class="duty-text">
                                    <b>당직근무자: {d_row['성명']} ({d_row['연락처']})</b><br>
                                    문제시 주말 당직자에게 연락 주세요. 안될 시 총무팀 주종호 선생(1187)에게 연락!<br>
                                    <span class="caution">※ 구내번호 외에 주말에 개인 핸드폰으로 연락하지 마세요.</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        curr += timedelta(days=1)

# 하단 입주 현황 검색 기능
st.markdown("---")
st.subheader("🏢 건물별 층별 입주 현황 검색")
search_val = st.text_input("검색어를 입력하세요 (예: 421호, 행정지원팀, 의과대학)", key="occ_search")
if search_val:
    filtered_occ = occ_master[occ_master.apply(lambda r: search_val in str(r.values), axis=1)]
    st.table(filtered_occ)
else:
    st.table(occ_master.head(10)) # 기본은 상위 10개만
