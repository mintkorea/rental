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

# 근무조 로직
def get_work_shift(d):
    anchor = date(2026, 3, 13)
    diff = (d - anchor).days
    shifts = [{"n": "A조", "bg": "#FF9800"}, {"n": "B조", "bg": "#E91E63"}, {"n": "C조", "bg": "#2196F3"}]
    return shifts[diff % 3]

def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

if 'target_date' not in st.session_state: st.session_state.target_date = today_kst()
if 'search_performed' not in st.session_state: st.session_state.search_performed = False

# 2. CSS 스타일 (부서명 우측 정렬 유지)
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
    .nav-link-bar {
        display: flex !important; width: 100% !important; background: white !important; 
        border: 1px solid #D1D9E6 !important; border-radius: 0 0 10px 10px !important; 
        margin-bottom: 25px !important;
    }
    .nav-item { flex: 1; text-align: center; padding: 12px 0; text-decoration: none; color: #1E3A5F; font-weight: bold; border-right: 1px solid #F0F0F0; font-size: 13px; }
    .nav-item:last-child { border-right: none; }

    .building-header { font-size: 18px !important; font-weight: bold; color: #2E5077; margin-top: 15px; border-bottom: 2px solid #2E5077; padding-bottom: 5px; margin-bottom: 12px; }
    .event-card { border: 1px solid #E0E0E0; border-left: 5px solid #2E5077; padding: 12px 14px; border-radius: 5px; margin-bottom: 12px !important; background-color: #ffffff; }
    .bottom-info { font-size: 11px; color: #666; margin-top: 10px; border-top: 1px solid #f5f5f5; padding-top: 8px; display: flex; justify-content: space-between; align-items: center; }
    
    .link-btn {
        display: block; padding: 14px; margin-bottom: 8px; background: #F0F4F8; color: #1E3A5F !important;
        text-decoration: none; border-radius: 10px; font-weight: bold; text-align: center; border: 1px solid #D1D9E6; font-size: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# 3. 검색 폼
with st.form("search_form"):
    selected_date = st.date_input("날짜", value=st.session_state.target_date, label_visibility="collapsed")
    ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
    selected_bu_list = [b for b in ALL_BU if st.checkbox(b, value=(b in ["성의회관", "의생명산업연구원"]), key=f"f_{b}")]
    
    c1, c2 = st.columns(2)
    show_t = c1.checkbox("당일", value=True)
    show_p = c2.checkbox("기간", value=True)
    
    if st.form_submit_button("🔍 검색", use_container_width=True):
        st.session_state.target_date = selected_date
        st.session_state.search_performed = True
        st.query_params["d"] = selected_date.strftime("%Y-%m-%d")
        st.rerun()

# 4. 데이터 조회 (생략)
@st.cache_data(ttl=300)
def get_data(d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": d.strftime('%Y-%m-%d'), "end": d.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return pd.DataFrame(res.json().get('res', [])) if res.status_code == 200 else pd.DataFrame()
    except: return pd.DataFrame()

# 5. 결과 출력
if st.session_state.search_performed:
    st.markdown('<div id="result-anchor"></div>', unsafe_allow_html=True)
    d = st.session_state.target_date
    df_raw = get_data(d)
    shift = get_work_shift(d)
    
    st.markdown(f"""
    <div class="date-display-box">
        <span class="res-main-title">{d.strftime("%Y.%m.%d")} 대관 현황</span>
        <span style="background:{shift['bg']}; color:white; padding:2px 10px; border-radius:12px; font-size:14px;">근무 : {shift['n']}</span>
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
        # ... (대관 카드 렌더링 로직 생략 - 기존과 동일) ...

# --- 핵심 수정 부분 ---

# 6. 숨겨둔 바로가기 링크 (슬라이딩 메뉴)
# 앵커 지점 설정: 메뉴가 열릴 때 이 지점으로 스크롤됨
st.markdown('<div id="sliding-menu-top"></div>', unsafe_allow_html=True)

with st.expander("🔗 자주 찾는 홈페이지 (열기)", expanded=False):
    # 메뉴 내부
    st.markdown('<a href="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do" target="_blank" class="link-btn">🏫 대관 신청 현황</a>', unsafe_allow_html=True)
    st.markdown('<a href="https://scube.s-tec.co.kr/sso/user/login/view" target="_blank" class="link-btn">🔐 S-CUBE 통합인증</a>', unsafe_allow_html=True)
    st.markdown('<a href="https://pms.s-tec.co.kr/mainfrm.php" target="_blank" class="link-btn">📂 개인정보관리</a>', unsafe_allow_html=True)
    st.markdown('<a href="https://www.onsafe.co.kr/" target="_blank" class="link-btn">📖 온세이프</a>', unsafe_allow_html=True)
    st.markdown('<a href="https://todayshift.com/" target="_blank" class="link-btn">📅 오늘근무</a>', unsafe_allow_html=True)
    
    # [강력한 한 방] 이 스크립트는 익스팬더가 '열릴 때'만 작동하여 화면을 위로 끌어올립니다.
    components.html("""
        <script>
            window.parent.document.getElementById('sliding-menu-top').scrollIntoView({behavior: 'smooth', block: 'start'});
        </script>
    """, height=0)

# 7. 자동 스크롤 보조
components.html("""
    <script>
        // 결과창 자동 스크롤
        if (window.parent.document.getElementById('result-anchor')) {
            window.parent.document.getElementById('result-anchor').scrollIntoView({behavior: 'smooth', block: 'start'});
        }
    </script>
""", height=0)
