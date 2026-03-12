import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정 (표 디자인 및 열 너비 강제 고정)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 5px; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 10px 0; margin-top: 30px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 15px; margin-bottom: 5px; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    /* 표 레이아웃 수정 */
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 750px; table-layout: fixed; margin-bottom: 15px; }
    th, td { border: 1px solid #ddd; padding: 10px 4px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }
    th { background-color: #f8f9fa; font-weight: bold; color: #333; }
    
    /* 열 너비 강제 고정 (시간 필드를 슬림하게) */
    .col-place { width: 110px; }
    .col-time  { width: 85px; }   /* 장소보다 좁게 설정 */
    .col-event { width: auto; }   /* 행사명은 남는 공간을 다 차지 */
    .col-count { width: 45px; }
    .col-dept  { width: 110px; }
    .col-stat  { width: 50px; }

    /* 행사명 왼쪽 정렬 및 가독성 */
    .event-text { text-align: left !important; padding-left: 8px !important; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (기본 유지)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
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
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', ''), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', ''), 
                        '인원': item.get('peopleCount', ''),
                        '부서': item.get('mgDeptNm', ''),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# (PDF 생성 함수는 동일하므로 생략 가능하나 유지를 위해 포함)
def create_split_pdf(df, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # ... (PDF 로직 동일)
    return bytes(pdf.output())

# 5. 메인 UI 및 화면 출력
st.sidebar.title("📅 대관 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

# PDF 관련 로직 (기본 유지)
if not all_df.empty:
    with st.sidebar:
        # PDF 버튼 생성 로직 (생략 - 기존 코드 유지)
        pass

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                # 수정된 표 구조 (클래스 부여로 너비 조절)
                table_html = f"""
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th class="col-place">장소</th>
                                <th class="col-time">시간</th>
                                <th class="col-event">행사명</th>
                                <th class="col-count">인원</th>
                                <th class="col-dept">부서</th>
                                <th class="col-stat">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, r in bu_df.iterrows():
                    table_html += f"""
                        <tr>
                            <td>{r['장소']}</td>
                            <td>{r['시간']}</td>
                            <td class="event-text">{r['행사명']}</td>
                            <td>{r['인원']}</td>
                            <td>{r['부서']}</td>
                            <td>{r['상태']}</td>
                        </tr>
                    """
                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
