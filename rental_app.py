import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (가장 상단에 위치)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 줌(확대) 강제 활성화 및 표 디자인 CSS
# touch-action: auto와 user-scalable: yes를 통해 브라우저 제어권을 확보합니다.
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        touch-action: auto !important;
        user-scalable: yes !important;
    }
    .main-title { font-size: 20px; font-weight: 800; text-align: center; margin-bottom: 10px; color: #1E3A5F; }
    .date-header { font-size: 18px; font-weight: 800; color: #1E3A5F; padding: 10px; background-color: #f0f2f6; border-left: 5px solid #2E5077; margin-top: 30px; }
    .bu-header { font-size: 15px; font-weight: 700; margin: 15px 0 8px 0; color: #333; border-bottom: 1px solid #ddd; width: fit-content; }
    
    .table-container { width: 100%; overflow-x: auto !important; }
    table { width: 100%; border-collapse: collapse; min-width: 850px; table-layout: fixed; }
    th, td { border: 1px solid #ddd; padding: 10px 4px; text-align: center; font-size: 14px; vertical-align: middle; }
    th { background-color: #f8f9fa; font-weight: bold; }
    
    /* 요청하신 열 너비 최적화: 시간 열 슬림화 */
    .col-place { width: 120px; }
    .col-time  { width: 85px; } 
    .col-event { width: auto; }
    .col-count { width: 45px; }
    .col-dept  { width: 110px; }
    .col-stat  { width: 55px; }

    .text-left { text-align: left !important; padding-left: 10px !important; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (KST 기준)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
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
                if s_date <= curr <= e_date:
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', ''), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', ''), 
                        '인원': item.get('peopleCount', ''),
                        '부서': item.get('mgDeptNm', ''),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 사이드바 및 필터 (로직 단순화)
st.sidebar.title("📅 대관 조회 필터")
s_date = st.sidebar.date_input("시작일", now_today)
e_date = st.sidebar.date_input("종료일", s_date)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

raw_df = get_data(s_date, e_date)

# 5. 메인 화면 출력 (선택한 건물만 루프)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not raw_df.empty:
    # 필터링: 사용자가 선택한 건물이 포함된 데이터만 추출
    filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)].copy()
    
    if not filtered_df.empty:
        for date in sorted(filtered_df['full_date'].unique()):
            day_df = filtered_df[filtered_df['full_date'] == date]
            st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
            
            for bu in BUILDING_ORDER:
                if bu in selected_bu:
                    bu_df = day_df[day_df['건물명'] == bu]
                    if not bu_df.empty:
                        st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                        
                        rows_html = "".join([f"""
                            <tr>
                                <td>{r['장소']}</td><td>{r['시간']}</td><td class="text-left">{r['행사명']}</td>
                                <td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td>
                            </tr>
                        """ for _, r in bu_df.iterrows()])
                        
                        st.markdown(f"""
                        <div class="table-container">
                            <table>
                                <thead>
                                    <tr>
                                        <th class="col-place">장소</th><th class="col-time">시간</th><th class="col-event">행사명</th>
                                        <th class="col-count">인원</th><th class="col-dept">부서</th><th class="col-stat">상태</th>
                                    </tr>
                                </thead>
                                <tbody>{rows_html}</tbody>
                            </table>
                        </div>
                        """, unsafe_allow_html=True)
    else:
        st.info("선택한 건물의 대관 내역이 없습니다.")
else:
    st.info("조회된 데이터가 없습니다.")
