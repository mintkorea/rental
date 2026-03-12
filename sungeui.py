import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

# 1. 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 가져오기
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
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': str(item.get('placeNm', '')), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': str(item.get('eventNm', '')), 
                        '인원': str(item.get('peopleCount', '0')),
                        '부서': str(item.get('mgDeptNm', '')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 3. PDF 생성 (AttributeError 방지 및 날짜별 페이지 분리)
def create_safe_pdf(df, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # 폰트 추가 (폰트 파일명이 다르면 에러가 나므로 확인 필요)
    try:
        pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
        pdf.set_font("Nanum", size=12)
    except:
        pdf.set_font("Arial", size=12)
    
    df_filtered = df[df['건물명'].isin(selected_buildings)]
    if df_filtered.empty: return None

    # 날짜별로 반복하며 페이지 추가
    for date_val in sorted(df_filtered['full_date'].unique()):
        pdf.add_page()
        date_df = df_filtered[df_filtered['full_date'] == date_val]
        
        # 날짜 제목
        pdf.set_font("Nanum", size=16) if "Nanum" in pdf.fonts else pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val})", ln=True, align='C')
        pdf.ln(5)

        for bu in selected_buildings:
            bu_day_df = date_df[date_df['건물명'] == bu]
            if bu_day_df.empty: continue
            
            pdf.set_font("Nanum", size=11) if "Nanum" in pdf.fonts else pdf.set_font("Arial", "B", 11)
            pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')

            # 헤더
            pdf.set_font("Nanum", size=9) if "Nanum" in pdf.fonts else pdf.set_font("Arial", size=9)
            pdf.set_fill_color(240, 240, 240)
            cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 50), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 8, txt, border=1, align='C', fill=True)
            pdf.ln()

            # 데이터
            for _, row in bu_day_df.iterrows():
                pdf.cell(40, 8, row['장소'][:20], border=1, align='C')
                pdf.cell(35, 8, row['시간'], border=1, align='C')
                pdf.cell(115, 8, " " + row['행사명'][:55], border=1, align='L')
                pdf.cell(12, 8, row['인원'], border=1, align='C')
                pdf.cell(50, 8, row['부서'][:18], border=1, align='C')
                pdf.cell(15, 8, row['상태'], border=1, align='C')
                pdf.ln()
            pdf.ln(5)

    # 에러 방지를 위한 바이트 출력 방식 변경
    return pdf.output()

# 4. 앱 화면 출력
st.sidebar.header("📅 조회 설정")
start_d = st.sidebar.date_input("시작일", value=now_today)
end_d = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

data = get_data(start_d, end_d)

if not data.empty:
    try:
        pdf_out = create_safe_pdf(data, selected_bu)
        if pdf_out:
            st.sidebar.download_button(
                label="📥 날짜별 PDF 다운로드", 
                data=bytes(pdf_out), # byte 변환 추가
                file_name=f"rental_{start_d}.pdf", 
                mime="application/pdf"
            )
    except Exception as e:
        st.sidebar.error(f"PDF 에러 발생: {e}")
else:
    st.sidebar.info("조회된 내역이 없습니다.")

st.title("🏫 성의교정 대관 조회")
# 화면에서도 날짜별로 구분해서 표시
if not data.empty:
    for date in sorted(data['full_date'].unique()):
        st.subheader(f"📅 {date}")
        day_df = data[data['full_date'] == date]
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.write(f"**🏢 {bu}**")
                st.table(bu_df[['장소', '시간', '행사명', '부서', '상태']])
else:
    st.info("내역이 없습니다.")
