import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import csv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 대관 관리 시스템", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 디자인 CSS
st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main .block-container { max-width: 1200px; margin: 0 auto; padding: 0.5rem 1rem !important; }
    .main-title { font-size: 24px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 30px; margin-bottom: 12px; font-size: 16px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 15px 0 8px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 6px 10px; }
    
    /* 테이블 스타일 */
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; table-layout: fixed; background: white; }
    .custom-table th { background: #f8f9fa; border: 1px solid #dee2e6; padding: 10px 5px; text-align: center; color: #495057; }
    .custom-table td { border: 1px solid #dee2e6; padding: 10px 8px; text-align: center; vertical-align: middle; }
    .event-cell { text-align: left !important; font-weight: 500; }
    
    /* 카드 스타일 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 8px; padding: 12px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .time-text { color: #e74c3c; font-weight: bold; font-size: 14px; }
    .period-tag { font-size: 11px; color: #2196F3; margin-top: 4px; display: block; }
    </style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    base_date = date(2026, 3, 13) # 기준일
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# --- 구글 시트 자동화 로직 (운영용 시트 직접 누적) ---
def update_google_sheet(df):
    if df.empty: return False
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # Secrets 환경설정 사용
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        # 시트 열기
        SHEET_KEY = "13P49JFl63lgA7psgGr8QYgutKwcPMIyq0_jjUcc8Fa0"
        sh = client.open_by_key(SHEET_KEY)
        sheet = sh.worksheet("운영용") 

        # 1. 기존 데이터 읽기 (중복 체크용)
        existing_data = sheet.get_all_values()
        if len(existing_data) > 1:
            existing_df = pd.DataFrame(existing_data[1:], columns=existing_data[0])
            # 중복 판단 기준: 날짜 + 장소 + 시간 + 행사명
            existing_df['unique_key'] = existing_df['날짜'] + existing_df['장소'] + existing_df['시간'] + existing_df['행사명']
            existing_keys = set(existing_df['unique_key'].tolist())
        else:
            existing_keys = set()
            # 헤더가 없으면 생성
            header = ['날짜', '요일', '근무조', '유형', '대관기간', '해당요일', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태']
            sheet.append_row(header)

        # 2. 신규 데이터 중복 제외 필터링
        new_rows = []
        for _, r in df.iterrows():
            t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
            current_key = r['full_date'] + r['장소'] + r['시간'] + r['행사명']
            
            if current_key not in existing_keys:
                row = [
                    r['full_date'], "월화수목금토일"[t_dt.weekday()], get_shift(t_dt),
                    "기간" if r['is_period'] else "당일", r['period_range'],
                    r['allowed_days'] if r['is_period'] else "월화수목금토일"[t_dt.weekday()],
                    r['건물명'], r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']
                ]
                new_rows.append(row)

        # 3. 신규 건만 시트 하단에 추가
        if new_rows:
            sheet.append_rows(new_rows)
            st.success(f"✅ 새롭게 예약된 {len(new_rows)}건을 운영용 시트에 추가했습니다!")
        else:
            st.info("ℹ️ 이미 모든 데이터가 시트에 반영되어 있습니다.")

        # 4. 최종 동기화 시간 기록 (R1 셀)
        sync_time = datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')
        sheet.update('R1', [[f"최종 동기화: {sync_time}"]])
        return True
    except Exception as e:
        st.error(f"시트 연동 오류: {e}")
        return False

# --- 데이터 크롤링 ---
@st.cache_data(ttl=300)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
                            'full_date': curr.strftime('%Y-%m-%d'), 
                            'is_period': is_p, 'period_range': p_rng, 'allowed_days': d_nms,
                            '건물명': str(item.get('buNm', '')).strip(), 
                            '장소': item.get('placeNm', '') or '-', 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-', 
                            '부서': item.get('mgDeptNm', '') or '-', 
                            '인원': str(item.get('peopleCount', '0')), 
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame()
    except: return pd.DataFrame()

# --- 메인 화면 ---
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 자동화 시스템</div>', unsafe_allow_html=True)

with st.expander("⚙️ 데이터 동기화 및 조회 설정", expanded=True):
    c1, c2, c3 = st.columns([1.5, 2, 1.2])
    with c1:
        s_date = st.date_input("조회 시작", value=now_today)
        e_date = st.date_input("조회 종료", value=s_date + timedelta(days=7))
    with c2:
        bu_list = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
        sel_bu = st.multiselect("건물 선택", options=bu_list, default=bu_list[:3])
    with c3:
        view_mode = st.radio("보기 모드", ["표 형식", "카드 형식"], horizontal=True)
        df = get_data(s_date, e_date)
        if not df.empty:
            if st.button("🚀 구글 시트 즉시 동기화", use_container_width=True, type="primary"):
                update_google_sheet(df)

# 화면 출력 로직
if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        if not day_df.empty:
            st.markdown(f'<div class="date-bar">📅 {d_str} ({"월화수목금토일"[curr.weekday()]}) | {get_shift(curr)}</div>', unsafe_allow_html=True)
            for bu in sel_bu:
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if b_df.empty: continue
                st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                if view_mode == "표 형식":
                    table_html = '<table class="custom-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>상태</th></tr></thead><tbody>'
                    for _, r in b_df.sort_values('시간').iterrows():
                        table_html += f"<tr><td>{r['장소']}</td><td class='time-text'>{r['시간']}</td><td class='event-cell'>{r['행사명']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
                else:
                    for _, r in b_df.sort_values('시간').iterrows():
                        st.markdown(f'''<div class="mobile-card">
                            <span class="time-text">🕒 {r['시간']}</span> | <b>{r['장소']}</b><br/>
                            <div style="margin-top:5px;"><b>{r['행사명']}</b> ({r['부서']})</div>
                            {f'<span class="period-tag">🗓️ {r["period_range"]}</span>' if r["is_period"] else ""}
                        </div>''', unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("선택한 기간에 대관 데이터가 없습니다.")
