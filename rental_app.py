import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 및 다크모드 대응 스타일
st.set_page_config(page_title="성의교정 대관 현황", layout="wide")

st.markdown("""
<style>
    /* 전체 배경과 글자색 최적화 */
    .main-title { font-size: 26px !important; font-weight: 800; text-align: center; margin: 20px 0; }
    
    /* 날짜 구분선: 아주 굵은 파란색 선으로 확실하게 구분 */
    .date-header { 
        font-size: 22px !important; font-weight: 800 !important; 
        margin-top: 80px !important; margin-bottom: 20px !important;
        padding-bottom: 10px !important;
        border-bottom: 5px solid #007BFF !important; 
        color: #007BFF !important;
    }
    
    /* 건물 헤더 */
    .building-header { 
        font-size: 18px !important; font-weight: 700 !important; 
        margin: 25px 0 10px 0 !important; 
        border-left: 10px solid #007BFF !important; padding-left: 15px !important;
    }

    /* 테이블: 다크모드/라이트모드 모두 선명하게 검은색 테두리 강제 적용 */
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
    .custom-table th { background-color: #f2f2f2; color: #333; font-weight: bold; border: 2px solid #444 !important; padding: 10px; }
    .custom-table td { border: 1px solid #666 !important; padding: 10px; text-align: center; color: inherit; }
</style>
""", unsafe_allow_html=True)

# 2. 데이터 수집 (성공했던 보안 헤더 로직 포함)
@st.cache_data(ttl=60)
def get_rental_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do",
        "X-Requested-With": "XMLHttpRequest"
    }
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=15)
        raw_data = res.json().get('res', [])
        rows = []
        for item in raw_data:
            if not item.get('startDt'): continue
            # 날짜 범위 내 데이터 가공
            rows.append({
                'date': item.get('startDt'),
                '요일': ['월','화','수','목','금','토','일'][datetime.strptime(item['startDt'], '%Y-%m-%d').weekday()],
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', ''), 
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', ''), 
                '부서': item.get('mgDeptNm', ''),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        df = pd.DataFrame(rows)
        return df.sort_values(by=['date', '시간']) if not df.empty else df
    except:
        return pd.DataFrame()

# 3. 사이드바 구성
KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.sidebar:
    st.header("📅 조회 설정")
    s_day = st.date_input("시작일", value=today)
    e_day = st.date_input("종료일", value=today + timedelta(days=7))
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원", "옴니버스 파크"])

# 4. 메인 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

df = get_rental_data(s_day, e_day)

if not df.empty:
    for date in sorted(df['date'].unique()):
        day_df = df[df['date'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]})</div>', unsafe_allow_html=True)
        
        for b in sel_bu:
            b_df = day_df[day_df['건물명'].str.contains(b) if b else day_df['건물명'] == b]
            if not b_df.empty:
                st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                
                # HTML 테이블 생성
                table_html = '<table class="custom-table"><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>상태</th></tr></thead><tbody>'
                for _, r in b_df.iterrows():
                    table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                table_html += '</tbody></table>'
                st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("해당 기간에 조회된 대관 내역이 없습니다.")
