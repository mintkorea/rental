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

# 근무조 계산
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

# 2. CSS 스타일
st.markdown("""
<style>
    #top-anchor { position: absolute; top: 0; left: 0; }
    .block-container { padding: 0.5rem 1rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 10px !important; }
    
    /* 상단 날짜 및 네비게이션 박스 */
    .date-display-box { 
        text-align: center; background-color: #F8FAFF; padding: 12px 10px 5px 10px; 
        border-radius: 12px 12px 0 0; border: 1px solid #D1D9E6; border-bottom: none;
    }
    .res-main-title { font-size: 18px !important; font-weight: 800; color: #1E3A5F; display: block; margin-bottom: 2px; }
    .nav-link-bar {
        display: flex !important; width: 100% !important; background: white !important; 
        border: 1px solid #D1D9E6 !important; border-radius: 0 0 10px 10px !important; 
        margin-bottom: 15px !important; overflow: hidden !important;
    }
    .nav-item { flex: 1; text-align: center; padding: 10px 0; text-decoration: none; color: #1E3A5F; font-weight: bold; border-right: 1px solid #F0F0F0; font-size: 13px; }
    .nav-item:last-child { border-right: none; }

    /* 대관 카드 디자인 */
    .building-header { font-size: 17px !important; font-weight: bold; color: #2E5077; margin-top: 15px; border-bottom: 2px solid #2E5077; padding-bottom: 4px; margin-bottom: 10px; }
    .event-card { border: 1px solid #E0E0E0; border-left: 5px solid #2E5077; padding: 10px 12px; border-radius: 5px; margin-bottom: 10px !important; background-color: #ffffff; }
    .bottom-info { font-size: 11px; color: #666; margin-top: 8px; border-top: 1px solid #f5f5f5; padding-top: 6px; display: flex; justify-content: space-between; }
    
    /* 바로가기 버튼 */
    .link-btn {
        display: block; padding: 12px; margin-bottom: 6px; background: #F0F4F8; color: #1E3A5F !important;
        text-decoration: none; border-radius: 8px; font-weight: bold; text-align: center; border: 1px solid #D1D9E6; font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# 3. [개선] 검색 옵션을 Expander로 묶어 공간 절약
with st.expander("🔍 검색 옵션 설정 (날짜/건물)", expanded=not st.session_state.search_performed):
    with st.form("search_form"):
        selected_date = st.date_input("날짜", value=st.session_state.target_date)
        ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
        cols = st.columns(2)
        selected_bu_list = [b for i, b in enumerate(ALL_BU) if cols[i%2].checkbox(b, value=(b in ["성의회관", "의생명산업연구원"]))]
        
        c1, c2 = st.columns(2)
        show_t = c1.checkbox("당일", value=True)
        show_p = c2.checkbox("기간", value=True)
        
        if st.form_submit_button("조회하기", use_container_width=True):
            st.session_state.target_date = selected_date
            st.session_state.search_performed = True
            st.rerun()

# 4. 데이터 로직 (생략 - 기존과 동일)
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
    w_idx = d.weekday()
    w_str = ['월','화','수','목','금','토','일'][w_idx]
    
    st.markdown(f"""
    <div class="date-display-box">
        <span class="res-main-title">{d.strftime("%Y.%m.%d")}({w_str})</span>
        <span style="background:{shift['bg']}; color:white; padding:1px 8px; border-radius:10px; font-size:12px;">근무 : {shift['n']}</span>
    </div>
    <div class="nav-link-bar">
        <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-item">◀ 이전</a>
        <a href="./?d={today_kst().strftime('%Y-%m-%d')}" target="_self" class="nav-item">오늘</a>
        <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-item">다음 ▶</a>
    </div>
    """, unsafe_allow_html=True)

    target_wd = str(d.weekday() + 1)
    for bu in selected_bu_list:
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        has_content = False
        if not df_raw.empty:
            bu_df = df_raw[df_raw['buNm'].str.replace(" ", "").str.contains(bu.replace(" ", ""), na=False)].copy()
            if not bu_df.empty:
                t_ev = bu_df[bu_df['startDt'] == bu_df['endDt']] if show_t else pd.DataFrame()
                p_ev = bu_df[bu_df['startDt'] != bu_df['endDt']] if show_p else pd.DataFrame()
                v_p_ev = p_ev[p_ev['allowDay'].apply(lambda x: target_wd in [day.strip() for day in str(x).split(",")])] if not p_ev.empty else pd.DataFrame()
                
                for ev_df, title in [(t_ev, "📌 당일"), (v_p_ev, "🗓️ 기간")]:
                    if not ev_df.empty:
                        has_content = True
                        for _, row in ev_df.sort_values(by='startTime').iterrows():
                            st.markdown(f"""
                            <div class="event-card">
                                <div style="font-size:15px; font-weight:bold; color:#1E3A5F;">📍 {row['placeNm']}</div>
                                <div style="color:#FF4B4B; font-weight:bold; font-size:14px; margin:2px 0;">⏰ {row['startTime']} ~ {row['endTime']}</div>
                                <div style="font-size:13px; color:#333;">📄 {row['eventNm']}</div>
                                <div class="bottom-info">
                                    <span>🗓️ {row['startDt']}</span>
                                    <span style="font-weight:bold;">👤 {row['mgDeptNm']}</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        if not has_content: st.markdown('<div style="color:#999; text-align:center; font-size:12px; padding:10px;">내역 없음</div>', unsafe_allow_html=True)

# 6. 하단 바로가기 메뉴 (항상 노출하되 콤팩트하게)
st.markdown("<div class=\"building-header\">🔗 바로가기</div>", unsafe_allow_html=True)
st.markdown('<div id="link-section"></div>', unsafe_allow_html=True)
c_l, c_r = st.columns(2)
with c_l:
    st.markdown('<a href="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do" target="_blank" class="link-btn">🏫 대관현황</a>', unsafe_allow_html=True)
    st.markdown('<a href="https://scube.s-tec.co.kr/sso/user/login/view" target="_blank" class="link-btn">🔐 S-CUBE</a>', unsafe_allow_html=True)
with c_r:
    st.markdown('<a href="https://pms.s-tec.co.kr/mainfrm.php" target="_blank" class="link-btn">📂 개인정보</a>', unsafe_allow_html=True)
    st.markdown('<a href="https://todayshift.com/" target="_blank" class="link-btn">📅 오늘근무</a>', unsafe_allow_html=True)

# 7. 스크롤 보정 자바스크립트
components.html(f"""
    <script>
        const parentDoc = window.parent.document;
        // 검색 수행 시 결과창으로 이동
        if ({str(st.session_state.search_performed).lower()}) {{
            setTimeout(() => {{
                parentDoc.getElementById('result-anchor')?.scrollIntoView({{behavior: 'smooth', block: 'start'}});
            }}, 300);
        }}
    </script>
""", height=0)
