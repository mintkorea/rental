import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (최상단)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 브라우저 줌 봉인 해제용 특수 CSS
st.markdown("""
<style>
    /* 1. 브라우저에게 확대를 절대 막지 말라고 강제 명령 */
    html, body, [data-testid="stAppViewContainer"] {
        touch-action: auto !important;
        user-scalable: yes !important;
        -webkit-overflow-scrolling: touch !important;
    }

    /* 2. 표 디자인 (11번 스크린샷 기반 복구) */
    .main-title { font-size: 22px; font-weight: 800; text-align: center; color: #2e5077; }
    .date-header { font-size: 18px; font-weight: 800; padding: 8px; background-color: #f0f2f6; border-left: 5px solid #2e5077; margin-top: 20px; }
    
    .table-container { width: 100%; overflow-x: auto !important; }
    .custom-table { width: 100%; min-width: 850px; border-collapse: collapse; table-layout: fixed; }
    .custom-table th, .custom-table td { border: 1px solid #ddd; padding: 10px 5px; text-align: center; font-size: 14px; }
    .custom-table th { background-color: #f8f9fa; font-weight: bold; }

    /* 열 너비 고정: 시간 열을 슬림하게 */
    .col-place { width: 120px; }
    .col-time  { width: 85px; } 
    .col-event { width: auto; }
    .col-dept  { width: 110px; }
    .col-status { width: 55px; }

    /* 텍스트 줄바꿈 방지 및 생략 */
    .cell-content { white-space: normal; line-height: 1.3; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (검증된 로직 유지)
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

# 4. 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

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
                
                html = f"""
                <div class="table-container">
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th class="col-place">장소</th>
                                <th class="col-time">시간</th>
                                <th class="col-event">행사명</th>
                                <th class="col-dept">부서</th>
                                <th class="col-status">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, r in bu_df.iterrows():
                    html += f"""
                        <tr>
                            <td><div class="cell-content">{r['장소']}</div></td>
                            <td>{r['시간']}</td>
                            <td style="text-align:left;"><div class="cell-content">{r['행사명']}</div></td>
                            <td><div class="cell-content">{r['부서']}</div></td>
                            <td>{r['상태']}</td>
                        </tr>
                    """
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)
else:
    st.info("데이터가 없습니다.")
