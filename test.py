import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인 CSS
st.set_page_config(page_title="성희교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 5rem !important; max-width: 95% !important; margin: 0 auto !important; }
    
    /* [수정] 표 헤더 및 데이터 중앙 정렬 강제 CSS */
    div[data-testid="stDataFrame"] th { text-align: center !important; }
    
    /* 표 내부 줄바꿈 설정 */
    div[data-testid="stTable"] td {
        white-space: normal !important;
        word-break: keep-all !important;
        line-height: 1.4 !important;
    }

    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px; }
    .date-shift-bar { background-color: #444; color: white; padding: 12px; border-radius: 8px; text-align: center; margin: 20px 0 10px 0; font-weight: bold; font-size: 17px !important; }
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:5px 0; margin-top:10px; }
    
    /* 세로 모드(카드) 스타일 */
    .mobile-card { padding: 8px 0; border-bottom: 1px solid #eee; width: 100%; }
    .card-first-line { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .place-name { font-weight: bold; color: #333; font-size: 15px; flex: 1; }
    .time-status-area { display: flex; align-items: center; flex-shrink: 0; gap: 5px; }
    .time-text { font-size: 12px; color: #e74c3c; font-weight: bold; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; }
    
    div.stDownloadButton > button { width: 100%; background-color: #1e3a5f !important; color: white !important; border: none !important; padding: 10px !important; border-radius: 8px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# [데이터 로직 - 기존과 동일]
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
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# [엑셀 생성 로직 생략]

# 5. UI 및 데이터 표출
with st.sidebar:
    st.header("⚙️ 설정 및 도구")
    view_mode = st.radio("📱 보기 모드 설정", ["세로 모드 (카드)", "가로 모드 (표)"], index=0)
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    df_result = get_data(s_date, e_date)

st.markdown('<div class="main-header">📋 성희교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_result.empty:
    # 에러 방지를 위해 alignment 인자를 제거한 설정
    col_config = {
        "장소": st.column_config.TextColumn("장소", width="medium"),
        "시간": st.column_config.TextColumn("시간", width="small"),
        "행사명": st.column_config.TextColumn("행사명", width="large"),
        "부서": st.column_config.TextColumn("부서", width="medium"),
        "상태": st.column_config.TextColumn("상태", width="small")
    }
    
    for d_str in sorted(df_result['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df_result[(df_result['full_date'] == d_str) & (df_result['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            st.markdown(f'<div class="building-header"><div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div></div>', unsafe_allow_html=True)
            if not b_df.empty:
                if view_mode == "가로 모드 (표)":
                    # [수정] 데이터 중앙 정렬을 위해 스타일 적용 (TypeError 방지)
                    styled_df = b_df[['장소', '시간', '행사명', '부서', '상태']].style.set_properties(
                        subset=['시간', '상태'], 
                        **{'text-align': 'center'}
                    )
                    st.dataframe(styled_df, use_container_width=True, hide_index=True, column_config=col_config)
                else:
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'<div class="mobile-card"><div class="card-first-line"><div class="place-name">📍 {r["장소"]}</div><div class="time-status-area"><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge" style="background-color:{bg};">{r["상태"]}</span></div></div><div class="card-second-line">📄 {r["행사명"]} | {r["부서"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="color:#999; padding:10px; font-size:13px; text-align:center; border:1px solid #eee; margin-top:5px; border-radius:5px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회된 날짜에 대관 내역이 없습니다.")
