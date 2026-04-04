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
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .row-1 { display: flex; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex: 1; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; }
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
            p_rng = f"{item['startDt']}~{item['endDt']}"
            d_nms = get_weekday_names(item.get('allowDay', ''))
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'), 'is_period': is_p, 'period_range': p_rng, 'allowed_days': d_nms,
                            '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', 
                            '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 추출 실패: {e}")
        return pd.DataFrame()

# --- 구글 시트 업데이트 함수 (누적 및 상세 정보 포함) ---
def update_google_sheet(df):
    if df.empty: return False
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        # 관리자님 구글 시트 ID
        SHEET_KEY = "13P49JFl63lgA7psgGr8QYgutKwcPMIyq0_jjUcc8Fa0"
        sh = client.open_by_key(SHEET_KEY)
        sheet = sh.get_worksheet(0)
        
        # 1. 헤더 설정 (기간대관 상세 정보 포함)
        header = ['날짜', '요일', '근무조', '유형', '대관기간', '해당요일', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태']
        
        # 2. 기존 시트 데이터 읽기 (누적 관리용)
        existing_data = sheet.get_all_values()
        if len(existing_data) > 1:
            existing_df = pd.DataFrame(existing_data[1:], columns=existing_data[0])
        else:
            existing_df = pd.DataFrame(columns=header)

        # 3. 신규 데이터 변환
        new_rows = []
        for _, r in df.iterrows():
            t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
            day_name = ["월", "화", "수", "목", "금", "토", "일"][t_dt.weekday()]
            new_rows.append({
                '날짜': r['full_date'], '요일': day_name, '근무조': get_shift(t_dt),
                '유형': "기간" if r['is_period'] else "당일",
                '대관기간': r['period_range'] if r['is_period'] else r['full_date'],
                '해당요일': r['allowed_days'] if r['is_period'] else day_name,
                '건물명': r['건물명'], '장소': r['장소'], '시간': r['시간'],
                '행사명': r['행사명'], '부서': r['부서'], '인원': r['인원'], '상태': r['상태']
            })
        new_df = pd.DataFrame(new_rows)

        # 4. 합치기 및 중복 제거 (날짜, 시간, 장소, 행사명 기준)
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(
            subset=['날짜', '시간', '장소', '행사명'], keep='last'
        )
        combined_df = combined_df.sort_values(by=['날짜', '시간'])

        # 5. 시트 쓰기 (Z1 에러 방지를 위해 L1 사용)
        final_values = [header] + combined_df.values.tolist()
        sheet.clear()
        sheet.update('A1', final_values)
        sheet.update('L1', [[datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')]])
        return True
    except Exception as e:
        st.error(f"구글 시트 전송 오류: {e}")
        return False

# --- 메인 실행 ---
st.markdown('<div class="main-title">🏫 성의교정 대관 관리 도구</div>', unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.expander("🔍 조회 및 수동 관리", expanded=True):
    c1, c2, c3 = st.columns([1.5, 2, 1.2])
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date + timedelta(days=7))
    with c2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    with c3:
        if st.button("🚀 시트 전송 (누적 업데이트)", use_container_width=True, type="primary"):
            df = get_data(s_date, e_date)
            if not df.empty and update_google_sheet(df):
                st.success("기존 데이터 보존 및 신규 데이터 누적 성공!")
            else:
                st.warning("전송할 데이터가 없거나 오류가 발생했습니다.")

# 데이터 표시 로직
df_view = get_data(s_date, e_date)
if not df_view.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df_view[df_view['full_date'] == d_str]
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
    st.info("선택한 기간에 데이터가 없습니다.")
