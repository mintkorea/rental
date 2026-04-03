import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인 (A형 카드 스타일 유지)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding: 5px 10px; background: #f1f4f9; }
    
    /* A형 카드 스타일 */
    .mobile-card { background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .row-1 { display: flex; align-items: center; justify-content: space-between; }
    .loc-text { font-size: 15px; font-weight: bold; color: #1E3A5F; }
    .time-text { font-size: 14px; font-weight: bold; color: #d9534f; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; background: #2ecc71; }
    .row-2 { font-size: 13px; color: #333; margin-top: 6px; padding-top: 6px; border-top: 1px solid #f8f9fa; }
    
    .section-label { font-size: 13px; font-weight: bold; color: #555; margin: 10px 0 5px 5px; }
    .period-tag { font-size: 11px; color: #2E5077; background: #f0f4f8; padding: 4px 8px; border-radius: 4px; margin-top: 5px; display: inline-block; border: 1px solid #d1d9e6; }
    </style>
""", unsafe_allow_html=True)

# --- 공통 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    anchor = date(2026, 3, 13)
    diff = (target_date - anchor).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# --- [원본 서식 유지 + 행사명 기간 추가] 엑셀 생성 함수 ---
def create_styled_excel(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황보고')
        
        # 엑셀 서식 설정
        title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center', 'font_color': '#1E3A5F'})
        date_fmt = workbook.add_format({'bold': True, 'bg_color': '#343A40', 'font_color': 'white', 'border': 1})
        head_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10, 'text_wrap': True})

        # 컬럼 너비 설정
        worksheet.set_column('A:A', 15) # 장소
        worksheet.set_column('B:B', 15) # 시간
        worksheet.set_column('C:C', 45) # 행사명 (정보 추가 대비 넓게 설정)
        worksheet.set_column('D:D', 20) # 부서
        worksheet.set_column('E:E', 10) # 상태

        row = 0
        worksheet.merge_range('A1:E1', "🏫 성의교정 시설 대관 현황 보고서", title_fmt)
        row = 2

        for d_str in sorted(df['날짜'].unique()):
            day_df = df[df['날짜'] == d_str]
            worksheet.write(row, 0, f"📅 {d_str} ({get_shift(datetime.strptime(d_str, '%Y-%m-%d').date())})", date_fmt)
            row += 1
            
            for bu in selected_bu:
                b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if not b_df.empty:
                    worksheet.write(row, 0, f"🏢 {bu}", head_fmt)
                    worksheet.write_row(row, 1, ["시간", "행사명", "부서", "상태"], head_fmt)
                    row += 1
                    for _, r in b_df.sort_values(['구분', '시간'], ascending=[False, True]).iterrows():
                        # [핵심] 기간 대관인 경우 행사명 셀에 기간 정보 추가
                        event_display = r['행사명']
                        if r['구분'] == '기간':
                            event_display = f"{r['행사명']}\n(기간: {r['상세기간']} / {r['요일']})"
                        
                        worksheet.write_row(row, 0, [r['장소'], r['시간'], event_display, r['부서'], r['상태']], cell_fmt)
                        row += 1
            row += 1 # 날짜간 간격
            
    return output.getvalue()

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
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'), '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-', '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            '구분': '기간' if is_p else '당일', '상세기간': f"{item['startDt']}~{item['endDt']}",
                            '요일': get_weekday_names(item.get('allowDay', ''))
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# --- 메인 화면 ---
st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

with st.expander("🔍 조회 및 다운로드 설정", expanded=True):
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with col2:
        sel_bu = st.multiselect("건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크"], default=["성의회관", "의생명산업연구원"])
    with col3:
        view_mode = st.radio("보기 유형", ["세로 카드(A형)", "가로 표"], horizontal=True)
        df = get_data(s_date, e_date)
        if not df.empty:
            c1, c2 = st.columns(2)
            c1.download_button("📄 CSV 다운", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), f"대관_{s_date}.csv", use_container_width=True)
            c2.download_button("📊 서식 엑셀", create_styled_excel(df, sel_bu), f"대관보고서_{s_date}.xlsx", use_container_width=True)

# --- 출력 로직 ---
if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['날짜'] == d_str]
        st.markdown(f'<div class="date-bar">📅 {d_str} ({get_shift(curr)})</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                if view_mode == "가로 표":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], hide_index=True, use_container_width=True)
                else:
                    # A형 카드: 당일/기간 분리 레이아웃
                    for tp, label in [('당일', '📌 당일 대관'), ('기간', '🗓️ 기간 대관')]:
                        sub_df = b_df[b_df['구분'] == tp].sort_values('시간')
                        if not sub_df.empty:
                            st.markdown(f'<div class="section-label">{label}</div>', unsafe_allow_html=True)
                            for _, r in sub_df.iterrows():
                                color = "#2ecc71" if tp == '당일' else "#2196F3"
                                st.markdown(f'''
                                    <div class="mobile-card" style="border-left: 5px solid {color};">
                                        <div class="row-1">
                                            <span class="loc-text">📍 {r["장소"]}</span>
                                            <span class="time-text">🕒 {r["시간"]}</span>
                                            <span class="status-badge">확정</span>
                                        </div>
                                        <div class="row-2"><b>{r["행사명"]}</b> / {r["부서"]}</div>
                                        {f'<div class="period-tag">🗓️ {r["상세기간"]} ({r["요일"]})</div>' if tp=='기간' else ''}
                                    </div>''', unsafe_allow_html=True)
        curr += timedelta(days=1)
