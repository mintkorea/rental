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

# 2. 건물 리스트 순서 고정
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 3. CSS 설정 (홈페이지 디자인 복구)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 25px; }
    .building-header { font-size: 18px !important; font-weight: 700; color: #2E5077; margin-top: 30px; margin-bottom: 10px; border-left: 5px solid #2E5077; padding-left: 10px; }
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; table-layout: auto; }
    .custom-table th { background-color: #444; color: white; padding: 10px; border: 1px solid #333; font-size: 14px; }
    .custom-table td { border: 1px solid #eee; padding: 10px; text-align: center; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 함수 (인원 포함)
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
                            'raw_date': curr,
                            '날짜': curr.strftime('%Y-%m-%d'),
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
            return df.sort_values(by=['날짜', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 5. PDF 생성 함수 (이미지 예시처럼 날짜별 건물 그룹화)
def create_pdf(df, title_text):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else:
        return None

    pdf.add_page()
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    # 날짜별 -> 건물별로 순회하며 테이블 생성
    for date in df['날짜'].unique():
        date_df = df[df['날짜'] == date]
        for bu in BUILDING_ORDER:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            
            # 건물명 헤더
            pdf.set_font("Nanum", size=12)
            pdf.cell(0, 10, f"{bu}({date})", ln=True)
            
            # 테이블 헤더
            pdf.set_fill_color(200, 200, 200)
            pdf.set_font("Nanum", size=10)
            cols = [("장소", 40), ("시간", 40), ("행사명", 90), ("인원", 15), ("부서", 50), ("상태", 20)]
            for txt, width in cols:
                pdf.cell(width, 8, txt, border=1, align='C', fill=True)
            pdf.ln()
            
            # 데이터 행
            for _, row in bu_df.iterrows():
                pdf.cell(40, 8, str(row['장소']), border=1, align='C')
                pdf.cell(40, 8, str(row['시간']), border=1, align='C')
                pdf.cell(90, 8, str(row['행사명']), border=1, align='L')
                pdf.cell(15, 8, str(row['인원']), border=1, align='C')
                pdf.cell(50, 8, str(row['부서']), border=1, align='C')
                pdf.cell(20, 8, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(5)
            
    return pdf.output()

# --- 실행 로직 ---
st.sidebar.title("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)

all_df = get_data(start_selected, end_selected)

# PDF 저장 버튼
if st.sidebar.button("📄 PDF 생성하기"):
    if not all_df.empty:
        pdf_bytes = create_pdf(all_df, f"성의교정 대관 현황 ({start_selected}~{end_selected})")
        if pdf_bytes:
            st.sidebar.download_button(
                label="📥 PDF 다운로드",
                data=bytes(pdf_bytes),
                file_name=f"rental_{start_selected}.pdf",
                mime="application/pdf"
            )
    else:
        st.sidebar.warning("데이터가 없습니다.")

# 메인 화면 표시
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({start_selected} ~ {end_selected})</div>', unsafe_allow_html=True)

if not all_df.empty:
    for bu in BUILDING_ORDER:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            st.write(bu_df[['날짜', '장소', '시간', '행사명', '부서', '상태']])
        else:
            st.write("대관 내역이 없습니다.")
else:
    st.info("해당 기간에 대관 내역이 없습니다.")
