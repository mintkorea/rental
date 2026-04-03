import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import csv

# 1. 페이지 설정 및 디자인 CSS (B형: 정갈한 리스트 스타일)
st.set_page_config(page_title="성의교정 대관 현황 (B형)", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main .block-container { max-width: 1200px; margin: 0 auto; padding: 0.5rem 1rem !important; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 15px; }
    
    /* 날짜 구분선 */
    .date-bar { background-color: #495057; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 30px; margin-bottom: 12px; font-size: 15px; }
    .date-bar:first-of-type { margin-top: 0px; }
    
    /* 건물 헤더 */
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 15px 0 8px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f8f9fa; padding-top: 5px; padding-bottom: 5px; }
    
    /* B형 카드 디자인: 시간순 정렬에 최적화된 깔끔한 디자인 */
    .event-card-b { background: white; border: 1px solid #dee2e6; border-radius: 6px; padding: 12px 15px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    
    .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
    .time-text { font-size: 14px; font-weight: bold; color: #d9534f; background: #fff5f5; padding: 2px 6px; border-radius: 4px; }
    .loc-text { font-size: 15px; font-weight: bold; color: #333; margin-left: 10px; flex: 1; }
    .status-badge { font-size: 11px; padding: 2px 6px; border-radius: 3px; color: white; background: #5cb85c; }
    
    .row-2 { font-size: 13px; color: #555; line-height: 1.5; margin-top: 5px; border-top: 1px dashed #eee; padding-top: 5px; }
    
    /* 기간 정보 (작게 표시) */
    .period-hint { font-size: 11px; color: #888; margin-top: 4px; display: block; }
    </style>
""", unsafe_allow_html=True)

# --- 유틸리티 및 데이터 로직 (기본 유지) ---
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
            
            is_period = (item['startDt'] != item['endDt'])
            period_info = f"{item['startDt']} ~ {item['endDt']}"
            day_names = get_weekday_names(item.get('allowDay', ''))
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            'is_period': is_period,
                            'period_text': f"🗓️ {period_info} ({day_names})" if is_period else "📌 당일 대관",
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

# --- 메인 화면 구성 (B형: 통합 시간순 나열) ---
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 (통합 리스트)</div>', unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

# 검색 설정
with st.expander("🔍 조회 날짜 및 건물 선택", expanded=True):
    col1, col2 = st.columns([1, 2])
    with col1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with col2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원", "옴니버스 파크"])

df = get_data(s_date, e_date)

if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        
        st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | 근무: {get_shift(curr)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                # B형: 구분 없이 시간순으로 정렬하여 나열
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'''
                        <div class="event-card-b">
                            <div class="row-1">
                                <span class="time-text">🕒 {r["시간"]}</span>
                                <span class="loc-text">📍 {r["장소"]}</span>
                                <span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span>
                            </div>
                            <div class="row-2">
                                <b>{r["행사명"]}</b> | {r["부서"]} ({r["인원"]}명)
                                <span class="period-hint">{r["period_text"]}</span>
                            </div>
                        </div>''', unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("조회된 대관 내역이 없습니다.")
