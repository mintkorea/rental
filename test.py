import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 사이드바 제거 CSS
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    /* 사이드바를 완전히 숨기고 메인 영역 확장 */
    [data-testid="stSidebar"] { display: none; }
    .block-container { padding: 1rem !important; }
    header { visibility: hidden; }
    
    /* 상단 설정 영역 디자인 */
    .stSelectbox, .stMultiSelect, .stDateInput { margin-bottom: 10px; }
    
    /* 폰트 및 스타일 (보내주신 캡처본 규격 유지) */
    .main-title { font-size: 28px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 20px; }
    .date-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 15px; font-size: 18px; }
    .bu-header { font-size: 20px; font-weight: bold; color: #1E3A5F; margin: 20px 0 10px 0; border-left: 8px solid #1E3A5F; padding-left: 12px; background: #f1f4f9; padding: 8px 12px; }
    
    .no-data { color: #7f8c8d; font-size: 15px; padding: 20px; background: #f8f9fa; border-radius: 6px; border: 1px dashed #ced4da; text-align: center; }
    
    /* 카드 스타일 (캡처본과 동일하게 유지) */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 8px; padding: 15px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .loc-text { font-size: 17px; font-weight: 800; color: #1E3A5F; }
    .time-text { font-size: 15px; font-weight: 700; color: #e74c3c; }
    .status-badge { padding: 4px 10px; border-radius: 4px; font-size: 12px; color: white; font-weight: bold; background-color: #2ecc71; }
    .row-2 { font-size: 14px; color: #555; border-top: 1px solid #f8f9fa; padding-top: 8px; }
    </style>
""", unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 2. 데이터 수집 로직
@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt, e_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({'full_date': curr.strftime('%Y-%m-%d'), '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}", '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'})
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 메인 화면 구성 (설정 메뉴 상단 배치)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# 상단 설정 바
with st.expander("🔍 날짜 및 건물 설정 변경 (여기를 누르세요)", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with col2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
        view_mode = st.radio("보기 모드", ["세로 카드", "가로 표"], horizontal=True)

df = get_data(s_date, e_date)

# 4. 결과 출력
curr = s_date
while curr <= e_date:
    d_str = curr.strftime('%Y-%m-%d')
    day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
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
            # 일관성: 데이터가 없을 때 표시
            st.markdown('<div class="no-data">ℹ️ 해당 건물에 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    curr += timedelta(days=1)
