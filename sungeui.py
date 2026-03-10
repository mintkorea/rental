import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 및 시간 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 건물 리스트 순서 고정 (홈페이지 순서 반영)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"] #

# 3. 데이터 가져오기 (인원 필드 peopleCount 적용)
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
            
            p_count = item.get('peopleCount', '-') #
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
                            '인원': p_count, #
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

# 4. PDF 생성 함수 (나눔고딕 폰트 적용)
def create_pdf(df, title_text):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    
    # 폰트 파일 경로 설정 (파일명이 정확해야 합니다)
    font_path = "NanumGothic.ttf" 
    
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else:
        st.error(f"폰트 파일을 찾을 수 없습니다: {font_path}")
        return None

    pdf.add_page()
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    # 테이블 헤더 (날짜 제외 6열: 장소, 시간, 행사명, 인원, 부서, 상태)
    cols = [("장소", 35), ("시간", 35), ("행사명", 90), ("인원", 15), ("부서", 45), ("상태", 20)]
    
    pdf.set_fill_color(200, 200, 200)
    pdf.set_font("Nanum", size=10)
    for txt, width in cols:
        pdf.cell(width, 10, txt, border=1, align='C', fill=True)
    pdf.ln()

    # 데이터 행 작성
    for _, row in df.iterrows():
        pdf.cell(35, 10, str(row['장소']), border=1, align='C')
        pdf.cell(35, 10, str(row['시간']), border=1, align='C')
        pdf.cell(90, 10, str(row['행사명']), border=1, align='L')
        pdf.cell(15, 10, str(row['인원']), border=1, align='C') #
        pdf.cell(45, 10, str(row['부서']), border=1, align='C')
        pdf.cell(20, 10, str(row['상태']), border=1, align='C')
        pdf.ln()
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 실행 로직 ---
all_df = get_data(now_today, now_today)

if st.sidebar.button("📄 PDF로 저장"):
    if not all_df.empty:
        pdf_data = create_pdf(all_df, f"성의교정 대관 현황 ({now_today})")
        if pdf_data:
            st.sidebar.download_button(
                label="📥 PDF 다운로드",
                data=pdf_data,
                file_name=f"rental_{now_today}.pdf",
                mime="application/pdf"
            )
    else:
        st.sidebar.warning("조회된 데이터가 없습니다.")
