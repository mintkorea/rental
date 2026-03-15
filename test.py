import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일 (첫 행 통합 및 비율 최적화)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@500;700;900&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Noto Sans KR', sans-serif; }
    
    /* [모바일 셸 레이아웃] */
    .event-shell { border-bottom: 1px solid #eee; padding: 10px 5px; background: white; }
    
    /* 첫 번째 줄: 장소(좌) + 시간(중) + 상태(우) 통합 배치 */
    .row-main { display: flex; align-items: center; justify-content: space-between; gap: 5px; }
    
    /* 장소: 가장 넓은 비중, 긴 이름은 말줄임 */
    .col-place { 
        flex: 5.5; font-size: 15px; font-weight: 700; color: #1e3a5f; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; 
    }
    /* 시간: 중간 비중, 붉은색 강조 */
    .col-time { 
        flex: 3; font-size: 13px; color: #d9534f; font-weight: bold; 
        text-align: center; white-space: nowrap;
    }
    /* 상태: 최소 비중, 우측 정렬 */
    .col-status { flex: 1.5; font-size: 12.5px; font-weight: bold; text-align: right; }

    /* 두 번째 줄: 행사명 및 상세 정보 */
    .row-sub { font-size: 13.5px; color: #666; margin-top: 4px; line-height: 1.4; word-break: keep-all; }

    /* 공통 디자인 */
    .main-title { font-size: 1.6rem; font-weight: 900; color: #1e3a5f; text-align: center; margin: 15px 0; }
    .date-container { background: #333; color: white; padding: 10px; border-radius: 8px; margin: 15px 0 10px 0; font-weight: bold; }
    .bu-header { font-size: 1.1rem; font-weight: 700; color: #1e3a5f; padding: 8px 0; border-bottom: 2px solid #1e3a5f; margin-top: 10px; }
    
    /* PC 표 자동 개행 */
    .stDataFrame div[data-testid="stTable"] td { white-space: normal !important; word-break: break-all !important; font-size: 14px !important; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 수집 함수 (기존 로직 유지)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.strftime('%Y-%m-%d'), "end": e_date.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            item_s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_day_str = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_str.split(',') if d.strip().isdigit()]
            
            curr = item_s_dt
            while curr <= item_e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}-{item.get('endTime', '')}", # 물결표 대신 하이픈으로 공간 절약
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 화면 구성
st.markdown('<div class="main-title">🏢 성의교정 실시간 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("조회일", value=datetime.now(KST).date())
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    view_mode = st.radio("보기 모드", ["📱 모바일", "💻 PC 표"], index=0)

df = get_data(s_date, s_date) # 시작/종료일을 조회일로 고정

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-container">📅 {d_str}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","").str.contains(bu.replace(" ","")))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu} <small>(총 {len(b_df)}건)</small></div>', unsafe_allow_html=True)
                
                if "모바일" in view_mode:
                    for _, row in b_df.iterrows():
                        status_color = "#28a745" if row['상태'] == "확정" else "#d9534f"
                        st.markdown(f"""
                        <div class="event-shell">
                            <div class="row-main">
                                <div class="col-place" title="{row['장소']}">📍 {row['장소']}</div>
                                <div class="col-time">⏰ {row['시간']}</div>
                                <div class="col-status" style="color:{status_color};">{row['상태']}</div>
                            </div>
                            <div class="row-sub">📄 {row['행사명']} ({row['부서']}, {row['인원']}명)</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], use_container_width=True, hide_index=True)
else:
    st.info("조회된 대관 내역이 없습니다.")
