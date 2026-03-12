import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (가장 상단에 위치)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. CSS 설정 (줌 활성화 및 표 규격 강제 고정)
st.markdown("""
<style>
    /* 줌 및 모바일 가로스크롤 허용 */
    html, body { zoom: 100% !important; touch-action: auto !important; }
    
    /* 제목 및 요일 스타일 */
    .main-title { font-size: 22px; font-weight: 800; text-align: center; }
    .date-header { font-size: 18px; font-weight: 800; padding: 10px; margin-top: 20px; border-bottom: 2px solid #eee; }
    .date-sat { color: #007BFF; }
    .date-sun { color: #FF0000; }
    
    /* 표 레이아웃: 장소보다 시간을 작게, 모바일에서도 찌그러지지 않게 */
    .report-table { width: 100%; min-width: 800px; border-collapse: collapse; table-layout: fixed; }
    .report-table th, .report-table td { border: 1px solid #ddd; padding: 6px 2px; text-align: center; font-size: 13px; }
    
    /* 너비 고정: 장소(15%), 시간(85px 고정), 행사명(40%) */
    .col-place { width: 15%; }
    .col-time  { width: 85px; } 
    .col-event { width: 40%; }
    .col-count { width: 40px; }
    .col-dept  { width: 20%; }
    .col-status { width: 45px; }

    .ov-text { overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.2; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (성공했던 로직 그대로)
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

# 4. 화면 출력
st.sidebar.title("설정")
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
                # 가로 스크롤을 위한 div 감싸기
                html = '<div style="overflow-x:auto;"><table class="report-table"><thead><tr>'
                html += '<th class="col-place">장소</th><th class="col-time">시간</th><th class="col-event">행사명</th>'
                html += '<th class="col-count">인원</th><th class="col-dept">부서</th><th class="col-status">상태</th></tr></thead><tbody>'
                
                for _, r in bu_df.iterrows():
                    html += f"<tr><td><div class='ov-text'>{r['장소']}</div></td><td>{r['시간']}</td>"
                    html += f"<td style='text-align:left;'><div class='ov-text'>{r['행사명']}</div></td>"
                    html += f"<td>{r['인원']}</td><td><div class='ov-text'>{r['부서']}</div></td><td>{r['상태']}</td></tr>"
                html += "</tbody></table></div>"
                st.markdown(html, unsafe_allow_html=True)
else:
    st.info("데이터가 없습니다.")
