import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

# 1. 페이지 설정: 확대/축소 가능하도록 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 고정된 건물 순서
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 설정: 다크 모드 방지 및 모바일 가독성 확보
st.markdown("""
<style>
    /* 다크 모드에서도 배경은 흰색, 글자는 검은색으로 고정 */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: white !important;
        color: black !important;
    }
    
    .main-title { font-size: 24px !important; font-weight: bold; margin-bottom: 20px; color: #1E3A5F; }
    
    /* 테이블 레이아웃 최적화 */
    .table-wrapper { width: 100%; overflow-x: auto; margin-bottom: 30px; }
    .custom-table { width: 100%; border-collapse: collapse; min-width: 700px; border: 1px solid #ddd; }
    
    /* 헤더 중앙 정렬 및 색상 고정 */
    .custom-table th { 
        background-color: #333333 !important; color: #ffffff !important; 
        text-align: center !important; font-weight: bold; padding: 12px 5px; border: 1px solid #444;
    }
    
    /* 셀 데이터 색상 고정 */
    .custom-table td { 
        background-color: #ffffff !important; color: #000000 !important; 
        border: 1px solid #eee; padding: 10px 8px !important; font-size: 14px; vertical-align: middle !important;
    }

    /* 열 너비 강제 지정 */
    .col-date { width: 110px; text-align: center !important; }
    .col-place { width: 15%; }
    .col-time { width: 120px; text-align: center !important; }
    .col-event { width: auto; min-width: 200px; } /* 행사명 넓게 확보 */
    .col-dept { width: 15%; }
    .col-status { width: 85px; text-align: center !important; }

    @media (max-width: 768px) {
        .custom-table td, .custom-table th { font-size: 12px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정 (달력 기본값: 오늘)
st.sidebar.header("🔍 기간 설정")
today = date.today()
start_date = st.sidebar.date_input("시작일", value=today) # 오늘 날짜 기본값
end_date = st.sidebar.date_input("종료일", value=today)   # 오늘 날짜 기본값
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 타이틀 표시
display_date = start_date.strftime('%Y-%m-%d') if start_date == end_date else f"{start_date} ~ {end_date}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({display_date})</div>', unsafe_allow_html=True)

# 4. 데이터 로드 및 처리
@st.cache_data(ttl=300)
def fetch_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date, "end": e_date}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        data = res.json().get('res', [])
        rows = []
        for item in data:
            # 기간 내 모든 날짜 전개
            curr = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            last = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            while curr <= last:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (str(curr.weekday() + 1) in allow):
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': f"{item['startTime']} ~ {item['endTime']}",
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '예약확정' if item.get('status') == 'Y' else '신청대기',
                            'raw_start': item['startTime']
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

df = fetch_data(start_date, end_date)

# 5. 결과 출력 (HTML 노출 방지를 위해 st.markdown 내부에서 루프 처리)
export_data = []
for bu in selected_bu:
    st.markdown(f"### 🏢 {bu}")
    if not df.empty:
        bu_df = df[df['건물명'].str.contains(bu.replace(" ", ""), na=False)].sort_values(['날짜', 'raw_start'])
        if not bu_df.empty:
            # HTML 테이블 직접 조립
            table_html = f'<div class="table-wrapper"><table class="custom-table"><thead><tr>'
            table_html += '<th class="col-date">날짜</th><th class="col-place">강의실</th>'
            table_html += '<th class="col-time">시간</th><th class="col-event">행사명</th>'
            table_html += '<th class="col-dept">관리부서</th><th class="col-status">상태</th></tr></thead><tbody>'
            
            for _, r in bu_df.iterrows():
                table_html += f'<tr><td style="text-align:center;">{r["날짜"]}</td>'
                table_html += f'<td>{r["강의실"]}</td><td style="text-align:center;">{r["시간"]}</td>'
                table_html += f'<td>{r["행사명"]}</td><td>{r["관리부서"]}</td>'
                table_html += f'<td style="text-align:center;">{r["상태"]}</td></tr>'
            
            table_html += '</tbody></table></div>'
            st.markdown(table_html, unsafe_allow_html=True) # 여기서 HTML 렌더링
            export_data.append(bu_df)
        else:
            st.write("대관 내역이 없습니다.")
    else:
        st.write("대관 내역이 없습니다.")

# 6. 엑셀 다운로드
if export_data:
    final_df = pd.concat(export_data).drop(columns=['raw_start'])
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀 저장", output.getvalue(), f"대관현황_{today}.xlsx")
