import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성희교정 대관 현황 조회", page_icon="📋", layout="wide")

# 2. CSS 보정 (카드 및 표 레이아웃)
st.markdown("""
    <style>
    .block-container { padding-top: 3rem !important; max-width: 95% !important; }
    
    /* 가로 모드: 표 너비 및 정렬 */
    div[data-testid="stTable"] { width: 100%; }
    div[data-testid="stTable"] table { width: 100% !important; }
    div[data-testid="stTable"] th { background-color: #f0f2f6 !important; text-align: center !important; }
    div[data-testid="stTable"] td { text-align: left !important; vertical-align: middle !important; }

    /* 세로 모드: 카드 레이아웃 정밀 보정 */
    .mobile-card { 
        background: white; border: 1px solid #e1e4e8; border-radius: 12px; 
        padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .card-place { font-size: 17px; font-weight: bold; color: #1e3a5f; margin-bottom: 8px; }
    .card-time-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .card-time { color: #e74c3c; font-weight: bold; font-size: 14px; }
    .card-info { font-size: 13px; color: #666; line-height: 1.5; border-top: 1px solid #f0f0f0; padding-top: 8px; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; }

    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; }
    .date-shift-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin: 15px 0; }
    .bu-title { font-size: 19px; font-weight: bold; color: #1e3a5f; margin: 25px 0 10px 0; padding-left: 10px; border-left: 5px solid #1e3a5f; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (기존 유지)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    rows.append({
                        '날짜': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 엑셀 다운로드 서식 적용 함수
def to_excel_with_format(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook = writer.book
        worksheet = writer.sheets['대관현황']
        header_format = workbook.add_format({'bold': True, 'bg_color': '#F0F2F6', 'border': 1})
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            worksheet.set_column(col_num, col_num, 20) # 너비 자동 조절 대신 기본 20 설정
    return output.getvalue()

# 4. 화면 구성
with st.sidebar:
    st.header("⚙️ 검색 설정")
    view_mode = st.radio("보기 모드 선택", ["세로 모드 (카드)", "가로 모드 (표)"], index=0)
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    
    df_res = get_data(s_date, e_date)
    if not df_res.empty:
        st.markdown("---")
        st.download_button("📥 엑셀 파일 다운로드", to_excel_with_format(df_res), f"대관현황_{s_date}.xlsx", use_container_width=True)

st.markdown('<div class="main-header">📋 성희교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_res.empty:
    for d_str in sorted(df_res['날짜'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} ({get_shift(d_obj)})</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df_res[(df_res['날짜'] == d_str) & (df_res['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-title">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                if view_mode == "가로 모드 (표)":
                    # No 없이 필요한 열만 노출
                    st.table(b_df[['장소', '시간', '행사명', '부서', '상태']])
                else:
                    for _, r in b_df.iterrows():
                        color = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="card-place">📍 {r["장소"]}</div>
                                <div class="card-time-row">
                                    <span class="card-time">🕒 {r["시간"]}</span>
                                    <span class="status-badge" style="background-color:{color};">{r["상태"]}</span>
                                </div>
                                <div class="card-info">
                                    <b>행사명:</b> {r["행사명"]}<br>
                                    <b>부서:</b> {r["부서"]}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
else:
    st.info("해당 조건의 대관 내역이 없습니다.")

