import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import csv

# 1. 페이지 설정 및 디자인 CSS (섹션 분리 및 강조 스타일 추가)
st.set_page_config(page_title="성의교정 대관 현황 (관리용)", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main .block-container { max-width: 1200px; margin: 0 auto; padding: 0.5rem 1rem !important; }
    .main-title { font-size: 24px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 15px; }
    
    /* 상단 날짜 및 근무조 바 */
    .date-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin-top: 30px; margin-bottom: 15px; font-size: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .date-bar:first-of-type { margin-top: 0px; }
    
    /* 건물 헤더 */
    .bu-header { font-size: 18px; font-weight: bold; color: #1E3A5F; margin: 20px 0 10px 0; border-bottom: 2px solid #1E3A5F; padding-bottom: 5px; }
    
    /* 대관 유형 섹션 타이틀 (모바일 스타일 이식) */
    .section-title { font-size: 14px; font-weight: bold; color: #555; margin: 15px 0 8px 0; padding-left: 8px; border-left: 4px solid #adb5bd; background: #f8f9fa; padding-top: 3px; padding-bottom: 3px; }
    
    /* 카드 디자인 */
    .event-card { background: white; border: 1px solid #eef0f2; border-radius: 8px; padding: 12px 16px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: transform 0.1s; }
    .event-card:hover { border-color: #1E3A5F; }
    .type-day { border-left: 5px solid #28a745; }   /* 당일: 초록색 */
    .type-period { border-left: 5px solid #007bff; } /* 기간: 파란색 */
    
    .row-1 { display: flex; align-items: center; width: 100%; margin-bottom: 6px; }
    .loc-text { font-size: 15px; font-weight: 800; color: #1E3A5F; flex: 1; }
    .time-text { font-size: 14px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 10px; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; font-weight: bold; background-color: #2ecc71; }
    
    .row-2 { font-size: 13px; color: #333; margin-bottom: 8px; font-weight: 500; }
    
    /* 기간 정보 노출 박스 */
    .period-box { font-size: 12px; color: #666; background: #f1f3f5; padding: 6px 10px; border-radius: 4px; border: 1px solid #dee2e6; display: flex; justify-content: space-between; }
    .no-data { color: #999; font-size: 13px; padding: 15px; text-align: center; border: 1px dashed #ddd; border-radius: 6px; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# --- 유틸리티 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# --- 데이터 로직 ---
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

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
            
            raw_days = str(item.get('allowDay', ''))
            allowed = [d.strip() for d in raw_days.split(",") if d.strip().isdigit()]
            day_names = get_weekday_names(raw_days)
            
            # 기간/당일 구분 데이터 생성
            is_period_bool = (item['startDt'] != item['endDt'])
            period_str = f"{item['startDt']} ~ {item['endDt']}"
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            'is_period': is_period_bool,
                            'period_range': period_str,
                            'allowed_days': day_names,
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

# --- 메인 화면 ---
st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

with st.expander("🔍 조회 조건 설정", expanded=True):
    c1, c2 = st.columns([1, 2])
    with c1:
        s_date = st.date_input("조회 시작일", value=now_today)
        e_date = st.date_input("조회 종료일", value=s_date)
    with c2:
        sel_bu = st.multiselect("대상 건물", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원", "옴니버스 파크"])

df = get_data(s_date, e_date)

if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        
        # 1. 날짜 헤더 표출
        st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | 근무: {get_shift(curr)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
            st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
            
            if not b_df.empty:
                # 2. 대관 유형 분리 (당일 vs 기간)
                t_ev = b_df[~b_df['is_period']].sort_values('시간') # 당일
                p_ev = b_df[b_df['is_period']].sort_values('시간')  # 기간
                
                # --- 당일 대관 출력 ---
                if not t_ev.empty:
                    st.markdown('<div class="section-title">📌 당일 대관</div>', unsafe_allow_html=True)
                    for _, r in t_ev.iterrows():
                        st.markdown(f'''
                            <div class="event-card type-day">
                                <div class="row-1">
                                    <span class="loc-text">📍 {r["장소"]}</span>
                                    <span class="time-text">🕒 {r["시간"]}</span>
                                    <span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span>
                                </div>
                                <div class="row-2">🏷️ <b>{r["행사명"]}</b> | {r["부서"]} ({r["인원"]}명)</div>
                            </div>''', unsafe_allow_html=True)
                
                # --- 기간 대관 출력 (날짜 정보 포함) ---
                if not p_ev.empty:
                    st.markdown('<div class="section-title">🗓️ 기간 대관</div>', unsafe_allow_html=True)
                    for _, r in p_ev.iterrows():
                        st.markdown(f'''
                            <div class="event-card type-period">
                                <div class="row-1">
                                    <span class="loc-text">📍 {r["장소"]}</span>
                                    <span class="time-text">🕒 {r["시간"]}</span>
                                    <span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span>
                                </div>
                                <div class="row-2">🏷️ <b>{r["행사명"]}</b> | {r["부서"]} ({r["인원"]}명)</div>
                                <div class="period-box">
                                    <span>🗓️ 전체기간: <b>{r["period_range"]}</b></span>
                                    <span>요일: <b>{r["allowed_days"]}</b></span>
                                </div>
                            </div>''', unsafe_allow_html=True)
            else:
                st.markdown('<div class="no-data">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
        
        curr += timedelta(days=1)
else:
    st.info("해당 조건의 대관 데이터가 없습니다.")
