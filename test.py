import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 초기화
st.set_page_config(page_title="성의교정 대관 및 입주 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# [중요] NameError 방지를 위해 빈 데이터프레임으로 df 우선 초기화
df = pd.DataFrame()

# 2. 스타일 설정 (당직 안내 박스 포함)
st.markdown("""
    <style>
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 15px; }
    .duty-box { background-color: #fdf2f2; border-left: 5px solid #e74c3c; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .duty-title { font-size: 16px; font-weight: bold; color: #c0392b; margin-bottom: 8px; }
    .duty-text { font-size: 13px; line-height: 1.6; color: #333; }
    .caution { color: #d32f2f; font-weight: bold; text-decoration: underline; }
    /* 기존 스타일 유지... */
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (기존 get_data 함수 유지)
@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    # ... (기존 API 호출 로직과 동일) ...
    # 테스트를 위해 빈 결과가 나올 수 있으므로 항상 DataFrame 리턴 보장
    return pd.DataFrame() 

# 4. 당직 및 입주 마스터 데이터 (사진 기반)
def get_static_masters():
    # 사진 8번 당직 내역 반영
    duty_data = pd.DataFrame([
        {"일자": "2026-03-21", "성명": "김태남", "연락처": "3147-8262", "행사": "2026 WOUND MEETING"},
        {"일자": "2026-03-22", "성명": "한정욱", "연락처": "3147-8261", "행사": "전북대학교 치과대학 학술대회"},
        {"일자": "2026-03-28", "성명": "한정욱", "연락처": "3147-8261", "행사": "제29차 당뇨병 교육자 연수좌"},
        {"일자": "2026-03-29", "성명": "김태남", "연락처": "3147-8262", "행사": "제67차 대한천식알레르기학회 교육강좌"}
    ])
    # 사진 3, 4, 5번 입주 현황 데이터 (샘플)
    occ_data = pd.DataFrame([
        {"건물": "성의회관", "층": "4F", "내용": "의학교육지원팀, 강의실(421, 422호), 학사지원팀"},
        {"건물": "의생명산업연구원", "층": "1F", "내용": "대학원 강의실(1002~1004), 세포배양실"},
        {"건물": "옴니버스파크", "층": "A동 1F", "내용": "대강의실(1001), 푸드코트, 루카스바이오"}
    ])
    return duty_data, occ_data

st.markdown('<div class="main-title">🏫 성의교정 대관 및 입주 현황</div>', unsafe_allow_html=True)

# 5. 상단 설정 메뉴
with st.expander("🔍 설정 및 엑셀 다운로드", expanded=True):
    c1, c2, c3 = st.columns([1.5, 2, 1])
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    
    # [수정] df 정의를 조건문 밖으로 꺼내서 NameError 방지
    df = get_data(s_date, e_date)
    
    with c2:
        sel_bu = st.multiselect("건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크"], default=["성의회관", "의생명산업연구원"])
    with c3:
        view_mode = st.radio("보기", ["카드", "표"], horizontal=True)

# 6. 대관 및 당직 안내 출력
duty_master, occ_master = get_static_masters()

if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        
        # 성의회관/의산연 행사 여부 체크 (하나라도 있어야 출력)
        has_main_event = not day_df[day_df['건물명'].str.contains("성의회관|의생명산업연구원")].empty
        
        if has_main_event:
            st.markdown(f'<div class="date-bar">📅 {d_str}</div>', unsafe_allow_html=True)
            for bu in sel_bu:
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                # 대관 리스트 출력 로직 (생략)
                
                # [반영] 의산연 출력 후 당직 안내
                if bu == "의생명산업연구원":
                    today_duty = duty_master[duty_master['일자'] == d_str]
                    if not today_duty.empty:
                        d_row = today_duty.iloc[0]
                        st.markdown(f"""
                            <div class="duty-box">
                                <div class="duty-title">📢 의학교육지원팀 당직근무 안내</div>
                                <div class="duty-text">
                                    <b>당직자: {d_row['성명']} ({d_row['연락처']})</b> | <b>행사:</b> {d_row['행사']}<br>
                                    문제 시 주말 당직자에게 연락 주세요. 연락 안 될 시 총무팀 주종호 선생(1187)에게 연락 바랍니다.<br>
                                    <span class="caution">구내번호 외에 주말에 핸드폰으로 연락하지 마세요.</span> 마리아홀 조정실에서 근무자 확인이 가능합니다.
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("조회된 대관 내역이 없습니다.")

# 7. 하단 입주 현황 검색 기능 (표 형태)
st.markdown("---")
st.subheader("🏢 건물별 층별 입주 현황 검색")
search_q = st.text_input("검색어 입력 (예: 421호, 의학교육, 성의회관)", key="occ_search")
if search_q:
    f_df = occ_master[occ_master.apply(lambda r: search_q in str(r.values), axis=1)]
    st.table(f_df)
else:
    st.table(occ_master)
