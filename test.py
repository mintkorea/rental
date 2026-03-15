import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성희교정 대관 현황 조회", page_icon="📋", layout="wide")

# 2. CSS - 레이아웃 및 카드 디자인 고정
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; max-width: 95% !important; }
    /* 가로 모드 표 스타일 */
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
    .custom-table th { background-color: #f8f9fa; padding: 12px; border: 1px solid #dee2e6; text-align: center; }
    .custom-table td { padding: 12px; border: 1px solid #dee2e6; vertical-align: middle; font-size: 14px; }
    
    /* 세로 모드 카드 스타일 */
    .mobile-card { 
        background: white; border: 1px solid #e1e4e8; border-radius: 12px; 
        padding: 18px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.06);
    }
    .card-place { font-size: 18px; font-weight: bold; color: #1e3a5f; margin-bottom: 8px; }
    .card-time-status { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
    .card-time { color: #e74c3c; font-weight: bold; font-size: 15px; }
    .status-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; }
    .card-info { font-size: 14px; color: #444; border-top: 1px solid #f0f0f0; padding-top: 10px; line-height: 1.5; }
    
    .date-shift-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin: 20px 0; }
    .bu-title { font-size: 19px; font-weight: bold; color: #1e3a5f; margin: 30px 0 10px 0; border-left: 6px solid #1e3a5f; padding-left: 12px; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 수집 함수 (안정성 강화)
def get_data(start_date, end_date):
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

def get_shift(d):
    diff = (d - date(2026, 3, 13)).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 4. 사이드바 제어
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.sidebar:
    st.header("⚙️ 검색 설정")
    view_mode = st.radio("보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"])
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    
    # 엑셀 다운로드 (가장 단순하고 안전한 방식)
    df_res = get_data(s_date, e_date)
    if not df_res.empty:
        towrite = io.BytesIO()
        df_res.to_excel(towrite, index=False, engine='xlsxwriter')
        st.download_button("📥 엑셀 결과 다운로드", towrite.getvalue(), f"대관현황_{s_date}.xlsx", use_container_width=True)

# 5. 메인 뷰
st.markdown("## 📋 성희교정 대관 현황 조회")

if not df_res.empty:
    for d_str in sorted(df_res['날짜'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df_res[(df_res['날짜'] == d_str) & (df_res['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-title">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                if view_mode == "가로 모드 (표)":
                    # HTML로 표를 직접 그려 인덱스(No) 원천 제거
                    table_html = '<table class="custom-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>상태</th></tr></thead><tbody>'
                    for _, r in b_df.iterrows():
                        table_html += f'<tr><td style="text-align:center">{r["장소"]}</td><td style="text-align:center">{r["시간"]}</td><td>{r["행사명"]}</td><td style="text-align:center">{r["부서"]}</td><td style="text-align:center">{r["상태"]}</td></tr>'
                    table_html += '</tbody></table>'
                    st.markdown(table_html, unsafe_allow_html=True)
                else:
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
    st.info("조회된 대관 내역이 없습니다. 날짜를 변경해 보세요.")
