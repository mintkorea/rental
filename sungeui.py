import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대(KST) 기준 오늘 날짜 계산 (2026-03-10)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 셀 너비 비율 재조정 및 가독성 강화
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: bold; color: #1E3A5F; margin-bottom: 15px; }
    
    /* 테이블 레이아웃: Fixed 설정으로 너비 강제 제어 */
    .custom-table { 
        width: 100% !important; 
        border-collapse: collapse; 
        table-layout: fixed !important; 
    }
    
    /* 헤더 스타일 */
    .custom-table th { 
        background-color: #444 !important; color: white !important; 
        text-align: center !important; padding: 8px 2px; font-size: 13px;
        border: 1px solid #333;
    }
    
    /* 셀 데이터 스타일 */
    .custom-table td { 
        background-color: white !important; color: black !important;
        border: 1px solid #eee; padding: 6px 2px !important; 
        font-size: 13px; vertical-align: middle; text-align: center;
        overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }

    /* 행사명은 내용이 많으므로 줄바꿈 허용 */
    .col-event { text-align: left !important; padding-left: 8px !important; white-space: normal !important; word-break: break-all; }

    /* [너비 조정 핵심] 열 너비 비율 재설정 (총합 100%) */
    .w-date   { width: 9%; }   /* 날짜: 극최소화 */
    .w-time   { width: 10%; }  /* 시간: 장소보다 좁게 설정 */
    .w-place  { width: 18%; }  /* 장소: 넓게 보강 */
    .w-event  { width: 40%; }  /* 행사명: 가장 넓게 */
    .w-dept   { width: 15%; }  /* 부서: 적정 유지 */
    .w-status { width: 8%; }   /* 상태: 최소화 */

    /* 모바일 대응 (768px 이하) */
    @media (max-width: 768px) {
        .custom-table th, .custom-table td { font-size: 11px !important; padding: 4px 1px !important; }
        .pc-time { display: none; }
        .mobile-time { display: block; font-size: 10px; line-height: 1.1; }
        
        /* 모바일에서는 장소와 행사명 비중을 더 높임 */
        .w-date { width: 11%; }
        .w-time { width: 12%; }
        .w-status { width: 9%; }
    }
    
    /* PC 대응 */
    @media (min-width: 769px) {
        .mobile-time { display: none; }
        .pc-time { display: block; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 날짜 설정 (초기값: 오늘 2026-03-10)
st.sidebar.header("🔍 조회 설정")
# key값을 고정하여 날짜 변경 시 리셋 방지
start_selected = st.sidebar.date_input("시작일", value=now_today, key="rental_start_fixed")
end_selected = st.sidebar.date_input("종료일", value=now_today, key="rental_end_fixed")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 처리 함수 (TTL을 짧게 유지하여 실시간성 확보)
@st.cache_data(ttl=60)
def fetch_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        return pd.DataFrame(res.json().get('res', []))
    except: return pd.DataFrame()

df = fetch_data(start_selected, end_selected)

# 5. 메인 화면 출력
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({start_selected})</div>', unsafe_allow_html=True)

for bu in selected_bu:
    st.markdown(f"#### 🏢 {bu}")
    if not df.empty:
        # 건물명 필터링 (공백 제거 후 비교)
        target_df = df[df['buNm'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        
        if not target_df.empty:
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="w-date">날짜</th><th class="w-place">장소</th><th class="w-time">시간</th>'
            html += '<th class="w-event">행사명</th><th class="w-dept">부서</th><th class="w-status">상태</th>'
            html += '</tr></thead><tbody>'
            
            for _, r in target_df.iterrows():
                # 시간 표시 최적화 (PC는 한 줄, 모바일은 두 줄)
                time_pc = f'<div class="pc-time">{r["startTime"]}~{r["endTime"]}</div>'
                time_mobile = f'<div class="mobile-time"><b>{r["startTime"]}</b><br>{r["endTime"]}</div>'
                
                html += f'<tr><td class="w-date">{r["startDt"][5:]}</td>'
                html += f'<td class="w-place">{r["placeNm"]}</td>'
                html += f'<td class="w-time">{time_pc}{time_mobile}</td>'
                html += f'<td class="col-event w-event">{r["eventNm"]}</td>'
                html += f'<td class="w-dept">{r["mgDeptNm"]}</td>'
                html += f'<td class="w-status">{"확정" if r["status"]=="Y" else "대기"}</td></tr>'
            
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; font-size:12px; padding-left:5px;">조회된 내역이 없습니다.</p>', unsafe_allow_html=True)

# 6. 엑셀 저장
if not df.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 결과 엑셀 저장", output.getvalue(), f"rental_{start_selected}.xlsx")
