import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import io

# 1. 초기 설정 (다크모드 방어)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

st.markdown("""
<style>
    .stApp { background-color: white !important; color: black !important; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F !important; margin-bottom: 20px; }
    .date-header { background-color: #2E5077 !important; color: white !important; padding: 10px 15px; border-radius: 5px; margin-top: 25px; display: flex; justify-content: space-between; align-items: center; }
    .building-header { font-size: 17px !important; font-weight: 700; margin-top: 20px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333 !important; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white !important; border: 1px solid #ddd !important; }
    th { background-color: #f8f9fa !important; color: #333 !important; border: 1px solid #ccc !important; text-align: center !important; padding: 8px 2px; font-size: 13px; }
    td { border: 1px solid #eee !important; color: #333 !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; background-color: white !important; text-align: center; }
</style>
""", unsafe_allow_html=True)

# 2. PDF 생성 함수 (에러 방어 로직 추가)
def create_pdf(df, selected_buildings):
    pdf = FPDF()
    pdf.add_page()
    
    # [중요] 한글 폰트 설정이 없으면 한글을 출력하지 않도록 방어
    try:
        pdf.add_font('Nanum', '', 'NanumGothic.ttf') # 폰트 파일이 있을 때만 작동
        pdf.set_font('Nanum', size=12)
        has_korean_font = True
    except:
        pdf.set_font("Helvetica", size=12)
        has_korean_font = False

    pdf.cell(200, 10, txt="Rental Status Report", ln=True, align='C')
    
    for date in sorted(df['date'].unique()):
        pdf.ln(5)
        pdf.cell(200, 10, txt=f"Date: {date}", ln=True)
        d_df = df[df['date'] == date]
        for b in selected_buildings:
            b_df = d_df[d_df['building'] == b.replace(" ", "")]
            if not b_df.empty:
                # 한글 폰트가 없으면 영어로 대체하여 에러 방지
                b_name = b if has_korean_font else "Building Location"
                pdf.cell(200, 8, txt=f" {b_name}", ln=True)
                for _, r in b_df.iterrows():
                    event_txt = r['event'] if has_korean_font else "Scheduled Event"
                    pdf.cell(200, 7, txt=f"  - {r['time']} | {event_txt}", ln=True)
    return pdf.output()

# 3. 사이드바 (기존 위치 유지)
with st.sidebar:
    st.header("📅 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

# 4. 데이터 로드 및 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if sel_bu:
    # 데이터 수집 (공백 제거 매칭 포함)
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            bu_nm = str(item.get('buNm', '')).replace(" ", "")
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    rows.append({
                        'date': curr.strftime('%Y-%m-%d'),
                        'building': bu_nm,
                        'place': item.get('placeNm', ''),
                        'time': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        'event': item.get('eventNm', ''),
                        'status': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
    except: df = pd.DataFrame()

    # 화면 출력
    if not df.empty:
        # PDF 버튼 (에러 발생 시 안내만 띄우고 앱은 유지)
        try:
            pdf_bytes = create_pdf(df, sel_bu)
            st.download_button("📄 PDF 다운로드", data=pdf_bytes, file_name="rental.pdf")
        except Exception as e:
            st.warning("PDF 생성 시 한글 폰트 에러가 발생했습니다. 화면의 표를 확인해주세요.")

        for d_str in sorted(df['date'].unique()):
            st.markdown(f'<div class="date-header">📅 {d_str}</div>', unsafe_allow_html=True)
            for b in sel_bu:
                st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                b_df = df[(df['date'] == d_str) & (df['building'] == b.replace(" ", ""))]
                if not b_df.empty:
                    html = "<table><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>상태</th></tr></thead><tbody>"
                    for _, r in b_df.iterrows():
                        html += f"<tr><td>{r['place']}</td><td>{r['time']}</td><td>{r['event']}</td><td>{r['status']}</td></tr>"
                    st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
