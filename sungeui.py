import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import csv

# 1. 페이지 설정 및 디자인 CSS (기존 스타일 유지 + A형 로직 보완)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main .block-container { max-width: 1200px; margin: 0 auto; padding: 0.5rem 1rem !important; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; font-size: 15px; }
    .date-bar:first-of-type { margin-top: 0px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    
    /* 기존 카드 스타일 유지 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .row-1 { display: flex; align-items: center; white-space: nowrap; width: 100%; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex: 1; overflow: hidden; text-overflow: ellipsis; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; flex-shrink: 0; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; font-weight: bold; background-color: #2ecc71; flex-shrink: 0; }
    .row-2 { font-size: 12px; color: #333; border-top: 1px solid #f8f9fa; padding-top: 6px; margin-top: 4px; }
    
    /* 섹션 구분 타이틀 */
    .section-split { font-size: 13px; font-weight: bold; color: #666; margin: 12px 0 6px 5px; display: flex; align-items: center; }
    .section-split::before { content: ""; width: 3px; height: 13px; background: #adb5bd; margin-right: 6px; border-radius: 2px; }
    
    /* 기간 정보 박스 */
    .period-info-box { font-size: 11px; color: #2E5077; background: #f8f9ff; padding: 5px 8px; border-radius: 4px; margin-top: 6px; border: 1px solid #d1d9e6; }
    </style>
""", unsafe_allow_html=True)

# --- 공통 로직 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    anchor = date(2026, 3, 13)
    diff = (target_date - anchor).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# --- 파일 생성 함수 ---
def create_csv(df):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(['날짜', '요일', '구분', '전체기간', '요일지정', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태'])
    for _, r in df.sort_values(['full_date', '시간']).iterrows():
        t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
        w_day = ["월", "화", "수", "목", "금", "토", "일"][t_dt.weekday()]
        writer.writerow([r['full_date'], w_day, "기간" if r['is_period'] else "당일", r['period_range'], r['allowed_days'], r['건물명'], r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']])
    return output.getvalue().encode('utf-8-sig')

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
            p_range = f"{item['startDt']} ~ {item['endDt']}"
            d_names = get_weekday_names(item.get('allowDay', ''))
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            'is_period': is_period, 'period_range': p_range, 'allowed_days': d_names,
                            '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# --- 메인 화면 ---
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

with st.expander("🔍 조회 및 다운로드 설정", expanded=True):
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with c2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    with c3:
        df = get_data(s_date, e_date)
        if not df.empty:
            st.download_button("📊 CSV 받기", data=create_csv(df), file_name=f"대관현황_{s_date}.csv", use_container_width=True)

if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                # 데이터 분리 (당일/기간)
                d_ev = b_df[~b_df['is_period']].sort_values('시간')
                p_ev = b_df[b_df['is_period']].sort_values('시간')
                
                if not d_ev.empty:
                    st.markdown('<div class="section-split">📌 당일 대관</div>', unsafe_allow_html=True)
                    for _, r in d_ev.iterrows():
                        st.markdown(f'<div class="mobile-card" style="border-left:5px solid #2ecc71;"><div class="row-1"><span class="loc-text">📍 {r["장소"]}</span><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span></div><div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div></div>', unsafe_allow_html=True)
                
                if not p_ev.empty:
                    st.markdown('<div class="section-split">🗓️ 기간 대관</div>', unsafe_allow_html=True)
                    for _, r in p_ev.iterrows():
                        st.markdown(f'<div class="mobile-card" style="border-left:5px solid #2196F3;"><div class="row-1"><span class="loc-text">📍 {r["장소"]}</span><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span></div><div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div><div class="period-info-box"><b>[기간]</b> {r["period_range"]} ({r["allowed_days"]})</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#999; font-size:12px; margin-left:10px;">내역 없음</div>', unsafe_allow_html=True)
        curr += timedelta(days=1)
