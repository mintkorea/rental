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

# 2. CSS 설정
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
    }
    
    .custom-table td { 
        background-color: white !important; color: black !important;
        border: 1px solid #eee; padding: 5px 2px !important; 
        font-size: 12.5px; vertical-align: middle; text-align: center;
        line-height: 1.2;
    }

    /* 너비 비율 */
    .w-date   { width: 9%; }   
    .w-time   { width: 10%; }  
    .w-place  { width: 19%; }  
    .w-event  { width: 37%; }  
    .w-dept   { width: 17%; }  
    .w-status { width: 8%; }   

    /* 부서명/장소명 텍스트 처리 */
    .cell-content {
        display: -webkit-box;
        -webkit-line-clamp: 2; /* 2줄 제한 */
        -webkit-box-orient: vertical;
        overflow: hidden;
        word-break: break-all;
        white-space: normal;
    }

    @media (max-width: 768px) {
        .custom-table th, .custom-table td { font-size: 10px !important; padding: 4px 1px !important; }
        .pc-time { display: none; }
        .mobile-time { display: block; font-size: 9px; line-height: 1.0; }
        
        /* [핵심] 부서명과 장소명의 폰트를 더 줄여서 2줄 안에 최대한 수용 */
        .shrink-text {
            font-size: 8.5px !important; /* 텍스트 크기 강제 축소 */
            line-height: 1.0 !important;
            letter-spacing: -0.5px; /* 자간 축소 */
        }
        
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

# 3. 사이드바 (초기값 오늘 날짜 고정)
st.sidebar.header("🔍 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today, key="rental_v3_start")
end_selected = st.sidebar.date_input("종료일", value=now_today, key="rental_v3_end")

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
                # 장소/부서 공통으로 축소 로직 적용
                html += f'<td class="w-place"><div class="cell-content shrink-text">{r["placeNm"]}</div></td>'
                html += f'<td class="w-time">{time_pc}{time_mobile}</td>'
                html += f'<td style="text-align:left; padding-left:5px; white-space:normal; font-size:inherit;">{r["eventNm"]}</td>'
                html += f'<td class="w-dept"><div class="cell-content shrink-text">{r["mgDeptNm"]}</div></td>'
                html += f'<td class="w-status">{"확정" if r["status"]=="Y" else "대기"}</td></tr>'
            
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; font-size:11px; padding-left:5px;">내역 없음</p>', unsafe_allow_html=True)

# 6. 엑셀 저장
if not df.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", output.getvalue(), f"rental_{start_selected}.xlsx")
