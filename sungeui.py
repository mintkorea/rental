import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정 및 시간
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 건물 리스트 순서 고정
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 3. CSS 설정: 모바일 대응 및 행사명 최대화 디자인
st.markdown("""
<style>
    /* 기본 배경 및 폰트 설정 */
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: 800; color: #000; margin-bottom: 15px; text-align: center; }
    .building-header { font-size: 17px !important; font-weight: 700; color: #000; margin-top: 20px; margin-bottom: 5px; }
    
    /* 모바일 가로 스크롤 및 테이블 고정 레이아웃 */
    .table-container { overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; min-width: 650px; }
    th { background-color: #f2f2f2 !important; color: #333 !important; border: 1px solid #ccc !important; padding: 6px 2px !important; font-size: 12px; }
    td { border: 1px solid #eee !important; padding: 8px 4px !important; text-align: center; font-size: 12px; vertical-align: middle; }
    
    /* 행사명은 길어지면 다음 줄로 넘어가도록 설정 (모바일 배려) */
    .event-col { text-align: left !important; white-space: normal !important; word-break: keep-all; line-height: 1.4; }

    /* 웹/모바일 컬럼별 너비 최적화 */
    th:nth-child(1), td:nth-child(1) { width: 55px; }  /* 날짜 */
    th:nth-child(2), td:nth-child(2) { width: 95px; }  /* 장소 */
    th:nth-child(3), td:nth-child(3) { width: 90px; }  /* 시간 */
    th:nth-child(4), td:nth-child(4) { width: auto; }  /* 행사명 (자유 확장) */
    th:nth-child(5), td:nth-child(5) { width: 40px; }  /* 인원 */
    th:nth-child(6), td:nth-child(6) { width: 100px; } /* 부서 */
    th:nth-child(7), td:nth-child(7) { width: 50px; }  /* 상태 */
</style>
""", unsafe_allow_html=True)

# 4. 데이터 로드 함수
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
                            '날짜': curr.strftime('%m-%d'),
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
            return df.sort_values(by=['날짜', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 5. PDF 생성 함수 (시간 줄이고 행사명 대폭 확장)
def create_pdf(df, title_text):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else: return None

    pdf.add_page()
    pdf.set_font("Nanum", size=18)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    for date in sorted(df['날짜'].unique()):
        date_df = df[df['날짜'] == date]
        for bu in BUILDING_ORDER:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            
            pdf.set_font("Nanum", size=12)
            pdf.cell(0, 10, f"{bu}(2026-{date})", ln=True)
            
            # PDF 컬럼 너비 최적화: 시간(28), 행사명(124), 인원(10)
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font("Nanum", size=10)
            cols = [("장소", 40), ("시간", 28), ("행사명", 124), ("인원", 10), ("부서", 55), ("상태", 20)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()

            pdf.set_font("Nanum", size=9)
            for _, row in bu_df.iterrows():
                pdf.cell(40, 10, str(row['장소']), border=1, align='C')
                pdf.cell(28, 10, str(row['시간']), border=1, align='C')
                pdf.cell(124, 10, " " + str(row['행사명']), border=1, align='L') 
                pdf.cell(10, 10, str(row['인원']), border=1, align='C')
                pdf.cell(55, 10, str(row['부서']), border=1, align='C')
                pdf.cell(20, 10, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(6)
            
    return pdf.output()

# --- 메인 로직 ---
st.sidebar.title("🔍 대관 조회")
start_selected = st.sidebar.date_input("조회 시작일", value=now_today)
end_selected = st.sidebar.date_input("조회 종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 타이틀 형식 (하루일 때와 기간일 때 구분)
display_title = f"성의교정 대관 현황 ({start_selected})" if start_selected == end_selected else f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

all_df = get_data(start_selected, end_selected)

if st.sidebar.button("📄 PDF 생성"):
    if not all_df.empty:
        pdf_bytes = create_pdf(all_df, display_title)
        if pdf_bytes:
            st.sidebar.download_button("📥 다운로드", data=bytes(pdf_bytes), file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
    else: st.sidebar.warning("데이터가 없습니다.")

st.markdown(f'<div class="main-title">{display_title}</div>', unsafe_allow_html=True)

if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            # 테이블을 가로 스크롤 컨테이너로 감싸 모바일 대응
            table_html = bu_df[['날짜', '장소', '시간', '행사명', '인원', '부서', '상태']].to_html(index=False, escape=False)
            # 행사명 열에 'event-col' 클래스 강제 삽입 (문자열 치환)
            table_html = table_html.replace('<td>', '<td class="event-col">', 4) # 행사명 열 위치에 맞게 조정 필요시 CSS nth-child 활용
            st.markdown(f'<div class="table-container">{table_html}</div>', unsafe_allow_html=True)
        else:
            st.write("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
