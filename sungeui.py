import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대(KST) 기준 오늘 날짜 강제 설정
KST = pytz.timezone('Asia/Seoul')
now_kst = datetime.now(KST)
now_today = now_kst.date()

# 2. CSS 설정: 모바일 여백 극최소화 및 시간 열 레이아웃
st.markdown("""
<style>
    .stApp { background-color: white; }
    .block-container { padding: 0.5rem 0.2rem !important; } /* 여백 극최소화 */
    
    .main-title { font-size: 18px !important; font-weight: bold; color: #1E3A5F; margin-bottom: 10px; }
    .building-header {
        font-size: 16px !important; font-weight: bold; color: #2E5077;
        margin-top: 15px; margin-bottom: 5px; border-left: 3px solid #2E5077; padding-left: 6px;
    }
    
    /* 테이블 폭 고정 및 줄바꿈 강제 */
    .custom-table { 
        width: 100% !important; 
        table-layout: fixed !important; 
        border-collapse: collapse; 
    }
    
    .custom-table th { 
        background-color: #333 !important; color: white !important; 
        text-align: center !important; font-size: 11px; padding: 4px 1px !important;
    }
    
    .custom-table td { 
        background-color: white !important; color: black !important;
        border: 1px solid #ddd; 
        padding: 4px 1px !important; /* 셀 안 여백 최소화 */
        font-size: 11px; 
        vertical-align: middle;
        text-align: center;
        line-height: 1.2;
    }

    /* 열 너비 비율 최적화 */
    .col-date { width: 15%; }
    .col-place { width: 17%; }
    .col-time { width: 14%; font-weight: 500; } /* 시간 열 */
    .col-event { width: 30%; text-align: left !important; padding-left: 3px !important; word-break: break-all; }
    .col-dept { width: 14%; }
    .col-status { width: 10%; }

    /* 시간 표시용 스타일 (시작/끝 두 줄) */
    .time-start { color: #000; display: block; }
    .time-end { color: #666; display: block; border-top: 1px dashed #eee; margin-top: 2px; }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 (투데이 날짜 강제 적용)
st.sidebar.header("🔍 대관 조회")
# key에 현재 시간을 포함하여 매 접속 시마다 컴포넌트 강제 갱신
start_selected = st.sidebar.date_input("시작일", value=now_today, key=f"s_{now_kst.strftime('%H%M%S')}")
end_selected = st.sidebar.date_input("종료일", value=now_today, key=f"e_{now_kst.strftime('%H%M%S')}")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 데이터 로직 (캐시 TTL 0으로 설정하여 실시간성 확보)
@st.cache_data(ttl=0)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
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
                            '시작': item.get('startTime', ''),
                            '종료': item.get('endTime', ''),
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'sort': f"{curr.isoformat()}{item.get('startTime', '')}"
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

df_all = get_data(start_selected, end_selected)

# 5. 결과 출력
st.markdown(f'<div class="main-title">🏫 대관 현황 ({start_selected.strftime("%Y-%m-%d")})</div>', unsafe_allow_html=True)

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not df_all.empty:
        bu_df = df_all[df_all['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)]
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by='sort')
            html = '<table class="custom-table"><thead><tr>'
            html += '<th class="col-date">날짜</th><th class="col-place">장소</th><th class="col-time">시간</th>'
            html += '<th class="col-event">행사명</th><th class="col-dept">부서</th><th class="col-status">상태</th>'
            html += '</tr></thead><tbody>'
            for _, r in bu_df.iterrows():
                # 시간을 ~ 없이 두 줄로 구성
                time_html = f'<span class="time-start">{r["시작"]}</span><span class="time-end">{r["종료"]}</span>'
                html += f'<tr><td>{r["날짜"]}</td><td>{r["강의실"]}</td><td class="col-time">{time_html}</td>'
                html += f'<td class="col-event">{r["행사명"]}</td><td>{r["관리부서"]}</td><td>{r["상태"]}</td></tr>'
            html += '</tbody></table>'
            st.markdown(html, unsafe_allow_html=True)
        else:
            st.markdown('<div style="font-size:11px; color:#999; padding-left:5px;">내역 없음</div>', unsafe_allow_html=True)

# 6. 엑셀 다운로드
if not df_all.empty:
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_all.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", output.getvalue(), f"대관_{now_today}.xlsx")
