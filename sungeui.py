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

# 2. CSS 설정 (PC와 모바일 가독성 동시 확보)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 24px !important; font-weight: bold; color: #1E3A5F; margin-bottom: 20px; }
    
    /* 테이블 기본 스타일 */
    .custom-table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; }
    .custom-table th { 
        background-color: #333 !important; color: white !important; 
        text-align: center !important; padding: 10px 5px; font-size: 14px;
    }
    .custom-table td { 
        background-color: white !important; color: black !important;
        border: 1px solid #ddd; padding: 8px 5px !important; 
        font-size: 14px; vertical-align: middle; text-align: center;
    }

    /* 행사명 열은 왼쪽 정렬 */
    .col-event { text-align: left !important; padding-left: 10px !important; overflow: hidden; text-overflow: ellipsis; }

    /* 모바일 환경 (화면 폭 768px 이하) 대응 */
    @media (max-width: 768px) {
        .custom-table th, .custom-table td { font-size: 11px !important; padding: 4px 2px !important; }
        .pc-time { display: none; } /* PC용 시간 숨김 */
        .mobile-time { display: block; font-size: 10px; line-height: 1.2; } /* 모바일용 시간 보임 */
        .main-title { font-size: 18px !important; }
    }
    
    /* PC 환경 대응 */
    @media (min-width: 769px) {
        .mobile-time { display: none; } /* 모바일용 시간 숨김 */
        .pc-time { display: block; } /* PC용 시간 보임 */
    }

    /* 열 너비 설정 */
    .w-date { width: 12%; }
    .w-place { width: 13%; }
    .w-time { width: 15%; }
    .w-event { width: 35%; }
    .w-dept { width: 15%; }
    .w-status { width: 10%; }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 (날짜 설정 - 초기값은 오늘, 이후 변경 가능)
st.sidebar.header("🔍 대관 조회")
# key를 고정하여 매번 날짜가 리셋되는 현상 방지
start_selected = st.sidebar.date_input("시작일", value=now_today, key="fixed_start")
end_selected = st.sidebar.date_input("종료일", value=now_today, key="fixed_end")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 로드 로직
@st.cache_data(ttl=300)
def get_rental_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = res.json().get('res', [])
        return pd.DataFrame(data)
    except: return pd.DataFrame()

raw_df = get_rental_data(start_selected, end_selected)

# 5. 결과 렌더링
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({start_selected})</div>', unsafe_allow_html=True)

for bu in selected_bu:
    st.markdown(f"### 🏢 {bu}")
    if not raw_df.empty:
        # 데이터 필터링 및 전개 로직 (상세 생략, 핵심 출력부 집중)
        bu_df = raw_df[raw_df['buNm'].str.contains(bu.replace(" ",""), na=False)]
        
        if not bu_df.empty:
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="w-date">날짜</th><th class="w-place">장소</th><th class="w-time">시간</th>'
            html += '<th class="w-event">행사명</th><th class="w-dept">부서</th><th class="w-status">상태</th></tr></thead><tbody>'
            
            for _, r in bu_df.iterrows():
                # PC용 시간 (한 줄) / 모바일용 시간 (두 줄, ~ 없음)
                time_pc = f'<div class="pc-time">{r["startTime"]} ~ {r["endTime"]}</div>'
                time_mobile = f'<div class="mobile-time"><b>{r["startTime"]}</b><br>{r["endTime"]}</div>'
                
                html += f'<tr><td>{r["startDt"][5:]}</td><td>{r["placeNm"]}</td>'
                html += f'<td>{time_pc}{time_mobile}</td>'
                html += f'<td class="col-event">{r["eventNm"]}</td><td>{r["mgDeptNm"]}</td>'
                html += f'<td>{"확정" if r["status"]=="Y" else "대기"}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.write("대관 내역이 없습니다.")

# 6. 엑셀 저장 버튼
if not raw_df.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        raw_df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 결과 저장", output.getvalue(), f"대관현황_{now_today}.xlsx")
