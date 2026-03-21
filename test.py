import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import streamlit.components.v1 as components
from zoneinfo import ZoneInfo

# 1. 페이지 설정 및 시간대
KST = ZoneInfo("Asia/Seoul")
def today_kst(): return datetime.now(KST).date()

st.set_page_config(page_title="성의교정 대관 조회(M)", page_icon="🏫", layout="centered")

# [데이터] 3월 마리아홀(의학연구지원팀) 주말 당직 정보
DUTY_DATA = {
    "2026-03-21": {"성명": "김태남", "연락처": "3147-8262", "행사": "2026 WOUND MEETING"},
    "2026-03-22": {"성명": "한정욱", "연락처": "3147-8261", "행사": "전북대학교 치과대학 학술대회"},
    "2026-03-28": {"성명": "한정욱", "연락처": "3147-8261", "행사": "제29차 당뇨병 교육자 연수강좌"},
    "2026-03-29": {"성명": "김태남", "연락처": "3147-8262", "행사": "제67차 대한천식알레르기학회 교육강좌"}
}

# 2. 스타일 설정
st.markdown("""
<style>
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 15px; }
    .building-header { font-size: 18px !important; font-weight: bold; color: #2E5077; margin-top: 20px; border-bottom: 2px solid #2E5077; padding-bottom: 5px; }
    .duty-card { background-color: #FFF4F4; border-left: 5px solid #FF4B4B; padding: 12px; margin: 10px 0; border-radius: 5px; border: 1px solid #FFDADA; }
    .event-card { border: 1px solid #E0E0E0; border-left: 5px solid #2E5077; padding: 12px; border-radius: 5px; margin-bottom: 10px; background: white; }
</style>
""", unsafe_allow_html=True)

# 3. 로직 함수
def get_work_shift(d):
    anchor = date(2026, 3, 13)
    diff = (d - anchor).days
    shifts = [{"n": "A조", "bg": "#FF9800"}, {"n": "B조", "bg": "#E91E63"}, {"n": "C조", "bg": "#2196F3"}]
    return shifts[diff % 3]

@st.cache_data(ttl=300)
def get_data(d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": d.strftime('%Y-%m-%d'), "end": d.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, timeout=10)
        return pd.DataFrame(res.json().get('res', []))
    except: return pd.DataFrame()

# 4. 입력부 (건물 목록 누락 해결)
st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

with st.form("search_form"):
    col1, col2 = st.columns(2)
    with col1:
        s_date = st.date_input("날짜 선택", value=today_kst())
    
    st.write("**🏢 건물 선택**")
    ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
    
    # 체크박스 형태로 전체 목록 표시
    selected_bus = []
    cols = st.columns(2)
    for i, bu_name in enumerate(ALL_BU):
        with cols[i % 2]:
            if st.checkbox(bu_name, value=(bu_name in ["성의회관", "의생명산업연구원"])):
                selected_bus.append(bu_name)
                
    submit = st.form_submit_button("🔍 검색 실행", use_container_width=True)

# 5. 결과 출력부 (NameError 방지를 위해 변수 초기화)
d_str = s_date.strftime("%Y-%m-%d")
df = get_data(s_date)
shift = get_work_shift(s_date)

st.info(f"📅 {d_str} ({shift['n']} 근무)")

if not selected_bus:
    st.warning("조회할 건물을 선택해 주세요.")
else:
    for bu in selected_bus:
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        
        # 데이터 필터링 (공백 제거 비교로 정확도 높임)
        bu_df = pd.DataFrame()
        if not df.empty:
            bu_df = df[df['buNm'].str.replace(" ", "").str.contains(bu.replace(" ", ""), na=False)]
        
        if not bu_df.empty:
            for _, row in bu_df.iterrows():
                st.markdown(f"""
                <div class="event-card">
                    <div style="font-weight:bold; color:#1E3A5F;">📍 {row['placeNm']}</div>
                    <div style="color:#FF4B4B; font-weight:bold;">⏰ {row['startTime']} ~ {row['endTime']}</div>
                    <div style="font-size:14px; color:#333;">📄 {row['eventNm']}</div>
                    <div style="font-size:12px; color:#666; text-align:right;">👤 {row['mgDeptNm']}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.write("대관 내역이 없습니다.")

        # [핵심] 의산연 하단에 당직 안내 고정
        if bu == "의생명산업연구원" and d_str in DUTY_DATA:
            duty = DUTY_DATA[d_str]
            st.markdown(f"""
            <div class="duty-card">
                <div style="font-weight:bold; color:#D32F2F; margin-bottom:5px;">📢 의학연구지원팀 당직 안내</div>
                <div style="font-size:13px; line-height:1.6;">
                    <b>당직자:</b> {duty['성명']} ({duty['연락처']})<br>
                    <b>행사명:</b> {duty['행사']}<br>
                    <span style="color:#D32F2F;">※ 비상시 마리아홀 조정실 또는 총무팀(1187) 연락</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

st.markdown("---")
st.caption("관리: 시설관리팀 | 내선 1187")
