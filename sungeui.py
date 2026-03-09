import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대(KST) 기준 오늘 날짜 계산 (2026-03-10)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 레이아웃 복구 및 타이틀 강조
st.markdown("""
<style>
    .stApp { background-color: white; }
    
    /* 메인 타이틀 강조 (건물명보다 크게) */
    .main-title { 
        font-size: 26px !important; 
        font-weight: 800; 
        color: #002D56; 
        margin-bottom: 20px; 
        padding-bottom: 10px;
        border-bottom: 2px solid #f0f0f0;
    }
    
    /* 건물명 섹션 헤더 */
    .building-header {
        font-size: 19px !important; 
        font-weight: 700; 
        color: #2E5077;
        margin-top: 25px; 
        margin-bottom: 12px;
        display: flex;
        align-items: center;
    }

    /* 테이블 레이아웃 복구 */
    .custom-table { 
        width: 100% !important; 
        border-collapse: collapse; 
        table-layout: fixed !important; 
        margin-bottom: 20px;
    }
    .custom-table th { 
        background-color: #444 !important; 
        color: white !important; 
        font-size: 13px; 
        padding: 10px 2px;
        border: 1px solid #333;
    }
    .custom-table td { 
        border: 1px solid #eee; 
        padding: 8px 4px !important; 
        font-size: 13px; 
        vertical-align: middle; 
        line-height: 1.4;
        word-break: break-all; /* 긴 단어 줄바꿈 */
    }

    /* 열별 텍스트 정렬 및 너비 고정 */
    .t-center { text-align: center !important; }
    .t-left { text-align: left !important; padding-left: 8px !important; }

    .w-date { width: 8%; }
    .w-time { width: 11%; }
    .w-place { width: 18%; }
    .w-event { width: 38%; }
    .w-dept { width: 17%; }
    .w-status { width: 8%; }

    /* 모바일 최적화 */
    @media (max-width: 768px) {
        .main-title { font-size: 20px !important; }
        .building-header { font-size: 17px !important; }
        .custom-table td { font-size: 11px !important; padding: 5px 2px !important; }
        .pc-time { display: none; }
        .mobile-time { display: block; font-size: 10px; line-height: 1.1; font-weight: bold; }
        
        .w-date { width: 10%; }
        .w-time { width: 12%; }
        .w-status { width: 9%; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정 (초기 로드시 오늘 날짜 반영)
st.sidebar.header("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today, key="start_d")
end_selected = st.sidebar.date_input("종료일", value=now_today, key="end_d")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("조회 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 정제 및 정렬 로직 (이미지 d888bc 기반 정렬)
@st.cache_data(ttl=60)
def get_rental_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw_data = res.json().get('res', [])
        rows = []
        for item in raw_data:
            if not item.get('startDt') or not item.get('buNm'): continue
            
            # API 날짜 정보 파싱
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # 기간 내 모든 날짜 생성 (정렬을 위해)
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    rows.append({
                        'raw_date': curr, # 정렬용 기준
                        'raw_time': item.get('startTime', '00:00'), # 정렬용 시간
                        '날짜': curr.strftime('%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', ''),
                        '시작': item.get('startTime', ''),
                        '종료': item.get('endTime', ''),
                        '행사명': item.get('eventNm', ''),
                        '부서': item.get('mgDeptNm', ''),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        
        df = pd.DataFrame(rows)
        # 1. 날짜 순 2. 시간 순 정렬 (이미지 d888bc 요청사항 반영)
        if not df.empty:
            df = df.sort_values(by=['raw_date', 'raw_time'])
        return df
    except: return pd.DataFrame()

df_final = get_rental_data(start_selected, end_selected)

# 5. 메인 화면 출력
# 타이틀 기간 표시 (image_d88120 보완)
date_range = f"{start_selected}" if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({date_range})</div>', unsafe_allow_html=True)

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    if not df_final.empty:
        # 건물별 필터링 (공백 제거 후 비교)
        bu_df = df_final[df_final['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        
        if not bu_df.empty:
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="w-date">날짜</th><th class="w-time">시간</th><th class="w-place">장소</th>'
            html += '<th class="w-event">행사명</th><th class="w-dept">부서</th><th class="w-status">상태</th>'
            html += '</tr></thead><tbody>'
            
            for _, r in bu_df.iterrows():
                # 시간 표시 (PC 한 줄, 모바일 두 줄) - 중복 출력 방지
                time_str = f'{r["시작"]}~{r["종료"]}'
                time_html = f'<div class="pc-time">{time_str}</div>'
                time_html += f'<div class="mobile-time">{r["시작"]}<br>{r["종료"]}</div>'
                
                html += f'<tr><td class="w-date t-center">{r["날짜"]}</td>'
                html += f'<td class="w-time t-center">{time_html}</td>'
                html += f'<td class="w-place t-center">{r["장소"]}</td>'
                html += f'<td class="w-event t-left">{r["행사명"]}</td>'
                html += f'<td class="w-dept t-center">{r["부서"]}</td>'
                html += f'<td class="w-status t-center">{r["상태"]}</td></tr>'
            
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; font-size:12px; margin-left:10px;">조회 내역 없음</p>', unsafe_allow_html=True)

# 6. 엑셀 다운로드
if not df_final.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final.drop(columns=['raw_date', 'raw_time']).to_excel(writer, index=False)
    st.sidebar.download_button("📥 전체 일정 엑셀 저장", output.getvalue(), f"대관현황_{start_selected}.xlsx")
