import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
today_now = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

# 2. CSS (여백 최소화, 시간 우측 배치)
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    header {visibility: hidden;}
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin: 0; padding: 5px 0; }
    .date-bar { background-color: #343a40; color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 8px; font-size: 14px; }
    .bu-header { font-size: 16px; font-weight: bold; color: #1E3A5F; margin: 12px 0 5px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 8px 12px; margin-bottom: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 12px; }
    .status-badge { padding: 1px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; min-width: 38px; text-align: center; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    .row-2 { font-size: 12px; color: #555; border-top: 1px solid #f8f9fa; margin-top: 4px; padding-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (요일 필터 정교화)
def get_shift(d):
    base = date(2026, 3, 13)
    return f"{['A', 'B', 'C'][(d - base).days % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_d, end_d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_d.isoformat(), "end": end_d.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        
        # 16일 선택 시 16일만 나오게 하는 핵심 로직
        current_date = start_d
        while current_date <= end_d:
            current_weekday_idx = (current_date.weekday() + 1) % 7
            for item in raw:
                # 시작~종료 기간 내에 해당 날짜가 포함되는지 확인
                s_dt = datetime.strptime(item.get('startDt'), '%Y-%m-%d').date()
                e_dt = datetime.strptime(item.get('endDt'), '%Y-%m-%d').date()
                
                if s_dt <= current_date <= e_dt:
                    allow_days = str(item.get('allowDay', '')).split(',')
                    if str(current_weekday_idx) in allow_days or not item.get('allowDay'):
                        rows.append({
                            '날짜': current_date,
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
            current_date += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. UI 및 결과 없음 처리
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 설정")
    date_range = st.date_input("조회 기간", value=[today_now, today_now])
    view_mode = st.radio("모드", ["세로 카드", "가로 표"])
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

if len(date_range) == 2:
    s_d, e_d = date_range
    df = get_data(s_d, e_d)
    
    # 선택된 건물들에 대한 데이터가 하나라도 있는지 체크
    has_any_data = False
    if not df.empty:
        # 건물명 정규화 후 필터링
        filtered_df = df[df['건물명'].str.replace(" ", "").isin([b.replace(" ", "") for b in sel_bu])]
        
        if not filtered_df.empty:
            has_any_data = True
            for d in sorted(filtered_df['날짜'].unique()):
                st.markdown(f'<div class="date-bar">📅 {d} ({WEEKDAYS[(d.weekday()+1)%7]}요일) | {get_shift(d)}</div>', unsafe_allow_html=True)
                
                day_df = filtered_df[filtered_df['날짜'] == d]
                for bu in sel_bu:
                    b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                    if not b_df.empty:
                        st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                        for _, r in b_df.sort_values('시간').iterrows():
                            s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                            st.markdown(f'''
                                <div class="mobile-card">
                                    <div class="row-1">
                                        <span class="loc-text">📍 {r["장소"]}</span>
                                        <span class="time-text">🕒 {r["시간"]}</span>
                                        <span class="status-badge {s_cls}">{r["상태"]}</span>
                                    </div>
                                    <div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                                </div>
                            ''', unsafe_allow_html=True)

    # 100번 말씀하신 "결과 없을 때 안내문" 처리
    if not has_any_data:
        st.warning(f"⚠️ {s_d} ~ {e_d} 기간 동안 선택하신 건물({', '.join(sel_bu)})의 대관 내역이 없습니다.")
