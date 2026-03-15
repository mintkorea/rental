import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 차분한 디자인(CSS) 적용
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 3rem !important; }
    section[data-testid="stSidebar"] { min-width: 320px !important; background-color: #f8f9fa; }
    
    /* 메인 타이틀: 기존보다 3pt 키움 (약 21px) */
    .main-title { font-size: 21px !important; font-weight: bold; color: #1e3a5f; margin-bottom: 25px; display: flex; align-items: center; gap: 10px; }
    
    /* 차분한 카드 디자인 */
    .event-card { padding: 15px 5px; border-bottom: 1px solid #eee; width: 100%; }
    .first-line { display: flex; justify-content: space-between; align-items: center; gap: 8px; width: 100%; }
    .place-name { flex: 1; font-weight: 600; color: #2c3e50; font-size: 14px; }
    .status-right { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
    .time-text { font-size: 12px; color: #555; font-weight: 500; }
    .status-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; }
    
    .second-line { font-size: 12px; color: #7f8c8d; margin-top: 6px; line-height: 1.4; }
    
    /* 건물 헤더: 차분한 네이비 톤 */
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #2c3e50; padding:8px 0; margin-top:25px; margin-bottom: 5px; }
    .count-text { font-size: 13px !important; font-weight: 600 !important; color: #7f8c8d; }
    
    /* 내역 없음 박스: 더 차분한 배경색 */
    .no-data-box { background-color: #f1f3f5; color: #666; padding: 15px; border-radius: 8px; text-align: center; font-size: 13px; margin: 10px 0; border: 1px dashed #ced4da; }
    </style>
""", unsafe_allow_html=True)

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
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
                        bu_nm_raw = str(item.get('buNm', '')).strip()
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명_key': bu_nm_raw.replace(" ", ""),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 사이드바 설정
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("보기 모드", ["모바일", "PC"], horizontal=True)

st.markdown('<div class="main-title">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

df = get_data(s_date, e_date)

# 날짜별 루프 (데이터가 없는 날짜도 표시하기 위해 s_date ~ e_date 직접 순회)
curr_day = s_date
while curr_day <= e_date:
    d_str = curr_day.strftime('%Y-%m-%d')
    # 날짜 헤더 디자인 개선
    st.markdown(f'<div style="background-color:#4a5568; color:white; padding:8px; border-radius:6px; text-align:center; margin-top:30px; font-weight:600; font-size:14px;">📅 {d_str} ({get_shift(curr_day)})</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        bu_key = bu.replace(" ", "")
        # 해당 날짜, 해당 건물의 데이터 필터링
        b_df = df[(df['full_date'] == d_str) & (df['건물명_key'] == bu_key)]
        
        st.markdown(f'<div class="building-header"><div style="font-size:15px; font-weight:bold; color:#2c3e50;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
        
        if not b_df.empty:
            if v_mode == "PC":
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
            else:
                for _, r in b_df.iterrows():
                    bg_color = '#38a169' if r['상태']=='확정' else '#a0aec0'
                    st.markdown(f"""
                        <div class="event-card">
                            <div class="first-line">
                                <div class="place-name">📍 {r['장소']}</div>
                                <div class="status-right">
                                    <span class="time-text">🕒 {r['시간']}</span>
                                    <span class="status-badge" style="background-color:{bg_color};">{r['상태']}</span>
                                </div>
                            </div>
                            <div class="second-line">📄 {r['행사명']}<br>🏢 {r['부서']}</div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            # [핵심] 3월 9일 등 데이터가 없는 건물에 대해 안내 메시지 강제 표출
            st.markdown(f'<div class="no-data-box">{bu} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
            
    curr_day += timedelta(days=1)
