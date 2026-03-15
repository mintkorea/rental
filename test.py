import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 디자인 요소 (CSS) - 스크린샷 기반 정밀 복구
st.markdown("""
    <style>
    .block-container { padding: 1rem 2rem !important; max-width: 100% !important; }
    
    /* [가로 모드] 표 디자인: 셸 크기 완전 통일 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 30px; border: 1px solid #dee2e6; }
    .custom-table th { background-color: #f8f9fa; color: #1E3A5F; padding: 12px 5px; border: 1px solid #dee2e6; font-weight: 800; font-size: 14px; text-align: center; }
    .custom-table td { padding: 12px 8px; border: 1px solid #dee2e6; text-align: center; font-size: 14px; vertical-align: middle; word-break: break-all; }
    
    /* 열 너비 고정 (부스 제외 총 6개 열) */
    .c-place { width: 20%; } .c-time { width: 15%; } .c-event { width: 35%; } 
    .c-dept { width: 15%; } .c-ppl { width: 7%; } .c-stat { width: 8%; }

    /* [세로 모드] 카드 디자인: 스크린샷 100% 복구 */
    .mobile-card { 
        background: white; border: 1px solid #eef0f2; border-radius: 15px; 
        padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .card-place { font-size: 19px; font-weight: 800; color: #1E3A5F; margin-bottom: 10px; display: flex; align-items: center; gap: 5px; }
    .card-time-row { display: flex; align-items: center; justify-content: flex-start; gap: 10px; margin-bottom: 12px; }
    .card-time { color: #e74c3c; font-weight: 700; font-size: 16px; display: flex; align-items: center; gap: 4px; }
    .status-badge { padding: 4px 12px; border-radius: 6px; font-size: 12px; font-weight: 800; color: white; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    .card-info-box { font-size: 14px; color: #444; border-top: 1px solid #f8f9fa; padding-top: 12px; line-height: 1.7; }

    /* 타이틀 및 헤더 */
    .main-title { font-size: 28px; font-weight: 900; color: #1E3A5F; text-align: center; margin-bottom: 25px; }
    .date-bar { background-color: #343a40; color: white; padding: 14px; border-radius: 10px; text-align: center; font-weight: 800; margin: 25px 0; font-size: 18px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .bu-header { font-size: 20px; font-weight: 800; color: #1E3A5F; margin: 35px 0 12px 0; border-left: 6px solid #1E3A5F; padding-left: 12px; display: flex; align-items: center; gap: 8px; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (반성: allowDay 필터링은 절대 건드리지 않음)
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": d.isoformat(), "end": d.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed_days = [str(x.strip()) for x in str(item.get('allowDay', '')).split(",") if x.strip().isdigit()]
            
            # 당일 검색 로직 최적화
            if s_dt <= d <= e_dt:
                if not allowed_days or str(d.isoweekday()) in allowed_days:
                    rows.append({
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 화면 구성
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 검색 설정")
    view_mode = st.radio("보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"])
    target_date = st.date_input("조회 날짜", value=now_today)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(target_date)

if not df.empty:
    st.markdown(f'<div class="date-bar">🗓️ {target_date.strftime("%Y-%m-%d")} | 근무조: {get_shift(target_date)}</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        b_df = df[df['건물명'].str.replace(" ", "") == bu.replace(" ", "")]
        if not b_df.empty:
            st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
            
            if view_mode == "가로 모드 (표)":
                # 디자인: 부스 제외 & 셸 크기 고정
                html = f'''<table class="custom-table">
                    <thead><tr>
                        <th class="c-place">장소</th><th class="c-time">시간</th><th class="c-event">행사명</th>
                        <th class="c-dept">부서</th><th class="c-ppl">인원</th><th class="c-stat">상태</th>
                    </tr></thead><tbody>'''
                for _, r in b_df.sort_values('시간').iterrows():
                    html += f'''<tr>
                        <td>{r["장소"]}</td><td>{r["시간"]}</td><td style="text-align:left;">{r["행사명"]}</td>
                        <td>{r["부서"]}</td><td>{r["인원"]}</td><td>{r["상태"]}</td>
                    </tr>'''
                html += '</tbody></table>'
                st.markdown(html, unsafe_allow_html=True)
            else:
                # 디자인: 카드형 레이아웃 정밀 복구
                for _, r in b_df.sort_values('시간').iterrows():
                    s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="card-place">📍 {r["장소"]}</div>
                            <div class="card-time-row">
                                <span class="card-time">🕒 {r["시간"]}</span>
                                <span class="status-badge {s_cls}">{r["상태"]}</span>
                            </div>
                            <div class="card-info-box">
                                <b>행사:</b> {r["행사명"]}<br>
                                <b>부서:</b> {r["부서"]} | <b>인원:</b> {r["인원"]}명
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
else:
    st.info("선택하신 날짜와 건물에 해당하는 대관 내역이 없습니다.")
