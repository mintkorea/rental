import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 설정 (반응형 폰트 및 모바일 최적화)
st.markdown("""
<style>
    @media only screen and (max-width: 768px) {
        .stMarkdown div { font-size: 12px !important; }
        table { font-size: 11px !important; }
    }
    .main-title { font-size: 22px; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .date-header { font-size: 18px; font-weight: 800; color: #1E3A5F; margin-top: 30px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 15px; font-weight: 700; margin: 15px 0 5px 0; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    /* 테이블 스타일 강제 고정 */
    .rendered_html table { width: 100%; border-collapse: collapse; table-layout: fixed !important; }
    .rendered_html th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 8px 2px; text-align: center; }
    .rendered_html td { border: 1px solid #eee; padding: 8px 4px; text-align: center; word-break: break-all; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 (기존 로직 유지)
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
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 메인 화면 출력
st.sidebar.title("📅 조회 설정")
start_selected = st.sidebar.date_input("날짜 선택", value=now_today)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

all_df = get_data(start_selected, start_selected)

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu][['장소', '시간', '행사명', '인원', '부서', '상태']]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                # HTML 노출 방지를 위한 핵심: Pandas to_html 사용
                html_table = bu_df.to_html(index=False, escape=False, classes='rendered_html')
                
                # 너비 조절 스타일 강제 주입
                html_table = html_table.replace('<thead>', '<thead><tr style="text-align: center;">')
                widths = ['15%', '15%', '40%', '7%', '15%', '8%']
                for idx, width in enumerate(widths):
                    html_table = html_table.replace(f'<th>{bu_df.columns[idx]}</th>', f'<th style="width: {width};">{bu_df.columns[idx]}</th>')

                st.write(html_table, unsafe_allow_html=True)
else:
    st.info("대관 내역이 없습니다.")
