import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 디자인 강화 (테두리 및 간격 최적화)
st.markdown("""
<style>
    .main-title { font-size: 26px !important; font-weight: 800; text-align: center; margin-bottom: 20px; }
    
    /* 날짜 구분: 아주 굵은 파란색 선과 넓은 여백 */
    .date-header { 
        font-size: 22px !important; font-weight: 800 !important; 
        margin-top: 100px !important; margin-bottom: 20px !important;
        padding-bottom: 10px !important;
        border-bottom: 5px solid #007BFF !important; 
        color: #007BFF !important;
    }
    
    /* 테이블: 테두리를 검은색에 가깝게 진하게 설정 */
    .table-container td, .table-container th { 
        border: 2px solid #555555 !important; 
        padding: 12px !important;
        text-align: center !important;
        color: #000000 !important; /* 글자색 검정 고정 */
    }
    .table-container th { background-color: #f8f9fa !important; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 (캐시 5초)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

@st.cache_data(ttl=5)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            allowed = [int(d.strip()) for d in str(item['allowDay']).split(',') if d.strip()] if item.get('allowDay') else []
            s_ptr, e_ptr = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_ptr
            while curr <= e_ptr:
                if s_date <= curr <= e_date:
                    if not allowed or (curr.weekday() + 1) in allowed:
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
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 4. UI 레이아웃
st.sidebar.title("📅 대관 조회 설정")
s_day = st.sidebar.date_input("시작일", value=now_today)
e_day = st.sidebar.date_input("종료일", value=s_day)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

df = get_data(s_day, e_day)

if not df.empty:
    for date in sorted(df['full_date'].unique()):
        day_df = df[df['full_date'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        for b in sel_bu:
            b_df = day_df[day_df['건물명'] == b]
            if not b_df.empty:
                st.markdown(f"**🏢 {b}**")
                rows_html = "".join([f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in b_df.iterrows()])
                st.markdown(f'<div class="table-container"><table><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>인원</th><th>부서</th><th>상태</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
else:
    st.info("선택하신 날짜와 건물에 대관 내역이 없습니다. 사이드바에서 날짜를 확인해 주세요.")
