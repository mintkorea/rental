import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

# 1. 페이지 및 시간 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 건물 리스트 순서 (홈페이지와 동일하게 고정)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 3. CSS 설정: 홈페이지 디자인 복구 및 테이블 깨짐 방지
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 25px; }
    .building-header { font-size: 20px !important; font-weight: 700; color: #2E5077; margin-top: 35px; margin-bottom: 15px; border-left: 5px solid #2E5077; padding-left: 10px; }
    .custom-table { width: 100% !important; border-collapse: collapse; margin-bottom: 30px; table-layout: auto !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 14px; padding: 12px 8px; border: 1px solid #333; text-align: center; }
    .custom-table td { border: 1px solid #eee; padding: 10px 8px !important; font-size: 13px; vertical-align: middle; text-align: center; line-height: 1.4; }
    .event-name { text-align: left !important; padding-left: 15px !important; }
</style>
""", unsafe_allow_html=True)

# 4. 사이드바 필터
st.sidebar.header("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("조회 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 5. 데이터 가져오기 (인원: peopleCount 반영)
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
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (str(curr.weekday()+1) in allow_days):
                        rows.append({
                            'raw_date': curr, 'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%m-%d'), 
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', '-'),
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['raw_date', '건물명', 'raw_time'])
        return df
    except: return pd.DataFrame()

all_df = get_data(start_selected, end_selected)

# 6. 홈페이지 화면 렌더링
display_title = f"성의교정 대관 현황 ({start_selected})" if start_selected == end_selected else f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"
st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)

for bu in selected_bu:
    bu_df = all_df[all_df['건물명'] == bu] if not all_df.empty else pd.DataFrame()
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not bu_df.empty:
        html = '<table class="custom-table"><thead><tr>'
        html += '<th>날짜</th><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>상태</th>'
        html += '</tr></thead><tbody>'
        for _, r in bu_df.iterrows():
            html += f'<tr><td>{r["날짜"]}</td><td>{r["장소"]}</td><td>{r["시간"]}</td>'
            html += f'<td class="event-name">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#999; margin-left:15px; margin-bottom:30px;">대관 내역 없음</p>', unsafe_allow_html=True)

# 7. PDF 생성 함수 (생략된 폰트 경로는 실제 환경에 맞춰주세요)
def create_pdf(df, title):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # 나눔고딕 폰트가 실행 환경에 있어야 합니다.
    try:
        pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
        pdf.set_font("Nanum", size=12)
    except:
        pdf.set_font("Arial", size=12)
        
    pdf.add_page()
    pdf.cell(0, 10, title, ln=True, align='C')
    # ... PDF 상세 레이아웃 로직 ...
    return pdf.output(dest='S').encode('latin-1')

if not all_df.empty:
    st.sidebar.markdown("---")
    st.sidebar.info("PDF 저장 기능을 사용하려면 서버에 폰트 파일이 필요합니다.")
