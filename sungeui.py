import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대(KST) 기준 오늘 날짜 계산
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 중복 노출 방지 핵심 로직
st.markdown("""
<style>
    .stApp { background-color: white; }
    
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 20px; }
    .building-header { font-size: 19px !important; font-weight: 700; color: #2E5077; margin-top: 25px; }

    .custom-table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 13px; padding: 10px 2px; }
    .custom-table td { border: 1px solid #eee; padding: 8px 4px !important; font-size: 13px; vertical-align: middle; line-height: 1.4; }

    /* [해결책] 디스플레이 설정 강제화 */
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }

    .t-center { text-align: center !important; }
    .t-left { text-align: left !important; padding-left: 8px !important; }

    .w-date { width: 8%; }
    .w-time { width: 12%; }
    .w-place { width: 18%; }
    .w-event { width: 37%; }
    .w-dept { width: 17%; }
    .w-status { width: 8%; }

    /* 모바일 환경에서만 PC 시간을 숨기고 모바일 시간을 보여줌 */
    @media (max-width: 768px) {
        .pc-time { display: none !important; }
        .mobile-time { display: block !important; font-size: 10px; font-weight: bold; line-height: 1.1; }
        .custom-table td { font-size: 11px !important; }
        .w-date { width: 11%; }
        .w-time { width: 13%; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정
st.sidebar.header("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("조회 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 로직 (정렬 순서: 날짜 -> 시간)
@st.cache_data(ttl=60)
def get_clean_data(s_date, e_date):
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
                        'raw_date': curr,
                        'raw_time': item.get('startTime', '00:00'),
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
        if not df.empty:
            df = df.sort_values(by=['raw_date', 'raw_time'])
        return df
    except: return pd.DataFrame()

df_final = get_clean_data(start_selected, end_selected)

# 5. 메인 출력
date_range = f"{start_selected}" if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({date_range})</div>', unsafe_allow_html=True)

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    if not df_final.empty:
        bu_df = df_final[df_final['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        
        if not bu_df.empty:
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="w-date">날짜</th><th class="w-time">시간</th><th class="w-place">장소</th>'
            html += '<th class="w-event">행사명</th><th class="w-dept">부서</th><th class="w-status">상태</th>'
            html += '</tr></thead><tbody>'
            
            for _, r in bu_df.iterrows():
                # [수정] HTML 구조 단순화하여 중복 렌더링 방지
                time_html = f'''
                <div class="pc-time">{r["시작"]} ~ {r["종료"]}</div>
                <div class="mobile-time">{r["시작"]}<br>{r["종료"]}</div>
                '''
                
                html += f'<tr><td class="w-date t-center">{r["날짜"]}</td>'
                html += f'<td class="w-time t-center">{time_html}</td>'
                html += f'<td class="w-place t-center">{r["장소"]}</td>'
                html += f'<td class="w-event t-left">{r["행사명"]}</td>'
                html += f'<td class="w-dept t-center">{r["부서"]}</td>'
                html += f'<td class="w-status t-center">{r["상태"]}</td></tr>'
            
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<p style="color:#999; font-size:12px; margin-left:10px;">내역 없음</p>', unsafe_allow_html=True)

# 6. 다운로드 버튼
if not df_final.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final.drop(columns=['raw_date', 'raw_time']).to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", output.getvalue(), f"rental_{start_selected}.xlsx")
