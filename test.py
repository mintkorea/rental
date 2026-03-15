import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 통합 디자인 CSS (오늘의 핵심 작업)
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; max-width: 98% !important; }
    
    /* [가로 모드] 표 디자인: 인덱스(No) 원천 제거 및 깔끔한 보더 */
    .custom-table { width: 100%; border-collapse: collapse; margin-top: 10px; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .custom-table th { background-color: #f8f9fa; color: #1E3A5F; padding: 12px; border: 1px solid #dee2e6; font-weight: bold; }
    .custom-table td { padding: 12px; border: 1px solid #dee2e6; text-align: center; font-size: 14px; vertical-align: middle; background-color: white; }

    /* [세로 모드] 카드 디자인: 시간/상태 정렬 및 가독성 보정 */
    .mobile-card { 
        background: white; border: 1px solid #e1e4e8; border-radius: 12px; 
        padding: 18px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.06);
    }
    .card-place { font-size: 18px; font-weight: bold; color: #1E3A5F; margin-bottom: 8px; }
    .card-time-status { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .card-time { color: #e74c3c; font-weight: bold; font-size: 15px; }
    .status-badge { display: inline-block; padding: 3px 10px; border-radius: 5px; font-size: 12px; font-weight: bold; color: white; }
    .status-y { background-color: #27ae60; } /* 확정 */
    .status-n { background-color: #95a5a6; } /* 대기 */
    .card-info { font-size: 14px; color: #444; border-top: 1px solid #f0f0f0; padding-top: 10px; line-height: 1.6; }

    /* 날짜 헤더 및 건물 타이틀 */
    .date-shift-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin: 25px 0; font-size: 17px; }
    .bu-title { font-size: 19px; font-weight: bold; color: #1E3A5F; margin: 30px 0 10px 0; border-left: 6px solid #1E3A5F; padding-left: 12px; }
    </style>
""", unsafe_allow_html=True)

# 3. 로직 함수 (근무조 및 데이터 수집)
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
            allowed_days = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '부스': str(item.get('boothCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 사이드바 제어
with st.sidebar:
    st.header("🔍 조회 설정")
    view_mode = st.radio("보기 모드 선택", ["세로 모드 (카드형)", "가로 모드 (표 형식)"], index=0)
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

# 5. 메인 화면 출력 (디자인 적용부)
st.markdown("<h2 style='text-align:center; color:#1E3A5F;'>🏫 성의교정 대관 현황</h2>", unsafe_allow_html=True)

if not df.empty:
    for d_str in sorted(df['날짜'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | 근무조: {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            # 건물명 매칭 시 공백 제거하여 정확도 상승
            b_df = df[(df['날짜'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            
            if not b_df.empty:
                st.markdown(f'<div class="bu-title">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                if "표 형식" in view_mode:
                    # 가로 모드 디자인: HTML 테이블로 인덱스 열 제거
                    html = '<table class="custom-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>인원</th><th>부스</th><th>상태</th></tr></thead><tbody>'
                    for _, r in b_df.sort_values('시간').iterrows():
                        html += f'<tr><td>{r["장소"]}</td><td>{r["시간"]}</td><td style="text-align:left;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["인원"]}</td><td>{r["부스"]}</td><td>{r["상태"]}</td></tr>'
                    html += '</tbody></table>'
                    st.markdown(html, unsafe_allow_html=True)
                else:
                    # 세로 모드 디자인: 카드 레이아웃 적용
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
                                    <b>부서:</b> {r["부서"]} | <b>인원:</b> {r["인원"]} | <b>부스:</b> {r["부스"]}
                                </div>
                            </div>
                        ''', unsafe_allow_html=True)
else:
    st.info("조회된 날짜 범위 내에 대관 내역이 없습니다.")
