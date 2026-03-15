import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성희교정 대관 현황 조회", page_icon="📋", layout="wide")

# 2. CSS - 가로/세로 모드 고정 (인덱스 숨김 포함)
st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; max-width: 95% !important; }
    div[data-testid="stTable"] thead tr th:first-child { display: none !important; }
    div[data-testid="stTable"] tbody tr td:first-child { display: none !important; }
    div[data-testid="stTable"] table { width: 100% !important; }
    .mobile-card { 
        background: white; border: 1px solid #e1e4e8; border-radius: 12px; 
        padding: 18px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.06);
    }
    .card-place { font-size: 18px; font-weight: bold; color: #1e3a5f; margin-bottom: 8px; }
    .card-time-status { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .card-time { color: #e74c3c; font-weight: bold; font-size: 15px; }
    .status-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; }
    .card-info { font-size: 14px; color: #444; border-top: 1px solid #f0f0f0; padding-top: 10px; line-height: 1.5; }
    .date-shift-bar { background-color: #343a40; color: white; padding: 14px; border-radius: 10px; text-align: center; font-weight: bold; margin: 25px 0; }
    .bu-title { font-size: 19px; font-weight: bold; color: #1e3a5f; margin: 30px 0 10px 0; border-left: 6px solid #1e3a5f; padding-left: 12px; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로딩 (캐시 제거하여 실시간 조회 강제)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json().get('res', [])
        rows = []
        for item in data:
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
    except:
        return pd.DataFrame()

# 조 계산 및 엑셀 변환
def get_shift(d):
    diff = (d - date(2026, 3, 13)).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

# 4. 사이드바
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.sidebar:
    st.header("⚙️ 검색 설정")
    view_mode = st.radio("보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"], index=0)
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)
    
    # 데이터 강제 새로고침 버튼
    if st.button("🔄 데이터 새로고침"):
        st.cache_data.clear()

    df_res = get_data(s_date, e_date)
    if not df_res.empty:
        st.download_button("📥 엑셀 다운로드", to_excel(df_res), f"대관현황_{s_date}.xlsx", use_container_width=True)

# 5. 메인 화면
st.header("📋 성희교정 대관 현황 조회")

if not df_res.empty:
    for d_str in sorted(df_res['날짜'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            # 건물명 공백 제거 후 비교로 검색 누락 방지
            b_df = df_res[(df_res['날짜'] == d_str) & (df_res['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-title">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                if view_mode == "가로 모드 (표)":
                    st.table(b_df[['장소', '시간', '행사명', '부서', '상태']])
                else:
                    for _, r in b_df.iterrows():
                        color = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="card-place">📍 {r["장소"]}</div>
                                <div class="card-time-status">
                                    <span class="card-time">🕒 {r["시간"]}</span>
                                    <span class="status-badge" style="background-color:{color};">{r["상태"]}</span>
                                </div>
                                <div class="card-info">📄 {r["행사명"]}<br>🏢 {r["부서"]}</div>
                            </div>
                        ''', unsafe_allow_html=True)
else:
    st.warning("현재 조회된 내역이 없습니다. 시작일과 종료일을 확인하시거나 '데이터 새로고침'을 눌러주세요.")
