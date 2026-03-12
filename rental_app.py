import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (확대를 막는 요소를 원천 차단)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 줌 기능 강제 활성화 및 표 디자인 (깔끔한 표 버전)
st.markdown("""
<style>
    /* 11번 스크린샷 스타일 복구 */
    .main-title { font-size: 24px; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .date-header { font-size: 18px; font-weight: 800; padding: 10px; background-color: #f8f9fa; border-bottom: 2px solid #2e5077; margin-top: 25px; }
    
    /* 표 규격 고정 및 스크롤 허용 */
    .table-wrapper { width: 100%; overflow-x: auto !important; }
    .report-table { width: 100%; min-width: 800px; border-collapse: collapse; }
    .report-table th, .report-table td { border: 1px solid #ddd; padding: 8px 4px; text-align: center; font-size: 14px; }
    .report-table th { background-color: #f2f2f2; }

    /* 열 너비 최적화 */
    .c-place { width: 15%; }
    .c-time  { width: 90px; } /* 시간을 조금 작게 */
    .c-event { width: auto; }
    .c-dept  { width: 100px; }
    .c-status { width: 50px; }

    /* 모바일 줌(확대)을 강제로 허용하는 브라우저 힌트 */
    @viewport { width: device-width; zoom: 1.0; user-scalable=yes; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (가장 완벽했던 로직)
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
                        'w_num': curr.weekday(),
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', ''), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', ''), 
                        '부서': item.get('mgDeptNm', ''),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 4. 화면 구성
st.markdown('<div class="main-title">🏫 성의교정 대관 조회 시스템</div>', unsafe_allow_html=True)

s_date = st.sidebar.date_input("시작일", now_today)
e_date = st.sidebar.date_input("종료일", s_date + timedelta(days=7))
target_bu = st.sidebar.multiselect("건물 필터", BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(s_date, e_date)

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]})</div>', unsafe_allow_html=True)
        
        for bu in target_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.write(f"🏢 **{bu}**")
                
                html = '<div class="table-wrapper"><table class="report-table"><thead><tr>'
                html += '<th class="c-place">장소</th><th class="c-time">시간</th><th class="c-event">행사명</th>'
                html += '<th class="c-dept">부서</th><th class="c-status">상태</th></tr></thead><tbody>'
                
                for _, r in bu_df.iterrows():
                    html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td>"
                    html += f"<td style='text-align:left;'>{r['행사명']}</td>"
                    html += f"<td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)
else:
    st.info("데이터가 없습니다.")
