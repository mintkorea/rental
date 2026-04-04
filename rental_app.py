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
    .date-bar:first-of-type { margin-top: 0px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .row-1 { display: flex; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex: 1; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; background-color: #2ecc71; }
    .row-2 { font-size: 12px; color: #333; border-top: 1px solid #f8f9fa; padding-top: 6px; margin-top: 4px; }
    .period-tag { font-size: 11px; color: #2E5077; background: #f0f4f8; padding: 4px 8px; border-radius: 4px; margin-top: 5px; display: inline-block; border: 1px solid #d1d9e6; }
    .section-label { font-size: 12px; font-weight: bold; color: #666; margin: 10px 0 5px 5px; display: flex; align-items: center; }
    .section-label::before { content: ""; width: 3px; height: 12px; background: #adb5bd; margin-right: 6px; border-radius: 2px; }
    </style>
""", unsafe_allow_html=True)

# --- [핵심] 구글 시트 업데이트 함수 ---
def update_google_sheet(df):
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        # GitHub 리포지토리에 credentials.json이 함께 있어야 합니다.
        creds = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(creds)
        
        # 관리자님의 구글 시트 ID (URL에서 확인 가능)
        SHEET_KEY = "1vTi4T20_JgmIH8e5kIsaokmfTT0Fz7Ua2MS4YnBPmHoCIqtB0F7WpY00fXDbOifOu7WZEjXJm9iWCUT"
        sh = client.open_by_key(SHEET_KEY)
        sheet = sh.get_worksheet(0)
        
        header = ['날짜', '요일', '근무조', '유형', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태']
        values = [header]
        
        # 날짜순, 시간순 정렬하여 데이터 구성
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
        # 업데이트 날짜 기록 (Z1 셀 활용)
        sheet.update('Z1', [[datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')]])
        return True
    except Exception as e:
        st.error(f"구글 시트 전송 중 오류 발생: {e}")
        return False

# --- 공통 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

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
        if not final_df.empty:
            final_df = final_df.drop_duplicates() # 중복 제거
        return final_df
    except: return pd.DataFrame()

# --- [중요] API 모드 감지 로직 (최상단 실행) ---
params = st.query_params
if params.get("task") == "update":
    st.info("🔄 API 자동 업데이트 모드로 실행 중...")
    # 오늘부터 향후 7일간의 데이터를 긁어와서 업데이트
    auto_df = get_data(now_today, now_today + timedelta(days=7))
    if not auto_df.empty:
        if update_google_sheet(auto_df):
            st.success("✅ 구글 시트 업데이트가 완료되었습니다.")
            st.balloons()
        else:
            st.error("❌ 업데이트 실패")
    else:
        st.warning("⚠️ 추출할 데이터가 없습니다.")
    st.stop() # API 모드일 경우 하단 UI는 렌더링하지 않음

# --- 엑셀 생성 함수 ---
def create_excel(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('성의교정대관현황')
        t_fmt = workbook.add_format({'bold': True, 'size': 16, 'align': 'center', 'valign': 'vcenter'})
        d_fmt = workbook.add_format({'bold': True, 'bg_color': '#3d444b', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        b_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        c_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})

        widths = [20, 15, 45, 20, 10, 10]
        for i, w in enumerate(widths): worksheet.set_column(i, i, w)
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", t_fmt)
        worksheet.set_row(0, 40)
        
        row = 2
        for d_str in sorted(df['full_date'].unique()):
            worksheet.set_row(row, 25); worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", d_fmt); row += 1
            for bu in BUILDING_ORDER:
                if bu not in selected_bu: continue
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                if b_df.empty: continue
                worksheet.set_row(row, 25); worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", b_fmt); row += 1
                worksheet.set_row(row, 25)
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                for _, r in b_df.sort_values(['is_period', '시간']).iterrows():
                    worksheet.set_row(row, 35)
                    ev_nm = f"{r['행사명']}\n({r['period_range']} / {r['allowed_days']})" if r['is_period'] else r['행사명']
                    worksheet.write_row(row, 0, [r['장소'], r['시간'], ev_nm, r['부서'], r['인원'], r['상태']], c_fmt)
                    row += 1
                row += 1
    return output.getvalue()

# --- 화면 구성 ---
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

st.markdown('<div class="main-title">🏫 성의교정 대관 현황 관리자</div>', unsafe_allow_html=True)

with st.expander("🔍 조회 및 데이터 관리", expanded=True):
    c1, c2, c3 = st.columns([1.5, 2, 1.2])
    with c1:
        s_date = st.date_input("조회 시작일", value=now_today)
        e_date = st.date_input("조회 종료일", value=s_date)
    with c2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    with c3:
        view_mode = st.radio("보기 유형", ["세로 카드", "가로 표"], horizontal=True)
        df = get_data(s_date, e_date)
        if not df.empty:
            sc1, sc2 = st.columns(2)
            file_dt = f"{s_date}_{e_date}" if s_date != e_date else f"{s_date}"
            sc1.download_button("📊 Excel", create_excel(df, sel_bu), f"대관현황_{file_dt}.xlsx", use_container_width=True)
            if st.button("🚀 구글 시트 전송", use_container_width=True, type="primary"):
                if update_google_sheet(df): st.success("✅ 전송 성공!")

# --- 데이터 표시부 ---
if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        if not day_df.empty:
            st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
            for bu in sel_bu:
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if b_df.empty: continue
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                if view_mode == "가로 표":
                    display_df = b_df.copy().sort_values('시간')
                    display_df['행사명'] = display_df.apply(lambda r: f"{r['행사명']}\n({r['period_range']} / {r['allowed_days']})" if r['is_period'] else r['행사명'], axis=1)
                    st.dataframe(display_df[['장소', '시간', '행사명', '부서', '인원', '상태']], hide_index=True, use_container_width=True)
                else:
                    d_ev = b_df[~b_df['is_period']].sort_values('시간')
                    p_ev = b_df[b_df['is_period']].sort_values('시간')
                    for evs, label, color in [(d_ev, "📌 당일 대관", "#2ecc71"), (p_ev, "🗓️ 기간 대관", "#2196F3")]:
                        if not evs.empty:
                            st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)
                            for _, r in evs.iterrows():
                                st.markdown(f'''
                                    <div class="mobile-card" style="border-left:5px solid {color};">
                                        <div class="row-1">
                                            <span class="loc-text">📍 {r["장소"]}</span>
                                            <span class="time-text">🕒 {r["시간"]}</span>
                                            <span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span>
                                        </div>
                                        <div class="row-2"><b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                                        {f'<div class="period-tag">🗓️ {r["period_range"]} ({r["allowed_days"]})</div>' if r["is_period"] else ""}
                                    </div>''', unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("조회된 데이터가 없습니다.")
