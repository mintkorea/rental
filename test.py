import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
today_now = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

# 2. CSS (여백 최소화, 시간 우측 끝 배치)
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

# 3. 데이터 로직 (날짜/요일 필터링만 집중)
def get_shift(d):
    base = date(2026, 3, 13)
    return f"{['A', 'B', 'C'][(d - base).days % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_d, end_d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_d.isoformat(), "end": end_d.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        return res.json().get('res', [])
    except: return []

# 4. 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 설정")
    date_range = st.date_input("조회 기간", value=[today_now, today_now])
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

if len(date_range) == 2:
    s_d, e_d = date_range
    raw_data = get_data(s_d, e_d)
    
    # 선택된 기간 내의 "개별 날짜"를 돌며 데이터가 있는지 확인
    found_any = False
    curr = s_d
    while curr <= e_d:
        # 1. 해당 날짜의 요일 인덱스 (0일~6토)
        wd_idx = str((curr.weekday() + 1) % 7)
        
        # 2. 해당 날짜에 열리는 행사 필터링
        day_events = []
        for item in raw_data:
            # 선택한 건물인지 확인
            if str(item.get('buNm', '')).strip().replace(" ", "") in [b.replace(" ", "") for b in sel_bu]:
                # 해당 날짜가 행사 기간에 포함되고, 해당 요일에 행사가 있는지 확인
                s_dt = datetime.strptime(item.get('startDt'), '%Y-%m-%d').date()
                e_dt = datetime.strptime(item.get('endDt'), '%Y-%m-%d').date()
                allow_days = str(item.get('allowDay', '')).split(',')
                
                if s_dt <= curr <= e_dt and (wd_idx in allow_days or not item.get('allowDay')):
                    day_events.append(item)

        # 3. 필터링된 데이터가 있으면 출력
        if day_events:
            found_any = True
            st.markdown(f'<div class="date-bar">📅 {curr} ({WEEKDAYS[int(wd_idx)]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
            
            for bu in sel_bu:
                bu_events = [e for e in day_events if e.get('buNm','').strip().replace(" ","") == bu.replace(" ","")]
                if bu_events:
                    st.markdown(f'<div class="bu-header">🏢 {bu} ({len(bu_events)}건)</div>', unsafe_allow_html=True)
                    for e in sorted(bu_events, key=lambda x: x.get('startTime', '')):
                        s_cls = "status-y" if e.get('status') == 'Y' else "status-n"
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="row-1">
                                    <span class="loc-text">📍 {e.get('placeNm','-')}</span>
                                    <span class="time-text">🕒 {e.get('startTime')}~{e.get('endTime')}</span>
                                    <span class="status-badge {s_cls}">{'확정' if e.get('status')=='Y' else '대기'}</span>
                                </div>
                                <div class="row-2">🏷️ <b>{e.get('eventNm','-')}</b> / {e.get('mgDeptNm','-')} ({e.get('peopleCount','0')}명)</div>
                            </div>
                        ''', unsafe_allow_html=True)
        curr += timedelta(days=1)

    # 100번 말씀하신 "결과 없을 때" 안내문 (가장 바깥쪽에서 체크)
    if not found_any:
        st.warning(f"⚠️ {s_d} ~ {e_d} 기간 내 선택하신 건물({', '.join(sel_bu)})의 대관 내역이 없습니다.")
