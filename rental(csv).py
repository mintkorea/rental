import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import csv
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
    
    /* 테이블 디자인 */
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; table-layout: fixed; background: white; }
    .custom-table th { background: #f8f9fa; border: 1px solid #dee2e6; padding: 10px 5px; text-align: center; color: #495057; font-weight: bold; }
    .custom-table td { border: 1px solid #dee2e6; padding: 10px 8px; text-align: center; vertical-align: middle; line-height: 1.4; }
    .event-cell { text-align: left !important; }
    .period-info { font-size: 11px; color: #2196F3; display: block; margin-top: 3px; font-weight: normal; }
    
    /* 모바일 카드 스타일 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .row-1 { display: flex; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex: 1; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; background-color: #2ecc71; }
    .row-2 { font-size: 12px; color: #333; border-top: 1px solid #f8f9fa; padding-top: 6px; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# --- 공통 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# --- 2. 구글 시트 연동 (스크린샷 A~M열 양식 준수) ---
def update_google_sheet(df):
    if df.empty: return False
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # credentials.json 파일이 같은 경로에 있어야 함
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        SHEET_KEY = "1vTi4T20_JgmIH8e5kIsaokmfTT0Fz7Ua2MS4YnBPmHoCIqtB0F7WpY00fXDbOifOu7WZEjXJm9iWCUT"
        sh = client.open_by_key(SHEET_KEY)
        sheet = sh.get_worksheet(0)
        
        # 스크린샷과 동일한 헤더 구성
        header = ['날짜', '요일', '근무조', '유형', '대관기간', '해당요일', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태']
        values = [header]
        
        for _, r in df.sort_values(['full_date', '시간']).iterrows():
            t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
            row = [
                r['full_date'],                         # A: 날짜
                "월화수목금토일"[t_dt.weekday()],       # B: 요일
                get_shift(t_dt),                        # C: 근무조
                "기간" if r['is_period'] else "당일",   # D: 유형
                r['period_range'],                      # E: 대관기간
                r['allowed_days'] if r['is_period'] else "월화수목금토일"[t_dt.weekday()], # F: 해당요일
                r['건물명'],                            # G: 건물명
                r['장소'],                              # H: 장소
                r['시간'],                              # I: 시간
                r['행사명'],                            # J: 행사명
                r['부서'],                              # K: 부서
                r['인원'],                              # L: 인원
                r['상태']                               # M: 상태
            ]
            values.append(row)
            
        sheet.clear()
        sheet.update('A1', values)
        sheet.update('O1', [[f"Last Sync: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"]])
        return True
    except Exception as e:
        st.error(f"시트 연동 오류: {e}")
        return False

# --- 3. 데이터 로직 ---
@st.cache_data(ttl=60)
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
                            'is_period': is_p, 
                            'period_range': p_rng, 
                            'allowed_days': d_nms,
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

# --- 4. CSV/Excel 파일 생성 ---
def create_excel(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('현황')
        t_fmt = workbook.add_format({'bold': True, 'size': 14, 'align': 'center'})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#f2f2f2', 'border': 1, 'align': 'center'})
        c_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", t_fmt)
        row = 2
        for d_str in sorted(df['full_date'].unique()):
            day_df = df[df['full_date'] == d_str]
            worksheet.write(row, 0, f"📅 {d_str}", h_fmt); row += 1
            for bu in BUILDING_ORDER:
                if bu not in selected_bu: continue
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if b_df.empty: continue
                worksheet.write(row, 0, f"🏢 {bu}", workbook.add_format({'bold':True})); row += 1
                cols = ['장소', '시간', '행사명', '부서', '인원', '상태']
                for i, c in enumerate(cols): worksheet.write(row, i, c, h_fmt)
                row += 1
                for _, r in b_df.sort_values('시간').iterrows():
                    worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt)
                    row += 1
                row += 1
    return output.getvalue()

def create_csv(df):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    # 스크린샷 양식 헤더
    writer.writerow(['날짜', '요일', '근무조', '유형', '대관기간', '해당요일', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태'])
    for _, r in df.sort_values(['full_date', '시간']).iterrows():
        t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
        writer.writerow([
            r['full_date'], "월화수목금토일"[t_dt.weekday()], get_shift(t_dt),
            "기간" if r['is_period'] else "당일", r['period_range'],
            r['allowed_days'] if r['is_period'] else "월화수목금토일"[t_dt.weekday()],
            r['건물명'], r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']
        ])
    return output.getvalue().encode('utf-8-sig')

# --- 5. 메인 화면 구성 ---
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

st.markdown('<div class="main-title">🏫 성의교정 대관 관리자</div>', unsafe_allow_html=True)

with st.expander("🔍 데이터 관리 및 조회", expanded=True):
    c1, c2, c3 = st.columns([1.5, 2, 1.2])
    with c1:
        s_date = st.date_input("조회 시작일", value=now_today)
        e_date = st.date_input("조회 종료일", value=s_date + timedelta(days=7))
    with c2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    with c3:
        view_mode = st.radio("보기 유형", ["세로 카드", "가로 표"], horizontal=True)
        df = get_data(s_date, e_date)
        if not df.empty:
            if st.button("🚀 구글 시트 동기화", use_container_width=True, type="primary"):
                if update_google_sheet(df): st.success("✅ 동기화 완료!")
            st.download_button("📄 CSV 다운로드", create_csv(df), f"대관현황_{s_date}.csv", use_container_width=True)

# 데이터 출력 부분
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
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                if view_mode == "가로 표":
                    table_html = '<table class="custom-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>인원</th><th>상태</th></tr></thead><tbody>'
                    for _, r in b_df.sort_values('시간').iterrows():
                        p_info = f'<span class="period-info">🗓️ {r["period_range"]} ({r["allowed_days"]})</span>' if r["is_period"] else ""
                        table_html += f"<tr><td>{r['장소']}</td><td style='color:#e74c3c; font-weight:bold;'>{r['시간']}</td><td class='event-cell'><b>{r['행사명']}</b>{p_info}</td><td>{r['부서']}</td><td>{r['인원']}명</td><td>{r['상태']}</td></tr>"
                    st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
                else:
                    for _, r in b_df.sort_values('시간').iterrows():
                        color = "#2196F3" if r["is_period"] else "#2ecc71"
                        st.markdown(f'''
                            <div class="mobile-card" style="border-left:5px solid {color};">
                                <div class="row-1"><span class="loc-text">📍 {r["장소"]}</span><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge">{r["상태"]}</span></div>
                                <div class="row-2"><b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                                {f'<div style="font-size:11px; color:#2196F3; margin-top:5px;">🗓️ {r["period_range"]} ({r["allowed_days"]})</div>' if r["is_period"] else ""}
                            </div>''', unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("조회된 데이터가 없습니다.")
