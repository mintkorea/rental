import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대(KST) 기준 오늘 날짜 계산
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 줄바꿈 허용 및 텍스트 크기 유연화
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: bold; color: #1E3A5F; margin-bottom: 15px; }
    
    .custom-table { 
        width: 100% !important; 
        border-collapse: collapse; 
        table-layout: fixed !important; 
    }
    
    .custom-table th { 
        background-color: #444 !important; color: white !important; 
        text-align: center !important; padding: 8px 2px; font-size: 13px;
        border: 1px solid #333;
    }
    
    .custom-table td { 
        background-color: white !important; color: black !important;
        border: 1px solid #eee; padding: 5px 2px !important; 
        font-size: 12.5px; /* 기본 폰트 살짝 조정 */
        vertical-align: middle; text-align: center;
        
        /* [중요] 글자 생략 방지 및 줄바꿈 설정 */
        white-space: normal !important; /* 자동 줄바꿈 허용 */
        word-break: keep-all; /* 단어 단위 줄바꿈으로 가독성 유지 */
        line-height: 1.2;
    }

    /* 행사명 및 장소, 부서는 왼쪽 정렬 권장 혹은 간격 유지 */
    .col-wrap { text-align: center !important; }
    .col-left { text-align: left !important; padding-left: 5px !important; }

    /* [너비 조정] 부서와 장소 비중 최적화 */
    .w-date   { width: 9%; }   
    .w-time   { width: 10%; }  
    .w-place  { width: 19%; }  /* 장소 확보 */
    .w-event  { width: 37%; }  /* 행사명 */
    .w-dept   { width: 17%; }  /* 부서 확보 */
    .w-status { width: 8%; }   

    @media (max-width: 768px) {
        .custom-table th, .custom-table td { font-size: 10.5px !important; padding: 4px 1px !important; }
        .pc-time { display: none; }
        .mobile-time { display: block; font-size: 9.5px; line-height: 1.1; }
        
        .w-date { width: 11%; }
        .w-time { width: 12%; }
        .w-status { width: 9%; }
    }
    
    @media (min-width: 769px) {
        .mobile-time { display: none; }
        .pc-time { display: block; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정
st.sidebar.header("🔍 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today, key="rental_start_final")
end_selected = st.sidebar.date_input("종료일", value=now_today, key="rental_end_final")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 로드
@st.cache_data(ttl=60)
def fetch_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return pd.DataFrame(res.json().get('res', []))
    except: return pd.DataFrame()

df = fetch_data(start_selected, end_selected)

# 5. 메인 출력
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({start_selected})</div>', unsafe_allow_html=True)

for bu in selected_bu:
    st.markdown(f"#### 🏢 {bu}")
    if not df.empty:
        target_df = df[df['buNm'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        
        if not target_df.empty:
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="w-date">날짜</th><th class="w-place">장소</th><th class="w-time">시간</th>'
            html += '<th class="w-event">행사명</th><th class="w-dept">부서</th><th class="w-status">상태</th>'
            html += '</tr></thead><tbody>'
            
            for _, r in target_df.iterrows():
                time_pc = f'<div class="pc-time">{r["startTime"]}~{r["endTime"]}</div>'
                time_mobile = f'<div class="mobile-time"><b>{r["startTime"]}</b><br>{r["endTime"]}</div>'
                
                html += f'<tr><td class="w-date">{r["startDt"][5:]}</td>'
                # [수정] 장소명 줄바꿈 적용
                html += f'<td class="w-place col-wrap">{r["placeNm"]}</td>'
                html += f'<td class="w-time">{time_pc}{time_mobile}</td>'
                html += f'<td class="col-left w-event">{r["eventNm"]}</td>'
                # [수정] 부서명 줄바꿈 적용
                html += f'<td class="w-dept col-wrap">{r["mgDeptNm"]}</td>'
                html += f'<td class="w-status">{"확정" if r["status"]=="Y" else "대기"}</td></tr>'
            
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; font-size:12px; padding-left:5px;">내역 없음</p>', unsafe_allow_html=True)

# 6. 엑셀 저장
if not df.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 결과 엑셀 저장", output.getvalue(), f"rental_{start_selected}.xlsx")
