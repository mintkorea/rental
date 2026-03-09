import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta
import pytz # 시간대 설정을 위해 추가

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대 설정 (서버 시간에 상관없이 오늘 날짜 정확히 계산)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date() 

# 2. CSS 설정: 여백을 0에 가깝게 줄이고 모바일 가로폭 고정
st.markdown(f"""
<style>
    .stApp {{ background-color: white; }}
    .block-container {{ padding: 0.5rem 0.3rem !important; }} /* 외부 여백 최소화 */
    
    .main-title {{ font-size: 17px !important; font-weight: bold; color: #1E3A5F; margin-bottom: 8px; }}
    .building-header {{
        font-size: 15px !important; font-weight: bold; color: #2E5077;
        margin-top: 12px; margin-bottom: 4px; border-left: 3px solid #2E5077; padding-left: 5px;
    }}
    
    /* 테이블 디자인: 여백 최소화 및 자동 줄바꿈 */
    .custom-table {{ 
        width: 100% !important; 
        table-layout: fixed !important; 
        border-collapse: collapse; 
        font-family: sans-serif;
    }}
    
    .custom-table th {{ 
        background-color: #333 !important; color: white !important; 
        text-align: center !important; font-size: 10px; padding: 3px 1px !important;
    }}
    
    .custom-table td {{ 
        background-color: white !important; color: black !important;
        border: 1px solid #ddd; 
        padding: 3px 1px !important; /* 셀 내부 여백 극최소화 */
        font-size: 10.5px; 
        vertical-align: middle;
        line-height: 1.1;
        text-align: center;
        word-break: break-all;
    }}

    /* 모바일 최적화 열 너비 비율 (%) */
    .col-date {{ width: 14%; }} 
    .col-place {{ width: 16%; }}
    .col-time {{ width: 15%; }}
    .col-event {{ width: 32%; text-align: left !important; padding-left: 2px !important; }}
    .col-dept {{ width: 13%; }}
    .col-status {{ width: 10%; }}
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 날짜 설정 (캐시를 타지 않도록 실시간 오늘 날짜를 기본값으로 사용)
st.sidebar.header("🔍 대관 조회 설정")
# key값을 날짜로 설정하여 날짜가 바뀔 때마다 컴포넌트가 새로고침되도록 유도
start_selected = st.sidebar.date_input("시작일", value=now_today, key=f"start_{now_today}")
end_selected = st.sidebar.date_input("종료일", value=now_today, key=f"end_{now_today}")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 로직 (캐시 무효화 기술 적용)
@st.cache_data(ttl=1) # 캐시 수명을 1초로 줄여 사실상 매번 새로고침
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            # 날짜 파싱 및 전개
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (str(curr.weekday() + 1) in allow):
                        rows.append({
                            '날짜': curr.strftime('%m-%d'), 
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': f"{item.get('startTime', '')}<br>~<br>{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'sort_key': f"{curr.isoformat()}{item.get('startTime', '')}"
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame()

df_all = get_data(start_selected, end_selected)

# 5. 결과 출력
st.markdown(f'<div class="main-title">🏫 대관 현황 ({start_selected.strftime("%Y-%m-%d")})</div>', unsafe_allow_html=True)

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not df_all.empty:
        bu_df = df_all[df_all['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by='sort_key')
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="col-date">날짜</th><th class="col-place">장소</th><th class="col-time">시간</th>'
            html += '<th class="col-event">행사명</th><th class="col-dept">부서</th><th class="col-status">상태</th>'
            html += '</tr></thead><tbody>'
            for _, r in bu_df.iterrows():
                html += f'<tr><td>{r["날짜"]}</td><td>{r["강의실"]}</td><td>{r["시간"]}</td>'
                html += f'<td class="col-event">{r["행사명"]}</td><td>{r["관리부서"]}</td><td>{r["상태"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:10px; color:#999; padding:5px;">내역 없음</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="font-size:10px; color:#999; padding:5px;">내역 없음</div>', unsafe_allow_html=True)

# 6. 다운로드 버튼
if not df_all.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", output.getvalue(), f"대관현황_{now_today}.xlsx")
