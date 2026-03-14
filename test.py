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

# 2. 세션 상태 초기화 (에러 방지 핵심)
if 'target_date' not in st.session_state:
    url_d = st.query_params.get("d")
    if url_d:
        try: st.session_state.target_date = datetime.strptime(url_d, "%Y-%m-%d").date()
        except: st.session_state.target_date = today_kst()
    else: st.session_state.target_date = today_kst()

if 'search_performed' not in st.session_state:
    st.session_state.search_performed = True if st.query_params.get("d") else False

# 요일/근무조 로직
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_work_shift(d):
    anchor = date(2026, 3, 13)
    diff = (d - anchor).days
    shifts = [{"n": "A조", "bg": "#FF9800"}, {"n": "B조", "bg": "#E91E63"}, {"n": "C조", "bg": "#2196F3"}]
    return shifts[diff % 3]

# 3. CSS 스타일 (간결함 유지)
st.markdown("""
<style>
    #top-anchor { position: absolute; top: 0; left: 0; }
    .block-container { padding: 0.5rem 0.8rem !important; max-width: 500px !important; }
    header { visibility: hidden; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 10px !important; }
    .stCheckbox { margin: -15px 0 !important; transform: scale(0.9); }
    .sat { color: #0000FF !important; } .sun { color: #FF0000 !important; }
    .date-display-box { 
        text-align: center; background-color: #F8FAFF; padding: 8px 5px 5px 5px; 
        border-radius: 8px 8px 0 0; border: 1px solid #D1D9E6; border-bottom: none; line-height: 1.1 !important;
    }
    .res-sub-title { font-size: 15px !important; font-weight: 700; color: #333; }
    .nav-link-bar {
        display: flex !important; width: 100% !important; background: white !important; 
        border: 1px solid #D1D9E6 !important; border-radius: 0 0 8px 8px !important; 
        margin-bottom: 15px !important; overflow: hidden !important;
    }
    .nav-item {
        flex: 1 !important; text-align: center !important; padding: 6px 0 !important;
        text-decoration: none !important; color: #1E3A5F !important; font-weight: bold !important; 
        border-right: 1px solid #F0F0F0 !important; font-size: 12px !important;
    }
    .building-header { font-size: 16px !important; font-weight: bold; color: #2E5077; margin-top: 10px; border-bottom: 1px solid #2E5077; padding-bottom: 2px; margin-bottom: 8px; }
    .section-title { font-size: 13px; font-weight: bold; color: #555; margin: 5px 0 3px 0; padding-left: 5px; border-left: 3px solid #ccc; }
    .event-card { border: 1px solid #E0E0E0; border-left: 4px solid #2E5077; padding: 8px 10px; border-radius: 4px; margin-bottom: 6px !important; background-color: #ffffff; line-height: 1.2 !important; }
    .status-badge { display: inline-block; padding: 1px 5px; font-size: 10px; border-radius: 4px; font-weight: bold; float: right; }
    .bottom-info { font-size: 11px; color: #666; margin-top: 4px; display: flex; justify-content: space-between; border-top: 1px solid #f9f9f9; padding-top: 3px; }
    .open-card { border: 1px dashed #2E5077; padding: 10px; border-radius: 8px; margin-bottom: 10px; background-color: #F8FAFF; line-height: 1.2; }
    .open-bu-title { font-weight: 800; color: #2E5077; font-size: 15px !important; margin-bottom: 5px; border-bottom: 1px solid #D1D9E6; }
    .open-room-name { font-weight: bold; color: #333; font-size: 14px !important; }
    .open-room-time { font-size: 13px !important; color: #FF4B4B; font-weight: bold; }
    .open-room-note { font-size: 12px !important; color: #555; background: #eee; padding: 2px 5px; border-radius: 3px; }
    .link-btn {
        display: block; padding: 8px; margin-bottom: 4px; background: #F0F4F8; color: #1E3A5F !important;
        text-decoration: none; border-radius: 6px; font-weight: bold; text-align: center; border: 1px solid #D1D9E6; font-size: 13px;
    }
    .spacer { height: 60px; }
    .top-btn { position:fixed; bottom:20px; right:15px; z-index:999; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# 4. 입력부
with st.form("search_form"):
    selected_date = st.date_input("날짜", value=st.session_state.target_date, label_visibility="collapsed")
    col_a, col_b = st.columns(2)
    ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
    selected_bu_list = []
    for i, bu in enumerate(ALL_BU):
        with (col_a if i % 2 == 0 else col_b):
            if st.checkbox(bu, value=(bu in ["성의회관", "의생명산업연구원"]), key=f"f_{bu}"):
                selected_bu_list.append(bu)
    show_t = col_a.checkbox("당일", value=True, key="chk_t")
    show_p = col_b.checkbox("기간", value=True, key="chk_p")
    
    if st.form_submit_button("🔍 검색", use_container_width=True):
        st.session_state.target_date = selected_date
        st.session_state.search_performed = True
        st.query_params["d"] = selected_date.strftime("%Y-%m-%d")
        st.rerun()

# 데이터 로드 로직 (동일)
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
        <span class="res-sub-title">{d.strftime("%y.%m.%d")}.<span class="{w_class}">({w_str})</span>
        <span style="background:{shift['bg']}; color:white; padding:1px 6px; border-radius:10px; font-size:12px;">{shift['n']}</span></span>
    </div>
    <div class="nav-link-bar">
        <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-item">◀ Prev</a>
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
                
                for ev_df, title in [(t_ev, "📌 당일"), (v_p_ev, "🗓️ 기간")]:
                    if not ev_df.empty:
                        has_content = True
                        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
                        for _, row in ev_df.sort_values(by='startTime').iterrows():
                            s_cls, s_txt = (("status-y", "확정") if row['status'] == 'Y' else ("status-n", "대기"))
                            st.markdown(f"""
                            <div class="event-card">
                                <span class="status-badge {s_cls}">{s_txt}</span>
                                <div style="font-size:14px; font-weight:bold; color:#1E3A5F;">📍 {row['placeNm']}</div>
                                <div style="color:#FF4B4B; font-weight:bold; font-size:13px;">⏰ {row['startTime']}~{row['endTime']}</div>
                                <div style="font-size:13px; color:#333;">📄 {row['eventNm']}</div>
                                <div class="bottom-info"><span>👤 {row['mgDeptNm']}</span></div>
                            </div>
                            """, unsafe_allow_html=True)
        if not has_content: st.markdown('<div style="color:#999; text-align:center; padding:5px; font-size:11px;">내역 없음</div>', unsafe_allow_html=True)

    # 6. 개방 지침
    st.markdown("<div class=\"building-header\">🔓 개방 지침</div>", unsafe_allow_html=True)
    sh_list = []
    if not is_weekend:
        sh_list.append({"r": "421~522호", "t": "주중 오전개방", "n": "퇴실독촉 금지"})
        if date(2026, 3, 2) <= d <= date(2026, 4, 30):
            sh_list.append({"r": "402~407호", "t": "08:00~20:00", "n": "첫/끝순찰 개폐"})
    if date(2026, 2, 7) <= d <= date(2026, 4, 24):
        sh_list.append({"r": "801호", "t": "09:00~21:00", "n": "평일:직원개방/야간폐쇄"})
    
    if sh_list:
        sh_html = "".join([f'<div style="margin-bottom:5px;"><span class="open-room-name">• {i["r"]}</span> <span class="open-room-time">({i["t"]})</span> <span class="open-room-note">{i["n"]}</span></div>' for i in sh_list])
        st.markdown(f'<div class="open-card"><div class="open-bu-title">🏢 성의회관</div>{sh_html}</div>', unsafe_allow_html=True)
    
    st.markdown(f"""<div class="open-card"><div class="open-bu-title">🏢 서울성모별관</div><span class="open-room-name">• 1201~1206호</span> <span class="open-room-time">({"주중개방" if not is_weekend else "주말대관확인"})</span></div>""", unsafe_allow_html=True)

    components.html("""<script>setTimeout(function() {window.parent.document.getElementById('result-anchor').scrollIntoView({behavior: 'smooth', block: 'start'});}, 300);</script>""", height=0)

# 7. 빠른 링크
with st.expander("🔗 빠른 링크", expanded=False):
    links = [("🏫 대관신청", "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"), ("🔐 S-CUBE", "https://scube.s-tec.co.kr/sso/user/login/view"), ("📂 개인정보", "https://pms.s-tec.co.kr/mainfrm.php"), ("📅 오늘근무", "https://todayshift.com/"), ("👮 경비교육", "https://www.ksst.or.kr/")]
    for name, url in links:
        st.markdown(f'<a href="{url}" target="_blank" class="link-btn">{name}</a>', unsafe_allow_html=True)

st.markdown('<div class="spacer"></div>', unsafe_allow_html=True)
st.markdown("""<div class="top-btn"><a href="#top-anchor" style="display:block; background:#1E3A5F; color:white !important; width:40px; height:40px; line-height:40px; text-align:center; border-radius:50%; font-size:11px; font-weight:bold; text-decoration:none !important; box-shadow:2px 2px 5px rgba(0,0,0,0.2);">TOP</a></div>""", unsafe_allow_html=True)
