import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (줌을 막는 meta 태그를 삽입하지 않도록 기본값 유지)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. CSS 설정 (줌 방해 요소 제거 및 표 규격 강제)
st.markdown("""
<style>
    /* 1. 줌 관련: 브라우저의 기본 확대 기능을 절대 건드리지 않음 */
    html, body { 
        overflow-x: auto !important; 
        -webkit-overflow-scrolling: touch !important;
    }

    /* 2. 표 스타일: 장소보다 시간을 작게 설정 (요청사항 반영) */
    .stTable { width: 100%; min-width: 850px !important; } /* 표 전체 최소 너비 고정 */
    
    /* HTML Table 전용 스타일 */
    .fixed-table { 
        width: 100%; 
        min-width: 850px; 
        border-collapse: collapse; 
        table-layout: fixed; 
    }
    .fixed-table th, .fixed-table td { 
        border: 1px solid #dee2e6; 
        padding: 8px 4px; 
        font-size: 13px; 
        text-align: center;
        vertical-align: middle;
    }
    
    /* 열 너비 강제 배분 (시간 필드를 작게) */
    .w-place { width: 120px; }
    .w-time  { width: 85px; }  /* 시간 필드 최소화 */
    .w-event { width: auto; }  /* 행사명은 남는 공간 확보 */
    .w-dept  { width: 110px; }
    .w-stat  { width: 50px; }

    .date-sat { color: #007BFF; font-weight: bold; }
    .date-sun { color: #FF0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (성공했던 로직 동일 유지)
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
                        '인원': item.get('peopleCount', ''),
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

# 4. 화면 출력 부분
st.sidebar.title("조회 설정")
s_date = st.sidebar.date_input("시작일", now_today)
e_date = st.sidebar.date_input("종료일", s_date + timedelta(days=7))
target_bu = st.sidebar.multiselect("건물 선택", BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(s_date, e_date)

st.title("🏫 성의교정 대관 현황")

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        w_num = day_df.iloc[0]['w_num']
        c_name = "date-sat" if w_num == 5 else ("date-sun" if w_num == 6 else "")
        
        st.markdown(f'### <span class="{c_name}">📅 {date} ({day_df.iloc[0]["요일"]})</span>', unsafe_allow_html=True)
        
        for bu in target_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.info(f"🏢 {bu}")
                
                # 줌 기능을 위해 HTML 구조를 단순화하여 출력
                html_code = f"""
                <div style="overflow-x: auto;">
                    <table class="fixed-table">
                        <thead>
                            <tr>
                                <th class="w-place">장소</th>
                                <th class="w-time">시간</th>
                                <th class="w-event">행사명</th>
                                <th class="w-dept">부서</th>
                                <th class="w-stat">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, r in bu_df.iterrows():
                    html_code += f"""
                        <tr>
                            <td>{r['장소']}</td>
                            <td>{r['시간']}</td>
                            <td style="text-align:left;">{r['행사명']}</td>
                            <td>{r['부서']}</td>
                            <td>{r['상태']}</td>
                        </tr>
                    """
                html_code += "</tbody></table></div>"
                st.markdown(html_code, unsafe_allow_html=True)
else:
    st.write("조회된 데이터가 없습니다.")

