import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 건물 리스트 순서 고정
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 3. CSS 설정: 모바일 가독성 및 행사명 공간 극대화
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 4px solid #2E5077; padding-left: 8px; }
    
    /* 모바일 스크롤 컨테이너 최적화 */
    .table-container { 
        overflow-x: auto; 
        -webkit-overflow-scrolling: touch; 
        margin-bottom: 20px;
    }
    
    table { 
        width: 100% !important; 
        border-collapse: collapse; 
        table-layout: fixed !important; 
        min-width: 580px; /* 모바일에서 표가 너무 찌그러지지 않는 최소 너비 */
    }
    
    th { background-color: #f8f9fa !important; border: 1px solid #dee2e6 !important; padding: 6px 2px !important; font-size: 11px; }
    td { border: 1px solid #eee !important; padding: 6px 3px !important; font-size: 11px; text-align: center; vertical-align: middle; }
    
    /* 컬럼별 너비 고정 (행사명 위주) */
    .col-date { width: 45px; }
    .col-place { width: 85px; }
    .col-time { width: 85px; }
    .col-event { width: auto; text-align: left !important; white-space: normal !important; word-break: keep-all; }
    .col-people { width: 35px; }
    .col-dept { width: 90px; }
    .col-status { width: 45px; }
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
            rows.append({
                '날짜': datetime.strptime(item['startDt'], '%Y-%m-%d').strftime('%m-%d'),
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', ''), 
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', ''), 
                '인원': item.get('peopleCount', ''),
                '부서': item.get('mgDeptNm', ''),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['날짜', '건물명'])
        return df
    except: return pd.DataFrame()

# 5. PDF 생성 함수 (인코딩 및 레이아웃 수정)
def create_pdf(df, title_text):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else: return None

    pdf.add_page()
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    
    # PDF 컬럼 너비 최적화
    cols = [("장소", 38), ("시간", 28), ("행사명", 124), ("인원", 10), ("부서", 57), ("상태", 20)]
    
    pdf.set_fill_color(230, 230, 230)
    for txt, width in cols:
        pdf.cell(width, 10, txt, border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font("Nanum", size=9)
    for _, row in df.iterrows():
        pdf.cell(38, 9, str(row['장소']), border=1, align='C')
        pdf.cell(28, 9, str(row['시간']), border=1, align='C')
        pdf.cell(124, 9, " " + str(row['행사명']), border=1, align='L')
        pdf.cell(10, 9, str(row['인원']), border=1, align='C')
        pdf.cell(57, 9, str(row['부서']), border=1, align='C')
        pdf.cell(20, 9, str(row['상태']), border=1, align='C')
        pdf.ln()
        
    return pdf.output()

# --- 메인 실행부 ---
st.sidebar.title("📅 대관 조회")
s_date = st.sidebar.date_input("날짜 선택", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

display_title = f"성의교정 대관 현황 ({s_date})"
all_df = get_data(s_date, s_date)

if st.sidebar.button("📄 PDF 생성"):
    if not all_df.empty:
        # ⚠️ bytes(pdf.output()) 형태로 수정하여 AttributeError 방지
        pdf_bytes = create_pdf(all_df, display_title)
        if pdf_bytes:
            st.sidebar.download_button("📥 PDF 다운로드", data=bytes(pdf_bytes), file_name=f"rental_{s_date}.pdf", mime="application/pdf")
    else: st.sidebar.warning("데이터가 없습니다.")

st.markdown(f'<div class="main-title">{display_title}</div>', unsafe_allow_html=True)

if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            # HTML 테이블 생성 시 클래스 부여하여 모바일 스크롤 및 너비 제어
            html = f"""
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th class="col-date">날짜</th><th class="col-place">장소</th><th class="col-time">시간</th>
                            <th class="col-event">행사명</th><th class="col-people">인원</th>
                            <th class="col-dept">부서</th><th class="col-status">상태</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join([f'<tr><td>{r["날짜"]}</td><td>{r["장소"]}</td><td>{r["시간"]}</td><td class="col-event">{r["행사명"]}</td><td>{r["인원"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>' for _, r in bu_df.iterrows()])}
                    </tbody>
                </table>
            </div>
            """
            st.markdown(html, unsafe_allow_html=True)
        else: st.write("대관 내역이 없습니다.")
else: st.info("조회된 내역이 없습니다.")
