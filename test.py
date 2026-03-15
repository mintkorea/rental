import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import io

# 1. 페이지 설정 및 시간대
KST = ZoneInfo("Asia/Seoul")
def today_kst(): return datetime.now(KST).date()

st.set_page_config(page_title="성희교정 대관 현황", page_icon="🏫", layout="wide")

# 2. CSS 스타일 - 제공해주신 디자인 요소 통합
st.markdown("""
<style>
    .block-container { padding-top: 1.5rem !important; max-width: 95% !important; }
    
    /* [가로 모드] 커스텀 테이블 (No 제거) */
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 10px; border-radius: 8px; overflow: hidden; }
    .custom-table th { background-color: #f8f9fa; color: #1E3A5F; padding: 12px; border: 1px solid #dee2e6; font-weight: bold; }
    .custom-table td { padding: 12px; border: 1px solid #dee2e6; text-align: center; font-size: 14px; vertical-align: middle; }

    /* [세로 모드] 카드 디자인 */
    .mobile-card { 
        background: white; border: 1px solid #e1e4e8; border-radius: 12px; 
        padding: 18px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.06);
    }
    .card-place { font-size: 18px; font-weight: bold; color: #1E3A5F; margin-bottom: 8px; }
    .card-time-status { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .card-time { color: #e74c3c; font-weight: bold; font-size: 15px; }
    .status-badge { display: inline-block; padding: 2px 10px; font-size: 12px; border-radius: 5px; font-weight: bold; color: white; }
    .status-y { background-color: #27ae60; } /* 확정 */
    .status-n { background-color: #95a5a6; } /* 대기 */
    .card-info { font-size: 14px; color: #444; border-top: 1px solid #f0f0f0; padding-top: 10px; line-height: 1.5; }

    /* 헤더 및 구분 바 */
    .date-shift-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin: 25px 0; }
    .bu-title { font-size: 19px; font-weight: bold; color: #1E3A5F; margin: 30px 0 10px 0; border-left: 6px solid #1E3A5F; padding-left: 12px; }
</style>
""", unsafe_allow_html=True)

# 3. 핵심 검색 로직 (allowDay 필터링 포함)
@st.cache_data(ttl=300)
def get_processed_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw_data = res.json().get('res', [])
        rows = []
        for item in raw_data:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'][:10], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'][:10], '%Y-%m-%d').date()
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                # 1. 검색 기간 내에 있고 2. allowDay(요일)에 해당하는 날만 포함
                target_wd = str(curr.weekday() + 1) # 월=1, ..., 일=7
                if start_date <= curr <= end_date:
                    if not allow_days or target_wd in allow_days:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
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

def get_work_shift(d):
    anchor = date(2026, 3, 13)
    diff = (d - anchor).days
    shifts = ["A조", "B조", "C조"]
    return shifts[diff % 3]

# 4. 사이드바 구성
ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]

with st.sidebar:
    st.header("🔍 검색 설정")
    view_mode = st.radio("보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"])
    s_date = st.date_input("시작일", value=today_kst())
    e_date = st.date_input("종료일", value=s_date)
    selected_bu = st.multiselect("건물 선택", options=ALL_BU, default=["성의회관", "의생명산업연구원"])
    
    if st.button("🔄 새로고침", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    df_res = get_processed_data(s_date, e_date)

# 5. 메인 화면 출력
st.markdown('<h2 style="color:#1E3A5F; text-align:center;">🏫 성희교정 대관 현황</h2>', unsafe_allow_html=True)

if not df_res.empty:
    # 날짜별 루프
    for d_str in sorted(df_res['날짜'].unique()):
        curr_date = datetime.strptime(d_str, '%Y-%m-%d').date()
        shift_name = get_work_shift(curr_date)
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} ({shift_name})</div>', unsafe_allow_html=True)
        
        # 건물별 루프
        for bu in selected_bu:
            b_df = df_res[(df_res['날짜'] == d_str) & (df_res['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-title">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                if view_mode == "가로 모드 (표)":
                    # 디자인 요소: No 없이 HTML로 직접 렌더링
                    html = '<table class="custom-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>상태</th></tr></thead><tbody>'
                    for _, r in b_df.sort_values('시간').iterrows():
                        html += f'<tr><td>{r["장소"]}</td><td>{r["시간"]}</td><td>{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
                    html += '</tbody></table>'
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    # 디자인 요소: 카드 레이아웃 (시간 -> 상태 순)
                    for _, r in b_df.sort_values('시간').iterrows():
                        s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="card-place">📍 {r["장소"]}</div>
                                <div class="card-time-status">
                                    <span class="card-time">🕒 {r["시간"]}</span>
                                    <span class="status-badge {s_cls}">{r["상태"]}</span>
                                </div>
                                <div class="card-info">
                                    <b>행사:</b> {r["행사명"]}<br>
                                    <b>부서:</b> {r["부서"]}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다. 기간이나 건물을 확인해주세요.")
