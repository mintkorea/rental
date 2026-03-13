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

# [수정] 근무조 계산 로직 (2026년 기준)
def get_work_shift(d):
    anchor = date(2026, 3, 13)
    diff = (d - anchor).days
    shifts = [
        {"n": "A조", "bg": "#FF9800"},
        {"n": "B조", "bg": "#E91E63"},
        {"n": "C조", "bg": "#2196F3"}
    ]
    return shifts[diff % 3]

def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

# 세션 관리 및 URL 파라미터 처리
if 'target_date' not in st.session_state:
    st.session_state.target_date = today_kst()
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

url_params = st.query_params
if "d" in url_params:
    try:
        param_date = datetime.strptime(url_params["d"], "%Y-%m-%d").date()
        if st.session_state.target_date != param_date:
            st.session_state.target_date = param_date
        st.session_state.search_performed = True
    except: pass

# 2. CSS 스타일 (동일 유지)
st.markdown("""
<style>
    #top-anchor { position: absolute; top: 0; left: 0; }
    .block-container { padding: 1rem 1.2rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 20px !important; }
    .sat { color: #0000FF !important; }
    .sun { color: #FF0000 !important; }
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
        flex: 1 !important; text-align: center !important; padding: 12px 0 !important;
        text-decoration: none !important; color: #1E3A5F !important; font-weight: bold !important; 
        border-right: 1px solid #F0F0F0 !important; font-size: 13px !important;
    }
    .nav-item:last-child { border-right: none !important; }
    .building-header { font-size: 18px !important; font-weight: bold; color: #2E5077; margin-top: 15px; border-bottom: 2px solid #2E5077; padding-bottom: 5px; margin-bottom: 12px; }
    .section-title { font-size: 15px; font-weight: bold; color: #555; margin: 10px 0 6px 0; padding-left: 5px; border-left: 4px solid #ccc; }
    .event-card { border: 1px solid #E0E0E0; border-left: 5px solid #2E5077; padding: 12px 14px; border-radius: 5px; margin-bottom: 12px !important; background-color: #ffffff; }
    .status-badge { display: inline-block; padding: 2px 8px; font-size: 11px; border-radius: 10px; font-weight: bold; float: right; }
    .status-y { background-color: #FFF4E5; color: #B25E09; } .status-n { background-color: #E8F0FE; color: #1967D2; }
    .bottom-info { font-size: 11px; color: #666; margin-top: 8px; border-top: 1px solid #f8f8f8; padding-top: 6px; display: flex; justify-content: space-between; align-items: flex-end; }
    .info-left { flex: 1; display: flex; flex-direction: column; gap: 2px; }
    .info-right { color: #888; margin-left: 10px; white-space: nowrap; }
    .link-btn {
        display: block; padding: 14px; margin-bottom: 8px; background: #F0F4F8; color: #1E3A5F !important;
        text-decoration: none; border-radius: 10px; font-weight: bold; text-align: center; border: 1px solid #D1D9E6; font-size: 15px;
    }
    .open-card { border: 2px dashed #2E5077; padding: 15px; border-radius: 10px; margin-bottom: 15px; background-color: #F8FAFF; }
    .open-bu-title { font-weight: 800; color: #2E5077; font-size: 19px !important; margin-bottom: 10px; border-bottom: 2px solid #D1D9E6; }
    .open-room-name { font-weight: bold; color: #333; font-size: 17px !important; margin-bottom: 3px; }
    .open-room-time { font-size: 16px !important; color: #FF4B4B; font-weight: bold; margin-bottom: 5px; }
    .open-room-note { font-size: 14px !important; color: #444; line-height: 1.4; background: #eee; padding: 5px 8px; border-radius: 4px; }
    .top-btn { position:fixed; bottom:80px; right:20px; z-index:999; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

# 3. 입력부
with st.form("search_form"):
    selected_date = st.date_input("날짜", value=st.session_state.target_date, label_visibility="collapsed")
    st.markdown('**🏢 건물 선택**')
    ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
    selected_bu_list = [b for b in ALL_BU if st.checkbox(b, value=(b in ["성의회관", "의생명산업연구원"]), key=f"f_{b}")]
    
    st.markdown('**🗓️ 대관 유형**')
    c1, c2 = st.columns(2)
    show_t = c1.checkbox("당일", value=True, key="chk_t")
    show_p = c2.checkbox("기간", value=True, key="chk_p")
    
    if st.form_submit_button("🔍 검색", use_container_width=True):
        st.session_state.target_date = selected_date
        st.session_state.search_performed = True
        st.query_params["d"] = selected_date.strftime("%Y-%m-%d")
        st.rerun()

# 4. 데이터 로직 (생략)
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
    is_weekend = d.isoweekday() in [6, 7]
    w_idx = d.weekday()
    w_str, w_class = ['월','화','수','목','금','토','일'][w_idx], ("sat" if w_idx == 5 else ("sun" if w_idx == 6 else ""))
    
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
        has_content = False
        if not df_raw.empty:
            bu_df = df_raw[df_raw['buNm'].str.replace(" ", "").str.contains(bu.replace(" ", ""), na=False)].copy()
            if not bu_df.empty:
                t_ev = bu_df[bu_df['startDt'] == bu_df['endDt']] if show_t else pd.DataFrame()
                p_ev = bu_df[bu_df['startDt'] != bu_df['endDt']] if show_p else pd.DataFrame()
                v_p_ev = p_ev[p_ev['allowDay'].apply(lambda x: target_wd in [day.strip() for day in str(x).split(",")])] if not p_ev.empty else pd.DataFrame()
                
                for ev_df, title in [(t_ev, "📌 당일 대관"), (v_p_ev, "🗓️ 기간 대관")]:
                    if not ev_df.empty:
                        has_content = True
                        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
                        for _, row in ev_df.sort_values(by='startTime').iterrows():
                            s_cls, s_txt = ("status-y", "예약확정") if row['status'] == 'Y' else ("status-n", "신청대기")
                            date_str = f"🗓️ {row['startDt']} ~ {row['endDt']} <span style='color:#2E5077; font-weight:bold;'>({get_weekday_names(row['allowDay'])})</span>" if title == "🗓️ 기간 대관" else f"🗓️ {row['startDt']}"
                            st.markdown(f"""
                            <div class="event-card">
                                <span class="status-badge {s_cls}">{s_txt}</span>
                                <div style="font-size:16px; font-weight:bold; color:#1E3A5F; margin-bottom:4px;">📍 {row['placeNm']}</div>
                                <div style="color:#FF4B4B; font-weight:bold; font-size:15px; margin:4px 0;">⏰ {row['startTime']} ~ {row['endTime']}</div>
                                <div style="font-size:14px; color:#333; font-weight:bold;">📄 {row['eventNm']}</div>
                                <div class="bottom-info">
                                    <div class="info-left"><span>{date_str}</span></div>
                                    <div class="info-right">👥 {row['mgDeptNm']}</div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
        if not has_content: st.markdown('<div style="color:#999; text-align:center; padding:15px; border:1px dashed #eee; font-size:13px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

    # 지침 (동일)
    st.markdown("<br><div class=\"building-header\">🔓 초회 순찰 개방 지침</div>", unsafe_allow_html=True)
    # ... 지침 HTML 생략 ...
    bg_status = "월~금: 오전 개방 / 오후 폐쇄" if not is_weekend else "주말: 대관 확인 후 개방"
    st.markdown(f"""<div class="open-card"><div class="open-bu-title">🏢 서울성모별관</div><div class="open-room-name">• 1201~1206호</div><div class="open-room-time">⏰ {bg_status}</div><div class="open-room-note">{"1206호(금) 10시 교육 예정" if d.isoweekday()==5 else "평일/주말 순찰 지침 준수"}</div></div>""", unsafe_allow_html=True)

# 6. 자주 찾는 홈페이지 (스크롤 고정용 앵커 설정)
# HTML 앵커를 익스팬더 바로 위에 배치
st.markdown('<div id="link-menu"></div>', unsafe_allow_html=True)

with st.expander("🔗 자주 찾는 홈페이지", expanded=False):
    # 익스팬더가 열리면 이 내부의 컴포넌트가 로드되면서 자바스크립트를 실행함
    st.markdown("""
        <div style="padding-top:10px;">
            <a href="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do" target="_blank" class="link-btn">🏫 성의교정 대관신청 현황</a>
            <a href="https://scube.s-tec.co.kr/sso/user/login/view" target="_blank" class="link-btn">🔐 S-CUBE 통합인증 (SSO)</a>
            <a href="https://pms.s-tec.co.kr/mainfrm.php" target="_blank" class="link-btn">📂 S-tec 개인정보관리</a>
            <a href="https://www.onsafe.co.kr/" target="_blank" class="link-btn">📖 온세이프 (법정교육)</a>
            <a href="https://todayshift.com/" target="_blank" class="link-btn">📅 오늘근무 (교대달력)</a>
        </div>
        
        <script>
            // 익스팬더가 열리는 시점에 부모 창의 위치를 #link-menu 앵커로 강제 이동
            var scrollTarget = window.parent.document.getElementById("link-menu");
            if (scrollTarget) {
                scrollTarget.scrollIntoView({behavior: "smooth", block: "start"});
            }
        </script>
    """, unsafe_allow_html=True)

# 7. TOP 버튼 및 결과창 자동 스크롤 (기존 로직 유지)
st.markdown("""<div class="top-btn"><a href="#top-anchor" style="display:block; background:#1E3A5F; color:white !important; width:45px; height:45px; line-height:45px; text-align:center; border-radius:50%; font-size:12px; font-weight:bold; text-decoration:none !important; box-shadow:2px 4px 8px rgba(0,0,0,0.3);">TOP</a></div>""", unsafe_allow_html=True)

components.html("""
    <script>
        // 결과 화면 로드 시 자동 스크롤
        setTimeout(function() {
            const res = window.parent.document.getElementById('result-anchor');
            if (res) res.scrollIntoView({behavior: 'smooth', block: 'start'});
        }, 500);
    </script>
""", height=0)


