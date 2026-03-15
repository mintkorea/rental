import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 CSS (기존 스타일 유지)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    header {visibility: hidden;}
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin: 0; padding: 5px 0; }
    .date-bar { background-color: #343a40; color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 8px; font-size: 14px; }
    .bu-header { font-size: 16px; font-weight: bold; color: #1E3A5F; margin: 12px 0 5px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; }
    .no-data { color: #7f8c8d; font-size: 13px; padding: 10px; background: #f8f9fa; border-radius: 4px; margin: 5px 0; border: 1px dashed #ced4da; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 8px 12px; margin-bottom: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 12px; }
    .status-badge { padding: 1px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; min-width: 38px; text-align: center; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    .row-2 { font-size: 12px; color: #555; border-top: 1px solid #f8f9fa; margin-top: 4px; padding-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
""", unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 2. 데이터 수집 및 엄격 필터링 (사용자 로직)
@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed_days = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 메인 UI
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

# 날짜별 출력 루프
curr_date = s_date
while curr_date <= e_date:
    d_str = curr_date.strftime('%Y-%m-%d')
    st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr_date.isoweekday()]}요일) | {get_shift(curr_date)}</div>', unsafe_allow_html=True)
    
    # 해당 날짜에 데이터가 아예 없는 경우 대비
    day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
    
    for bu in sel_bu:
        bu_clean = bu.replace(" ", "")
        b_df = day_df[day_df['건물명'].str.replace(" ", "") == bu_clean] if not day_df.empty else pd.DataFrame()
        
        # 건물명 헤더 출력
        st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
        
        if not b_df.empty:
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
        else:
            # 말씀하신 "대관 내역이 없습니다" 표출 부분
            st.markdown('<div class="no-data">ℹ️ 해당 일자에 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
            
    curr_date += timedelta(days=1)
