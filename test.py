import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성희교정 대관 현황 조회", page_icon="📋", layout="wide")

# 2. 통합 CSS (정렬 및 개행 강제)
st.markdown("""
    <style>
    .block-container { padding-top: 5rem !important; max-width: 95% !important; margin: 0 auto !important; }
    
    /* 표 헤더 & 데이터 정렬 및 개행 */
    div[data-testid="stTable"] table { width: 100% !important; }
    div[data-testid="stTable"] th { 
        text-align: center !important; 
        background-color: #f0f2f6 !important; 
        font-weight: bold !important;
        white-space: nowrap;
    }
    div[data-testid="stTable"] td { 
        vertical-align: middle !important; 
        line-height: 1.5 !important;
        white-space: normal !important; /* 자동 줄바꿈 강제 */
        word-break: keep-all !important;
    }
    /* 시간과 상태 열 중앙 정렬 (2번째, 5번째 열) */
    div[data-testid="stTable"] td:nth-child(2),
    div[data-testid="stTable"] td:nth-child(5) { 
        text-align: center !important; 
    }

    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px; }
    .date-shift-bar { background-color: #444; color: white; padding: 12px; border-radius: 8px; text-align: center; margin: 20px 0 10px 0; font-weight: bold; font-size: 17px !important; }
    .building-header { border-bottom:2px solid #1e3a5f; padding:5px 0; margin-top:20px; font-weight: bold; color: #1e3a5f; font-size: 18px; }
    
    /* 모바일 카드 스타일 */
    .mobile-card { padding: 12px 0; border-bottom: 1px solid #eee; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; }
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
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
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

# UI 구성
with st.sidebar:
    st.header("⚙️ 설정")
    view_mode = st.radio("📱 보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"], index=1) # 가로 기본
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    df_result = get_data(s_date, e_date)

st.markdown('<div class="main-header">📋 성희교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_result.empty:
    for d_str in sorted(df_result['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df_result[(df_result['full_date'] == d_str) & (df_result['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu} (총 {len(b_df)}건)</div>', unsafe_allow_html=True)
                if view_mode == "가로 모드 (표)":
                    # [수정] st.table을 사용하여 모든 행 펼침 + 중앙 정렬 100% 보장
                    st.table(b_df[['장소', '시간', '행사명', '부서', '상태']])
                else:
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div style="display:flex; justify-content:space-between;">
                                    <span style="font-weight:bold;">📍 {r["장소"]}</span>
                                    <span class="status-badge" style="background-color:{bg};">{r["상태"]}</span>
                                </div>
                                <div style="color:#e74c3c; font-size:13px; font-weight:bold; margin:4px 0;">🕒 {r["시간"]}</div>
                                <div style="font-size:13px; color:#444;">📄 {r["행사명"]} | {r["부서"]}</div>
                            </div>
                        ''', unsafe_allow_html=True)
else:
    st.info("조회된 날짜에 대관 내역이 없습니다.")
