import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 디자인 레이아웃 (CSS 고정)
st.set_page_config(page_title="성희교정 대관 현황", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경 및 폰트 설정 */
    .block-container { padding-top: 1.5rem !important; }
    
    /* [가로 모드] 표 디자인 - 인덱스(No) 제거용 */
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    .custom-table th { background-color: #f8f9fa; color: #333; padding: 12px; border: 1px solid #dee2e6; }
    .custom-table td { padding: 12px; border: 1px solid #dee2e6; text-align: center; font-size: 14px; }

    /* [세로 모드] 카드 디자인 - 스크린샷 구조 복구 */
    .mobile-card { 
        background: white; border: 1px solid #e1e4e8; border-radius: 12px; 
        padding: 18px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.06);
    }
    .card-place { font-size: 18px; font-weight: bold; color: #1e3a5f; margin-bottom: 8px; }
    .card-time-status { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .card-time { color: #e74c3c; font-weight: bold; font-size: 15px; }
    .status-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; }
    .card-info { font-size: 14px; color: #444; border-top: 1px solid #f0f0f0; padding-top: 10px; line-height: 1.5; }

    /* 날짜 및 건물 타이틀 */
    .date-shift-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin: 20px 0; }
    .bu-title { font-size: 19px; font-weight: bold; color: #1e3a5f; margin: 30px 0 10px 0; border-left: 6px solid #1e3a5f; padding-left: 12px; }
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 검색 (기본 로직 복구)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json().get('res', [])
        rows = []
        for item in data:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'][:10], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'][:10], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
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

# 3. 사이드바 설정
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.sidebar:
    st.header("⚙️ 설정")
    view_mode = st.radio("보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"])
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)
    
    df_res = get_data(s_date, e_date)

# 4. 메인 화면 출력 (디자인 요소 적용)
st.markdown("## 📋 성희교정 대관 현황")

if not df_res.empty:
    for d_str in sorted(df_res['날짜'].unique()):
        st.markdown(f'<div class="date-shift-bar">📅 {d_str}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df_res[(df_res['날짜'] == d_str) & (df_res['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-title">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                if view_mode == "가로 모드 (표)":
                    # 디자인 요소: No 열 없이 HTML로 직접 렌더링
                    html = '<table class="custom-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>상태</th></tr></thead><tbody>'
                    for _, r in b_df.iterrows():
                        html += f'<tr><td>{r["장소"]}</td><td>{r["시간"]}</td><td>{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
                    html += '</tbody></table>'
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    # 디자인 요소: 카드 레이아웃 (시간이 상태 앞으로)
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="card-place">📍 {r["장소"]}</div>
                                <div class="card-time-status">
                                    <span class="card-time">🕒 {r["시간"]}</span>
                                    <span class="status-badge" style="background-color:{bg};">{r["상태"]}</span>
                                </div>
                                <div class="card-info"><b>행사:</b> {r["행사명"]}<br><b>부서:</b> {r["부서"]}</div>
                            </div>
                        ''', unsafe_allow_html=True)
else:
    st.info("해당 조건의 대관 내역이 없습니다. 날짜를 변경해 보세요.")
