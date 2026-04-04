import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 설정 및 디자인 CSS
st.set_page_config(page_title="성의교정 대관 관리 시스템", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main .block-container { max-width: 1200px; margin: 0 auto; padding: 0.5rem 1rem !important; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; font-size: 15px; }
    .date-bar:first-of-type { margin-top: 0px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .row-1 { display: flex; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex: 1; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; background-color: #2ecc71; }
    .row-2 { font-size: 12px; color: #333; border-top: 1px solid #f8f9fa; padding-top: 6px; margin-top: 4px; }
    .period-tag { font-size: 11px; color: #2E5077; background: #f0f4f8; padding: 4px 8px; border-radius: 4px; margin-top: 5px; display: inline-block; border: 1px solid #d1d9e6; }
    </style>
""", unsafe_allow_html=True)

# --- 공통 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    # 관리자님의 C-조 로직 반영
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            is_p = (item['startDt'] != item['endDt'])
            p_rng, d_nms = f"{item['startDt']}~{item['endDt']}", get_weekday_names(item.get('allowDay', ''))
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'), 'is_period': is_p, 'period_range': p_rng, 'allowed_days': d_nms,
                            '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        final_df = pd.DataFrame(rows)
        return final_df.drop_duplicates() if not final_df.empty else pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 추출 실패: {e}")
        return pd.DataFrame()

# --- 구글 시트 업데이트 함수 (들여쓰기 오류 수정 완료) ---
def update_google_sheet(df):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        
        # [중요] credentials.json 대신 Streamlit Secrets를 사용합니다.
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        # 관리자님 구글 시트 ID
        SHEET_KEY = "1vTi4T20_JgmIH8e5kIsaokmfTT0Fz7Ua2MS4YnBPmHoCIqtB0F7WpY00fXDbOifOu7WZEjXJm9iWCUT"
        sh = client.open_by_key(SHEET_KEY)
        sheet = sh.get_worksheet(0)
        
        header = ['날짜', '요일', '근무조', '유형', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태']
        values = [header]
        
        for _, r in df.sort_values(['full_date', '시간']).iterrows():
            t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
            day_name = ["월", "화", "수", "목", "금", "토", "일"][t_dt.weekday()]
            values.append([
                r['full_date'], day_name, get_shift(t_dt), 
                "기간" if r['is_period'] else "당일",
                r['건물명'], r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']
            ])
            
        sheet.clear()
        sheet.update('A1', values)
        sheet.update('Z1', [[datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')]])
        return True
    except Exception as e:
        st.error(f"구글 시트 전송 오류: {e}")
        return False

# --- 자동 업데이트 체크 (접속 시 7일 경과 확인) ---
def check_and_run_weekly():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        sh = client.open_by_key("1vTi4T20_JgmIH8e5kIsaokmfTT0Fz7Ua2MS4YnBPmHoCIqtB0F7WpY00fXDbOifOu7WZEjXJm9iWCUT")
        sheet = sh.get_worksheet(0)
        last_str = sheet.acell('Z1').value
        
        if last_str:
            last_date = datetime.strptime(last_str.split(' ')[0], '%Y-%m-%d').date()
            # 7일(1주일)마다 자동으로 30일(1개월)치 데이터를 동기화
            if (date.today() - last_date).days >= 7:
                update_google_sheet(get_data(now_today, now_today + timedelta(days=30)))
    except:
        pass

# --- 메인 실행 로직 ---
params = st.query_params
if params.get("task") == "update":
    st.info("🔄 API 모드: 향후 1개월 데이터를 갱신합니다...")
    auto_df = get_data(now_today, now_today + timedelta(days=30))
    if not auto_df.empty and update_google_sheet(auto_df):
        st.success("✅ 업데이트 완료!")
        st.balloons()
    st.stop()

# 화면 상단 타이틀
st.markdown('<div class="main-title">🏫 성의교정 대관 관리 도구</div>', unsafe_allow_html=True)

# 7일 주기 자동 업데이트 체크 실행
check_and_run_weekly()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.expander("🔍 조회 및 수동 관리", expanded=True):
    c1, c2, c3 = st.columns([1.5, 2, 1.2])
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with c2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    with c3:
        view_mode = st.radio("보기 유형", ["세로 카드", "가로 표"], horizontal=True)
        df = get_data(s_date, e_date)
        if not df.empty and st.button("🚀 시트 전송", use_container_width=True, type="primary"):
            if update_google_sheet(df): st.success("갱신 성공!")

# 데이터 표시
if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        if not day_df.empty:
            st.markdown(f'<div class="date-bar">📅 {d_str} ({"월화수목금토일"[curr.weekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
            for bu in sel_bu:
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if b_df.empty: continue
                st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'''
                        <div class="mobile-card" style="border-left:5px solid {"#2196F3" if r["is_period"] else "#2ecc71"};">
                            <div class="row-1"><span class="loc-text">📍 {r["장소"]}</span><span class="time-text">🕒 {r["시간"]}</span></div>
                            <div class="row-2"><b>{r["행사명"]}</b> / {r["부서"]}</div>
                            {f'<div class="period-tag">🗓️ {r["period_range"]} ({r["allowed_days"]})</div>' if r["is_period"] else ""}
                        </div>''', unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("데이터가 없습니다.")
