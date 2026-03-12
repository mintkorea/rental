import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 줌 기능 강제 활성화 및 표 디자인 (CSS)
st.markdown("""
<style>
    /* 브라우저에게 확대를 허용하도록 강제 명령 */
    @viewport { width: device-width; zoom: 1.0; user-scalable=yes; }
    
    /* 전체 폰트 크기 및 터치 조작 허용 */
    html, body { 
        touch-action: manipulation !important; 
        -ms-touch-action: manipulation !important;
    }

    .main-title { font-size: 22px; font-weight: 800; text-align: center; }
    .date-header { font-size: 18px; font-weight: 800; padding: 10px; margin-top: 20px; border-bottom: 2px solid #eee; }
    .date-sat { color: #007BFF; }
    .date-sun { color: #FF0000; }

    /* 표 레이아웃: 가로 스크롤을 유지하면서 찌그러짐 방지 */
    .scroll-container { width: 100%; overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
    
    .custom-table { 
        width: 100% !important; 
        min-width: 900px !important; /* 표가 이 너비 아래로 절대 줄어들지 않음 */
        border-collapse: collapse; 
        table-layout: fixed !important; 
    }
    
    .custom-table th, .custom-table td { 
        border: 1px solid #ddd; 
        padding: 8px 4px; 
        text-align: center; 
        font-size: 13px; 
        word-break: break-all; 
    }

    /* 열 너비 고정: 요청하신 대로 시간 필드를 장소보다 작게 설정 */
    .c-place { width: 110px; }  /* 장소 */
    .c-time  { width: 85px; }   /* 시간 (고정) */
    .c-event { width: auto; }   /* 행사명 (남는 공간 다 차지) */
    .c-count { width: 45px; }   /* 인원 */
    .c-dept  { width: 110px; }  /* 부서 */
    .c-stat  { width: 50px; }   /* 상태 */

    .ov-text { line-height: 1.3; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (성공했던 로직 유지)
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

# 4. 메인 화면
s_date = st.sidebar.date_input("시작일", now_today)
e_date = st.sidebar.date_input("종료일", s_date + timedelta(days=7))
target_bu = st.sidebar.multiselect("건물 필터", BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(s_date, e_date)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        w_num = day_df.iloc[0]['w_num']
        c_class = "date-sat" if w_num == 5 else ("date-sun" if w_num == 6 else "")
        st.markdown(f'<div class="date-header {c_class}">📅 {date} ({day_df.iloc[0]["요일"]})</div>', unsafe_allow_html=True)
        
        for bu in target_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.write(f"🏢 **{bu}**")
                
                html = f"""
                <div class="scroll-container">
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th class="c-place">장소</th>
                                <th class="c-time">시간</th>
                                <th class="c-event">행사명</th>
                                <th class="c-count">인원</th>
                                <th class="c-dept">부서</th>
                                <th class="c-stat">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, r in bu_df.iterrows():
                    html += f"""
                        <tr>
                            <td><div class="ov-text">{r['장소']}</div></td>
                            <td>{r['시간']}</td>
                            <td style="text-align:left;"><div class="ov-text">{r['행사명']}</div></td>
                            <td>{r['인원']}</td>
                            <td><div class="ov-text">{r['부서']}</div></td>
                            <td>{r['상태']}</td>
                        </tr>
                    """
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)
else:
    st.info("조회된 데이터가 없습니다.")
