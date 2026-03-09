import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 고정된 건물 순서
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 설정: 여백 극최소화 및 가로 스크롤 완전 차단
st.markdown("""
<style>
    .stApp { background-color: white; }
    .block-container { padding: 1rem 0.5rem !important; } /* 전체 여백 축소 */
    
    .main-title { font-size: 18px !important; font-weight: bold; color: #1E3A5F; margin-bottom: 10px; }
    .building-header {
        font-size: 16px !important; font-weight: bold; color: #2E5077;
        margin-top: 15px; margin-bottom: 5px; border-left: 3px solid #2E5077; padding-left: 6px;
    }
    
    /* 테이블 가로 폭 고정 및 줄바꿈 강제 */
    .custom-table { 
        width: 100% !important; 
        table-layout: fixed !important; 
        border-collapse: collapse; 
        word-break: break-all;
    }
    
    .custom-table th { 
        background-color: #333 !important; color: white !important; 
        text-align: center !important; font-size: 11px; padding: 4px 1px !important;
    }
    
    .custom-table td { 
        background-color: white !important; color: black !important;
        border: 1px solid #ddd; 
        padding: 4px 2px !important; /* 셀 여백 극최소화 */
        font-size: 11px; 
        vertical-align: middle;
        line-height: 1.1;
    }

    /* 모바일 환경 최적화 열 너비 */
    .col-date { width: 15%; }    /* 날짜 (MM-DD) */
    .col-place { width: 17%; }   /* 장소 */
    .col-time { width: 15%; }    /* 시간 */
    .col-event { width: 30%; }   /* 행사명 */
    .col-dept { width: 13%; }    /* 부서 */
    .col-status { width: 10%; }  /* 상태 */
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정 (매번 실행 시마다 오늘 날짜 계산)
st.sidebar.header("🔍 설정")
# 캐시 문제 방지를 위해 실시간 오늘 날짜 호출
now_today = datetime.now().date() 

# 날짜 입력 기본값을 오늘로 강제 고정
start_selected = st.sidebar.date_input("시작일", value=now_today, key="start_date")
end_selected = st.sidebar.date_input("종료일", value=now_today, key="end_date")
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 타이틀 표시 (선택된 날짜를 즉각 반영)
display_title = start_selected.strftime('%Y-%m-%d') if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({display_title})</div>', unsafe_allow_html=True)

# 4. 데이터 로직 (캐시 TTL 단축하여 실시간성 강화)
@st.cache_data(ttl=60) # 1분마다 자동 갱신
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.strftime('%Y-%m-%d'), "end": e_date.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            # 날짜별 데이터 전개 로직 (중복 제거 및 기간 필터 포함)
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (str(curr.weekday() + 1) in allow):
                        rows.append({
                            '날짜': curr.strftime('%m-%d'), # 연도 제외하여 공간 확보
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': f"{item.get('startTime', '')}<br>~<br>{item.get('endTime', '')}", # 세로 배치
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'sort_val': f"{curr.strftime('%Y%m%d')}{item.get('startTime', '')}"
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

df_all = get_data(start_selected, end_selected)

# 5. 결과 출력
for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not df_all.empty:
        bu_df = df_all[df_all['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by='sort_val')
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="col-date">날짜</th><th class="col-place">장소</th><th class="col-time">시간</th>'
            html += '<th class="col-event">행사명</th><th class="col-dept">부서</th><th class="col-status">상태</th>'
            html += '</tr></thead><tbody>'
            for _, r in bu_df.iterrows():
                html += f'<tr><td style="text-align:center;">{r["날짜"]}</td>'
                html += f'<td style="text-align:center;">{r["강의실"]}</td>'
                html += f'<td style="text-align:center;">{r["시간"]}</td>'
                html += f'<td>{r["행사명"]}</td><td>{r["관리부서"]}</td>'
                html += f'<td style="text-align:center;">{r["상태"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:11px; color:#999; padding-left:5px;">내역 없음</div>', unsafe_allow_html=True)

# 6. 엑셀 저장
if not df_all.empty:
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", output.getvalue(), f"대관현황_{now_today}.xlsx")
