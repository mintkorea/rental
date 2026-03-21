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

# [핵심] 3월 마리아홀(의학연구지원팀) 주말 당직 데이터
DUTY_DATA = {
    "2026-03-21": {"성명": "김태남", "연락처": "3147-8262", "행사": "2026 WOUND MEETING"},
    "2026-03-22": {"성명": "한정욱", "연락처": "3147-8261", "행사": "전북대학교 치과대학 학술대회"},
    "2026-03-28": {"성명": "한정욱", "연락처": "3147-8261", "행사": "제29차 당뇨병 교육자 연수강좌"},
    "2026-03-29": {"성명": "김태남", "연락처": "3147-8262", "행사": "제67차 대한천식알레르기학회 교육강좌"}
}

# 2. 스타일 및 헬퍼 함수
st.markdown("""
<style>
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 20px; }
    .duty-card { background-color: #FFF4F4; border-left: 5px solid #FF4B4B; padding: 12px; margin: 10px 0; border-radius: 5px; border: 1px solid #FFDADA; }
    .duty-header { font-size: 15px; font-weight: bold; color: #D32F2F; margin-bottom: 5px; }
    .event-card { border: 1px solid #E0E0E0; border-left: 5px solid #2E5077; padding: 12px; border-radius: 5px; margin-bottom: 10px; background: white; }
    .building-header { font-size: 18px; font-weight: bold; color: #2E5077; margin-top: 15px; border-bottom: 2px solid #2E5077; padding-bottom: 5px; }
</style>
""", unsafe_allow_html=True)

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

# 3. 입력부 및 로직
st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

with st.form("search_form"):
    selected_date = st.date_input("날짜 선택", value=today_kst())
    selected_bu = st.multiselect("🏢 건물 선택", 
                               options=["성의회관", "의생명산업연구원", "옴니버스 파크"], 
                               default=["성의회관", "의생명산업연구원"])
    submit = st.form_submit_button("🔍 검색", use_container_width=True)

# 4. 결과 출력
d_str = selected_date.strftime("%Y-%m-%d")
df = get_data(selected_date)
shift = get_work_shift(selected_date)

# 상단 정보바
st.info(f"📅 {d_str} | 근무조: {shift['n']}")

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    # 해당 건물의 대관 정보 필터링
    bu_df = pd.DataFrame()
    if not df.empty:
        bu_df = df[df['buNm'].str.replace(" ", "").str.contains(bu.replace(" ", ""), na=False)]
    
    if not bu_df.empty:
        for _, row in bu_df.iterrows():
            st.markdown(f"""
            <div class="event-card">
                <div style="font-weight:bold; color:#1E3A5F;">📍 {row['placeNm']}</div>
                <div style="color:#FF4B4B; font-size:14px;">⏰ {row['startTime']} ~ {row['endTime']}</div>
                <div style="font-size:13px;">📄 {row['eventNm']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.write("대관 내역이 없습니다.")

    # [중요] 의산연 출력 직후 당직 내역 추가
    if bu == "의생명산업연구원" and d_str in DUTY_DATA:
        duty = DUTY_DATA[d_str]
        st.markdown(f"""
        <div class="duty-card">
            <div class="duty-header">📢 의학연구지원팀 당직 안내</div>
            <div style="font-size: 13px; color: #333;">
                <b>당직자: {duty['성명']} ({duty['연락처']})</b><br>
                <b>행사:</b> {duty['행사']}<br>
                <span style="color: #D32F2F; font-weight: bold;">※ 문제 시 마리아홀 조정실 근무자 확인</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")
st.caption("건의사항: 시설관리팀 (내선 1187)")
