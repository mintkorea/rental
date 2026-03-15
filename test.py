import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정 및 CSS (날짜 바 상단 마진 대폭 강화)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 0.5rem 1rem !important; }
    
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    
    /* [핵심 수정] 날짜 바 상단 여백을 50px로 늘려 전날 데이터와 확실히 분리 */
    .date-bar { 
        background-color: #343a40; 
        color: white; 
        padding: 12px; 
        border-radius: 6px; 
        text-align: center; 
        font-weight: bold; 
        margin-top: 50px; /* 기존보다 훨씬 넓게 설정 */
        margin-bottom: 15px; 
        font-size: 15px; 
    }
    /* 첫 번째 날짜 바는 상단 여백 제거 */
    .date-bar:first-of-type { margin-top: 0px; }

    .bu-header { 
        font-size: 17px; 
        font-weight: bold; 
        color: #1E3A5F; 
        margin: 15px 0 10px 0; 
        border-left: 5px solid #1E3A5F; 
        padding: 6px 12px; 
        background: #f1f4f9; 
    }
    
    /* 카드 디자인: 폰트 축소 및 시간 우측 강제 정렬 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    
    .row-1 { 
        display: flex; 
        align-items: center; 
        white-space: nowrap; 
        width: 100%;
    }
    
    .loc-text { font-size: 13.5px; font-weight: 800; color: #1E3A5F; flex: 1; overflow: hidden; text-overflow: ellipsis; }
    
    .time-text { 
        font-size: 12.5px; 
        font-weight: 700; 
        color: #e74c3c; 
        margin-left: auto; /* 우측 끝으로 밀기 */
        margin-right: 8px; 
        flex-shrink: 0;
    }
    
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; background-color: #2ecc71; flex-shrink: 0; }
    
    .row-2 { font-size: 11.5px; color: #555; border-top: 1px solid #f8f9fa; padding-top: 6px; margin-top: 6px; }
    
    .no-data { color: #7f8c8d; font-size: 12px; padding: 12px; background: #f8f9fa; border-radius: 6px; border: 1px dashed #ced4da; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 및 로직 (기존과 동일)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

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
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({'full_date': curr.strftime('%Y-%m-%d'), '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}", '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'})
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 레이아웃
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.expander("🔍 조회 설정", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with c2:
        sel_bu = st.multiselect("건물", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
        view_mode = st.radio("보기", ["세로 카드", "가로 표"], horizontal=True)

df = get_data(s_date, e_date)

# 4. 출력부
curr = s_date
while curr <= e_date:
    d_str = curr.strftime('%Y-%m-%d')
    day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
    
    # 여백이 강화된 날짜 바
    st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")] if not day_df.empty else pd.DataFrame()
        st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
        
        if not b_df.empty:
            if view_mode == "가로 표":
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], hide_index=True, use_container_width=True)
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="row-1">
                                <span class="loc-text">📍 {r["장소"]}</span>
                                <span class="time-text">🕒 {r["시간"]}</span>
                                <span class="status-badge">확정</span>
                            </div>
                            <div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                        </div>
                    ''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data">ℹ️ 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    curr += timedelta(days=1)
