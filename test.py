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

# 요일 및 근무조 계산 함수
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_work_shift(d):
    anchor = date(2026, 3, 13)
    diff = (d - anchor).days
    shifts = [{"n": "A조", "bg": "#FF9800"}, {"n": "B조", "bg": "#E91E63"}, {"n": "C조", "bg": "#2196F3"}]
    return shifts[diff % 3]

# 세션 상태 초기화
if 'target_date' not in st.session_state:
    st.session_state.target_date = today_kst()
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

# URL 파라미터 처리
url_params = st.query_params
if "d" in url_params:
    try:
        url_d = datetime.strptime(url_params["d"], "%Y-%m-%d").date()
        st.session_state.target_date = url_d
        st.session_state.search_performed = True
    except: pass

# 2. CSS 스타일 (당직 박스 스타일 추가)
st.markdown("""
<style>
    #top-anchor { position: absolute; top: 0; left: 0; }
    .block-container { padding: 1rem 1.2rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 20px !important; }
    .date-display-box { 
        text-align: center; background-color: #F8FAFF; padding: 15px 10px 8px 10px; 
        border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none; 
    }
    .res-main-title { font-size: 20px !important; font-weight: 800; color: #1E3A5F; display: block; margin-bottom: 4px; }
    .res-sub-title { font-size: 18px !important; font-weight: 700; color: #333; }
    .nav-link-bar {
        display: flex !important; width: 100% !important; background: white !important; 
        border: 1px solid #D1D9E6 !important; border-radius: 0 0 10px 10px !important; 
        margin-bottom: 25px !important; overflow: hidden !important;
    }
    .nav-item {
        flex: 1 !important; text-align: center !important; padding: 10px 0 !important;
        text-decoration: none !important; color: #1E3A5F !important; font-weight: bold !important; 
        border-right: 1px solid #F0F0F0 !important; font-size: 13px !important;
    }
    .building-header { font-size: 18px !important; font-weight: bold; color: #2E5077; margin-top: 15px; border-bottom: 2px solid #2E5077; padding-bottom: 5px; margin-bottom: 12px; }
    .event-card { border: 1px solid #E0E0E0; border-left: 5px solid #2E5077; padding: 12px 14px; border-radius: 5px; margin-bottom: 12px !important; background-color: #ffffff; }
    
    /* 🔴 당직 안내 박스 스타일 */
    .duty-card { 
        background-color: #FFF4F4; border: 1px solid #FFDADA; border-left: 5px solid #FF4B4B; 
        padding: 12px; margin: 10px 0 20px 0; border-radius: 5px; 
    }
    .duty-title { font-size: 15px; font-weight: bold; color: #D32F2F; margin-bottom: 5px; }
    .duty-content { font-size: 13px; line-height: 1.5; color: #333; }
    
    .link-btn { display: block; padding: 5px 0; color: #1E3A5F !important; text-decoration: none; font-weight: bold; text-align: center; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

# 3. 입력부
with st.form("search_form"):
    selected_date = st.date_input("날짜", value=st.session_state.target_date, label_visibility="collapsed")
    st.markdown('**🏢 건물 선택**')
    ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "대학본관", "서울성모별관"]
    selected_bu_list = [b for b in ALL_BU if st.checkbox(b, value=(b in ["성의회관", "의생명산업연구원"]), key=f"f_{b}")]
    if st.form_submit_button("🔍 검색", use_container_width=True):
        st.session_state.target_date = selected_date
        st.session_state.search_performed = True
        st.query_params["d"] = selected_date.strftime("%Y-%m-%d")
        st.rerun()

# 4. 데이터 크롤링 함수
@st.cache_data(ttl=300)
def get_data(d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": d.strftime('%Y-%m-%d'), "end": d.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return pd.DataFrame(res.json().get('res', [])) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# 5. 결과 출력부
if st.session_state.search_performed:
    st.markdown('<div id="result-anchor"></div>', unsafe_allow_html=True)
    d = st.session_state.target_date
    df_raw = get_data(d)
    shift = get_work_shift(d)
    
    # 당직 데이터 정의
    duty_dict = {
        "2026-03-21": {"n": "김태남", "p": "3147-8262", "e": "2026 WOUND MEETING"},
        "2026-03-22": {"n": "한정욱", "p": "3147-8261", "e": "전북대학교 치과대학 학술대회"},
        "2026-03-28": {"n": "한정욱", "p": "3147-8261", "e": "제29차 당뇨병 교육자 연수강좌"},
        "2026-03-29": {"n": "김태남", "p": "3147-8262", "e": "제67차 대한천식알레르기학회 교육강좌"}
    }

    # 성의회관/의산연 행사 여부 체크 (노출 제어)
    check_bus = ["성의회관", "의생명산업연구원"]
    has_event = not df_raw[df_raw['buNm'].str.replace(" ","").isin([b.replace(" ","") for b in check_bus])].empty if not df_raw.empty else False

    if has_event:
        w_idx = d.weekday()
        w_str, w_class = ['월','화','수','목','금','토','일'][w_idx], ("sat" if w_idx == 5 else ("sun" if w_idx == 6 else ""))
        
        # 날짜 헤더
        st.markdown(f"""
        <div class="date-display-box">
            <span class="res-main-title">성의교정 대관 현황</span>
            <span class="res-sub-title">{d.strftime("%Y.%m.%d")}.<span class="{w_class}">({w_str})</span>
            <span style="background:{shift['bg']}; color:white; padding:2px 10px; border-radius:12px; font-size:14px; margin-left:5px; vertical-align:middle;">근무 : {shift['n']}</span></span>
        </div>
        <div class="nav-link-bar">
            <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-item">◀ Before</a>
            <a href="./?d={today_kst().strftime('%Y-%m-%d')}" target="_self" class="nav-item">Today</a>
            <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-item">Next ▶</a>
        </div>
        """, unsafe_allow_html=True)

        target_wd = str(d.weekday() + 1)
        for bu in selected_bu_list:
            st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
            bu_content = False
            
            if not df_raw.empty:
                bu_df = df_raw[df_raw['buNm'].str.replace(" ","") == bu.replace(" ","")].copy()
                if not bu_df.empty:
                    bu_content = True
                    for _, row in bu_df.sort_values(by='startTime').iterrows():
                        s_cls, s_txt = ("status-y", "예약확정") if row['status'] == 'Y' else ("status-n", "신청대기")
                        st.markdown(f"""
                        <div class="event-card">
                            <span class="status-badge {s_cls}">{s_txt}</span>
                            <div style="font-size:16px; font-weight:bold; color:#1E3A5F; margin-bottom:4px;">📍 {row['placeNm']}</div>
                            <div style="color:#FF4B4B; font-weight:bold; font-size:15px; margin:4px 0;">⏰ {row['startTime']} ~ {row['endTime']}</div>
                            <div style="font-size:14px; color:#333; font-weight:bold;">📄 {row['eventNm']}</div>
                            <div style="font-size:12px; color:#666; margin-top:8px;">👤 {row['mgDeptNm']}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            if not bu_content:
                st.markdown('<div style="color:#999; text-align:center; padding:15px; border:1px dashed #eee; font-size:13px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

            # [핵심 배치] 의산연 리스트 바로 뒤에 당직 안내 출력
            d_key = d.strftime('%Y-%m-%d')
            if bu == "의생명산업연구원" and d_key in duty_dict:
                duty = duty_dict[d_key]
                st.markdown(f"""
                <div class="duty-card">
                    <div class="duty-title">📅 의학교육지원팀 당직근무 안내</div>
                    <div class="duty-content">
                        <b>당직자: {duty['n']} ({duty['p']})</b><br>
                        <b>행사:</b> {duty['e']}<br>
                        주말 당직자 미연락 시 총무팀 주종호(1187) 선생 문의.<br>
                        <span style="color:#D32F2F; font-weight:bold;">※ 구내번호 연락 안 될 시 마리아홀 조정실 확인 바랍니다.</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    else:
        st.info("해당 날짜에 성의회관/의산연 대관 행사가 없습니다.")

# 6. 자주 찾는 링크
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("🔗 자주 찾는 홈페이지", expanded=False):
    st.markdown('''
        <a href="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do" target="_blank" class="link-btn">• 🏫 대관신청 현황</a>
        <a href="https://www.onsafe.co.kr" target="_blank" class="link-btn">• 👮 직무 교육 (온세이프)</a>
        <a href="https://todayshift.com/" target="_blank" class="link-btn">• 📅 오늘근무</a>
    ''', unsafe_allow_html=True)

st.markdown("""<div style="position:fixed; bottom:20px; right:20px; z-index:999;"><a href="#top-anchor" style="display:block; background:#1E3A5F; color:white; width:45px; height:45px; line-height:45px; text
