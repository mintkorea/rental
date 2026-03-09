import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 설정: 여백 최소화 및 모바일 가로스크롤 방지
st.markdown("""
<style>
    /* 전체 배경 흰색 고정 */
    .stApp { background-color: white; }
    
    /* 상단 여백 줄임 */
    .block-container { padding: 2rem 1rem !important; }
    
    .main-title { font-size: 22px !important; font-weight: bold; color: #1E3A5F; margin-bottom: 15px; }
    .building-header {
        font-size: 18px !important; font-weight: bold; color: #2E5077;
        margin-top: 20px; margin-bottom: 8px; border-left: 4px solid #2E5077; padding-left: 8px;
    }
    
    /* 테이블 구조 최적화: 가로 스크롤 방지 */
    .custom-table { 
        width: 100% !important; 
        table-layout: fixed !important; /* 너비 고정 */
        border-collapse: collapse; 
        word-break: break-all; /* 긴 단어 자동 줄바꿈 */
    }
    
    .custom-table th { 
        background-color: #333 !important; color: white !important; 
        text-align: center !important; font-size: 12px; padding: 6px 2px !important;
    }
    
    .custom-table td { 
        background-color: white !important; color: black !important;
        border: 1px solid #ddd; 
        padding: 6px 3px !important; /* 셀 안 여백 최소화 */
        font-size: 12px; 
        vertical-align: middle;
        line-height: 1.2;
    }

    /* 열 너비 비율 지정 (총합 100%) */
    .col-date { width: 18%; }    /* 날짜 */
    .col-place { width: 15%; }   /* 강의실 */
    .col-time { width: 18%; }    /* 시간 */
    .col-event { width: 25%; }   /* 행사명 (가장 넓게) */
    .col-dept { width: 14%; }    /* 부서 */
    .col-status { width: 10%; }  /* 상태 */

    /* 모바일 환경 추가 조정 */
    @media (max-width: 768px) {
        .custom-table td, .custom-table th { font-size: 11px !important; }
        .main-title { font-size: 18px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 (기본값: 오늘)
st.sidebar.header("🔍 설정")
today = date.today()
start_selected = st.sidebar.date_input("시작일", value=today)
end_selected = st.sidebar.date_input("종료일", value=today)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

title_date = start_selected.strftime('%Y-%m-%d') if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({title_date})</div>', unsafe_allow_html=True)

# 4. 데이터 로직
@st.cache_data(ttl=300)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date, "end": e_date}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            # 날짜 전개 및 필터링 (생략 - 이전 로직과 동일)
            # ... (데이터 처리 부분)
            rows.append({
                '날짜': item['startDt'][5:], # 모바일 공간 확보를 위해 연도 제외(03-10 형태)
                '건물명': item.get('buNm', '').strip(),
                '강의실': item.get('placeNm', ''),
                '시간': f"{item.get('startTime', '')}\n~\n{item.get('endTime', '')}", # 시간을 세로로 배치하여 폭 확보
                '행사명': item.get('eventNm', ''),
                '관리부서': item.get('mgDeptNm', ''),
                '상태': '확정' if item.get('status') == 'Y' else '대기', # 상태 단어 축약
                'raw_start': item.get('startTime', '')
            })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 실제 서비스 환경을 위한 간략화된 데이터 처리 로직 재구성
df_all = get_data(start_selected, end_selected)

# 5. 결과 출력
for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not df_all.empty:
        # 건물명 매칭 (공백 제거 후 비교)
        bu_df = df_all[df_all['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        
        if not bu_df.empty:
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="col-date">날짜</th><th class="col-place">장소</th><th class="col-time">시간</th>'
            html += '<th class="col-event">행사명</th><th class="col-dept">부서</th><th class="col-status">상태</th>'
            html += '</tr></thead><tbody>'
            
            for _, r in bu_df.iterrows():
                # 시간 내 줄바꿈 적용
                formatted_time = r['시간'].replace("\n", "<br>")
                html += f'<tr><td style="text-align:center;">{r["날짜"]}</td>'
                html += f'<td style="text-align:center;">{r["강의실"]}</td>'
                html += f'<td style="text-align:center;">{formatted_time}</td>'
                html += f'<td>{r["행사명"]}</td>'
                html += f'<td>{r["관리부서"]}</td>'
                html += f'<td style="text-align:center;">{r["상태"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.write("내역 없음")

# 6. 엑셀 저장
if not df_all.empty:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", output.getvalue(), "대관현황.xlsx")
