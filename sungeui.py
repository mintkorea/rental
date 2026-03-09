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

# 2. CSS 설정: 타이틀 크기 역전 및 테이블 가독성 강화
st.markdown("""
<style>
    .stApp { background-color: white; }
    
    /* [수정] 메인 타이틀을 건물명보다 확실히 크게 설정 */
    .main-title { 
        font-size: 28px !important; 
        font-weight: 800; 
        color: #002D56; 
        margin-bottom: 25px; 
        border-bottom: 2px solid #eee;
        padding-bottom: 10px;
    }
    
    /* 건물명 섹션 헤더 크기 조정 */
    .building-header {
        font-size: 18px !important; 
        font-weight: 700; 
        color: #2E5077;
        margin-top: 30px; 
        margin-bottom: 10px;
    }

    .custom-table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 13px; padding: 10px 2px; }
    .custom-table td { border: 1px solid #eee; padding: 6px 4px; font-size: 13px; vertical-align: middle; line-height: 1.3; }

    /* 열 너비 설정 */
    .w-date { width: 9%; text-align: center; }
    .w-time { width: 11%; text-align: center; }
    .w-place { width: 18%; text-align: center; }
    .w-event { width: 37%; text-align: left; }
    .w-dept { width: 17%; text-align: center; }
    .w-status { width: 8%; text-align: center; }

    @media (max-width: 768px) {
        .main-title { font-size: 20px !important; }
        .building-header { font-size: 16px !important; }
        .custom-table td { font-size: 11px !important; }
        .pc-time { display: none; }
        .mobile-time { display: block; font-size: 10px; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 (초기 로드시 오늘 날짜 자동 반영)
st.sidebar.header("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today, key="st_date")
end_selected = st.sidebar.date_input("종료일", value=now_today, key="en_date")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("조회 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 로직 (정렬 및 이상 데이터 필터링)
@st.cache_data(ttl=60)
def get_clean_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            # 1단계: 빈 데이터나 잘못된 형식 필터링
            if not item.get('startDt') or not item.get('buNm'): continue
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    # 장기 대관일 경우 해당 요일만 포함 (단일일은 무조건 포함)
                    if (item['startDt'] == item['endDt']) or (not allow) or (str(curr.weekday() + 1) in allow):
                        rows.append({
                            'raw_date': curr, # 정렬용
                            '날짜': curr.strftime('%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''),
                            '시작': item.get('startTime', '00:00'),
                            '종료': item.get('endTime', '00:00'),
                            '행사명': item.get('eventNm', ''),
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        
        # [정렬 핵심] 날짜 -> 시간 -> 건물명 순으로 정렬
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by=['raw_date', '시작', '건물명'])
        return df
    except: return pd.DataFrame()

processed_df = get_clean_data(start_selected, end_selected)

# 5. 결과 렌더링
# 타이틀에 조회 기간 명시 및 크기 강조
date_range_str = f"{start_selected}" if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({date_range_str})</div>', unsafe_allow_html=True)

# 건물별 섹션 출력 (선택된 건물이 있을 경우만)
for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    if not processed_df.empty:
        # 현재 건물 데이터만 필터링 (정렬은 이미 위에서 완료됨)
        bu_df = processed_df[processed_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        
        if not bu_df.empty:
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="w-date">날짜</th><th class="w-time">시간</th><th class="w-place">장소</th>'
            html += '<th class="w-event">행사명</th><th class="w-dept">부서</th><th class="w-status">상태</th>'
            html += '</tr></thead><tbody>'
            
            for _, r in bu_df.iterrows():
                time_pc = f'<div class="pc-time">{r["시작"]}~{r["종료"]}</div>'
                time_mobile = f'<div class="mobile-time"><b>{r["시작"]}</b><br>{r["종료"]}</div>'
                
                html += f'<tr><td class="w-date">{r["날짜"]}</td>'
                html += f'<td class="w-time">{time_pc}{time_mobile}</td>'
                html += f'<td class="w-place">{r["장소"]}</td>'
                html += f'<td class="w-event">{r["행사명"]}</td>'
                html += f'<td class="w-dept">{r["부서"]}</td>'
                html += f'<td class="w-status">{r["상태"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; font-size:12px; padding-left:10px;">해당 기간 내 대관 내역이 없습니다.</p>', unsafe_allow_html=True)

# 6. 다운로드 버튼
if not processed_df.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        processed_df.drop(columns=['raw_date']).to_excel(writer, index=False)
    st.sidebar.download_button("📥 전체 일정 엑셀 저장", output.getvalue(), f"rental_report_{now_today}.xlsx")
