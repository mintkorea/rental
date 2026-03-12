import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정 및 초기화
st.set_page_config(page_title="성의교정 대관 현황", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 순서 정의
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS: 다크모드 대응 및 표 디자인
st.markdown("""
<style>
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .date-header { font-size: 19px !important; font-weight: 800; color: #007BFF; padding: 10px 0; margin-top: 30px; border-bottom: 2px solid #007BFF; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 15px; border-left: 5px solid #007BFF; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (기간 대관 완벽 처리)
@st.cache_data(ttl=60)
def get_rental_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    headers = {"User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        raw_data = res.json().get('res', [])
        rows = []
        
        for item in raw_data:
            if not item.get('startDt'): continue
            
            # 기간 대관 대응: 시작일부터 종료일까지 루프
            start_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            end_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # 해당 이벤트의 허용 요일 (없으면 전체)
            allowed_days = [int(d.strip()) for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            curr = start_dt
            while curr <= end_dt:
                # 사용자가 선택한 조회 기간 내에 있는지 확인
                if s_date <= curr <= e_date:
                    # 요일 체크 (1:월, ..., 7:일)
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['날짜', '건물명', '시간'])
        return df
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()

# 4. PDF 생성 함수 (fpdf2 기준)
def create_pdf(df, buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # 한글 폰트가 없을 경우를 대비한 안전 장치
    font_path = "NanumGothic.ttf"
    has_font = os.path.exists(font_path)
    if has_font:
        pdf.add_font("Nanum", "", font_path)
        pdf.set_font("Nanum", size=10)
    else:
        pdf.set_font("Arial", size=10)

    for date in sorted(df['날짜'].unique()):
        pdf.add_page()
        date_df = df[df['날짜'] == date]
        pdf.set_font_size(16)
        pdf.cell(0, 10, f"Rental Status - {date}", ln=True, align='C')
        
        for bu in buildings:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            pdf.set_font_size(12)
            pdf.ln(5)
            pdf.cell(0, 10, f"Building: {bu}", ln=True)
            
            # 헤더
            pdf.set_font_size(9)
            pdf.cell(40, 8, "Place", border=1)
            pdf.cell(35, 8, "Time", border=1)
            pdf.cell(120, 8, "Event", border=1)
            pdf.cell(20, 8, "Status", border=1, ln=True)
            
            for _, r in bu_df.iterrows():
                pdf.cell(40, 8, str(r['장소']), border=1)
                pdf.cell(35, 8, str(r['시간']), border=1)
                pdf.cell(120, 8, str(r['행사명'])[:40], border=1)
                pdf.cell(20, 8, str(r['상태']), border=1, ln=True)
                
    return pdf.output()

# 5. 메인 UI
st.sidebar.title("🗓️ 대관 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected + timedelta(days=6))
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_rental_data(start_selected, end_selected)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    # PDF 저장 버튼 (fpdf2 설치 필요)
    try:
        pdf_out = create_pdf(all_df, selected_bu)
        st.sidebar.download_button("📥 PDF 다운로드", data=bytes(pdf_out), file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
    except Exception as e:
        st.sidebar.warning(f"PDF 라이브러리 설정 필요: {e}")

    # 화면 출력
    for date in sorted(all_df['날짜'].unique()):
        day_df = all_df[all_df['날짜'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                st.dataframe(bu_df[['장소', '시간', '행사명', '부서', '상태']], hide_index=True, use_container_width=True)
else:
    st.info("조회된 내역이 없습니다. 시작일과 종료일을 다시 확인해 주세요.")
