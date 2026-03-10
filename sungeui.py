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

# 건물 리스트 순서 고정
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 2. CSS 설정: 모바일 최적화 및 표 너비 자동 조절
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 4px solid #2E5077; padding-left: 8px; margin-bottom: 10px; }
    
    /* 테이블 컨테이너: 가로 스크롤 제거 및 자동 너비 */
    .table-container { width: 100%; overflow-x: hidden; }
    
    table { 
        width: 100% !important; 
        border-collapse: collapse; 
        table-layout: auto !important; /* 고정 너비 해제하여 모바일 대응 */
    }
    
    th { background-color: #f8f9fa !important; border: 1px solid #dee2e6 !important; padding: 4px 2px !important; font-size: 10px; }
    td { border: 1px solid #eee !important; padding: 6px 2px !important; font-size: 11px; text-align: center; vertical-align: middle; }
    
    /* 행사명은 길면 줄바꿈 처리 */
    .col-event { text-align: left !important; white-space: normal !important; word-break: break-all; min-width: 100px; }
    
    /* 모바일에서 불필요하게 넓은 셀 방지 */
    .small-cell { width: 35px; font-size: 9px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (시작일/종료일 기간 조회)
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
                        '날짜': curr.strftime('%m-%d'),
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

# 4. PDF 생성 함수 (AttributeError 해결 버전)
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
    
    # PDF 컬럼 (이미지 001.jpg 레이아웃 반영)
    cols = [("장소", 40), ("시간", 30), ("행사명", 120), ("인원", 10), ("부서", 57), ("상태", 20)]
    pdf.set_fill_color(230, 230, 230)
    for txt, width in cols:
        pdf.cell(width, 10, txt, border=1, align='C', fill=True)
    pdf.ln()

    pdf.set_font("Nanum", size=9)
    for _, row in df.iterrows():
        pdf.cell(40, 9, str(row['장소']), border=1, align='C')
        pdf.cell(30, 9, str(row['시간']), border=1, align='C')
        pdf.cell(120, 9, " " + str(row['행사명']), border=1, align='L')
        pdf.cell(10, 9, str(row['인원']), border=1, align='C')
        pdf.cell(57, 9, str(row['부서']), border=1, align='C')
        pdf.cell(20, 9, str(row['상태']), border=1, align='C')
        pdf.ln()
    return pdf.output(dest='S') # 바이트 형식으로 직접 반환하여 오류 방지

# 5. 메인 로직
st.sidebar.title("📅 조회 기간 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

if start_selected == end_selected:
    display_title = f"성의교정 대관 현황 ({start_selected})"
else:
    display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

all_df = get_data(start_selected, end_selected)

# PDF 다운로드 처리 (SyntaxError 해결)
if st.sidebar.button("📄 PDF 생성하기"):
    if not all_df.empty:
        pdf_data = create_pdf(all_df, display_title)
        if pdf_data:
            st.sidebar.download_button("📥 다운로드", data=pdf_data, file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
    else: st.sidebar.warning("데이터가 없습니다.")

st.markdown(f'<div class="main-title">{display_title}</div>', unsafe_allow_html=True)

if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            # HTML 테이블 렌더링 (모바일 스크롤 제거 및 너비 자동 조절)
            rows_html = "".join([f"""
                <tr>
                    <td class="small-cell">{r['날짜']}</td><td>{r['장소']}</td><td>{r['시간']}</td>
                    <td class="col-event">{r['행사명']}</td><td class="small-cell">{r['인원']}</td>
                    <td>{r['부서']}</td><td class="small-cell">{r['상태']}</td>
                </tr>""" for _, r in bu_df.iterrows()])
            
            st.markdown(f"""
            <div class="table-container">
                <table>
                    <thead>
                        <tr>
                            <th class="small-cell">날짜</th><th>장소</th><th>시간</th>
                            <th>행사명</th><th class="small-cell">인원</th>
                            <th>부서</th><th class="small-cell">상태</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
            </div>
            """, unsafe_allow_html=True)
        else: st.info("대관 내역이 없습니다.")
else: st.info("조회된 내역이 없습니다.")
