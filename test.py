import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# [기존 설정 및 CSS 유지...]
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# [스타일 섹션에 당직/입주 현황 전용 CSS 추가]
st.markdown("""
    <style>
    /* ... 기존 CSS 유지 ... */
    .duty-box { background-color: #f8f9fa; border-left: 5px solid #1E3A5F; padding: 15px; margin: 10px 0; border-radius: 5px; border: 1px solid #dee2e6; }
    .duty-title { font-size: 16px; font-weight: bold; color: #1E3A5F; margin-bottom: 8px; display: flex; align-items: center; }
    .duty-text { font-size: 13px; line-height: 1.5; color: #333; }
    .caution { color: #d32f2f; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 1. 휴일 당직 및 입주 현황 데이터 정의
@st.cache_data
def get_static_data():
    duty_df = pd.DataFrame([
        {"일자": "2026-03-21", "성명": "김태남", "연락처": "3147-8262", "행사": "2026 WOUND MEETING"},
        {"일자": "2026-03-22", "성명": "한정욱", "연락처": "3147-8261", "행사": "전북대학교 치과대학 학술대회"},
        {"일자": "2026-03-28", "성명": "한정욱", "연락처": "3147-8261", "행사": "제29차 당뇨병 교육자 연수강좌"},
        {"일자": "2026-03-29", "성명": "김태남", "연락처": "3147-8262", "행사": "제67차 대한천식알레르기학회 교육강좌"}
    ])
    # 입주 현황 (사진 데이터 기반)
    occupancy_df = pd.DataFrame([
        {"건물": "성의회관", "층": "14F", "내용": "게스트하우스(1404~1421호), 학교관리용"},
        {"건물": "의생명산업연구원", "층": "1F", "내용": "대학원 강의실(1002~1004), 물품보관실"},
        {"건물": "옴니버스 파크", "층": "A동 1F", "내용": "대강의실(1001), 푸드코트, 루카스바이오"}
    ])
    return duty_df, occupancy_df

# [기존 create_excel, get_shift, get_data 함수 유지...]

# 메인 로직 시작
duty_master, occupancy_master = get_static_data()
# ... (상단 설정 메뉴 및 데이터 로드 유지) ...

if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        
        # [로직] 화관, 의산연 모두 행사가 없으면 아예 노출하지 않음
        target_bus = ["성의회관", "의생명산업연구원"]
        check_df = day_df[day_df['건물명'].str.replace(" ","").isin([b.replace(" ","") for b in target_bus])]
        
        if not check_df.empty:
            st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
            
            for bu in sel_bu:
                # [가이드라인] 건물명 정확히 일치(==)로 중복 차단
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")].sort_values('시간')
                
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                # 대관 리스트 출력 (가로 표/세로 카드 분기 로직 유지)
                if not b_df.empty:
                    # ... (기존 출력 로직) ...
                    pass
                else:
                    st.markdown('<div class="no-data">ℹ️ 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
                
                # [신규] 의산연 출력 직후 당직 안내 추가
                if bu == "의생명산업연구원":
                    today_duty = duty_master[duty_master['일자'] == d_str]
                    if not today_duty.empty:
                        d_row = today_duty.iloc[0]
                        st.markdown(f"""
                            <div class="duty-box">
                                <div class="duty-title">📅 의학교육지원팀 당직근무 안내</div>
                                <div class="duty-text">
                                    <b>당직근무자: {d_row['성명']} ({d_row['연락처']})</b> | 행사: {d_row['행사']}<br>
                                    문제시 주말 당직자에게 연락 주세요. 안될 시 총무팀 주종호 선생(010-3324-1187)에게 연락하여 강의실 변경!<br>
                                    구내번호 외에 주말에 핸드폰 연락하지 마세요. <span class="caution">안 될 시 마리아홀 조정실 확인 바랍니다.</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
        curr += timedelta(days=1)

# [신규] 하단 건물별 입주 현황 검색 섹션
st.markdown("---")
st.markdown('<div class="main-title">🏢 건물별 입주 현황 검색</div>', unsafe_allow_html=True)

if 'search_key' not in st.session_state: st.session_state.search_key = ""

col1, col2 = st.columns([4, 1])
search_val = col1.text_input("검색어", value=st.session_state.search_key, placeholder="건물, 층, 입주기관 검색...", label_visibility="collapsed")
if col2.button("🔄 초기화", use_container_width=True):
    st.session_state.search_key = ""
    st.rerun()

if search_val:
    res_df = occupancy_master[occupancy_master.apply(lambda r: search_val in str(r.values), axis=1)]
    st.dataframe(res_df, use_container_width=True, hide_index=True)
else:
    st.dataframe(occupancy_master, use_container_width=True, hide_index=True)
