import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import io

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 리스트 순서 고정
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 2. CSS 설정: 모바일 최적화 및 표 가독성
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 4px solid #2E5077; padding-left: 8px; margin-bottom: 10px; }
    .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { width: 100% !important; border-collapse: collapse; table-layout: auto !important; min-width: 550px; }
    th { background-color: #f8f9fa !important; border: 1px solid #dee2e6 !important; padding: 4px 2px !important; font-size: 10px; }
    td { border: 1px solid #eee !important; padding: 6px 2px !important; font-size: 11px; text-align: center; }
    .col-event { text-align: left !important; white-space: normal !important; word-break: keep-all; min-width: 150px; }
    .small-cell { width: 45px; font-size: 10px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수
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

# 4. PDF 생성 함수 (io.BytesIO를 사용한 가장 안전한 방식)
def get_pdf_output(df, title_text):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
    pdf.add_page()
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    
    # 헤더 설정
    cols = [("장소", 40), ("시간", 30), ("행사명", 120), ("인원", 10), ("부서", 57), ("상태", 20)]
    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Nanum", size=10)
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
    
    # ⚠️ 중요: output() 결과를 bytearray로 변환하여 반환
    return bytes(pdf.output())

# 5. 메인 UI
st.sidebar.title("📅 대관 조회 필터")
start_selected = st.sidebar.date_input("조회 시작일", value=now_today)
end_selected = st.sidebar.date_input("조회 종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

all_df = get_data(start_selected, end_selected)
display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})" if start_selected != end_selected else f"성의교정 대관 현황 ({start_selected})"

# 🚀 PDF 즉시 다운로드 버튼 (데이터 있을 때만 표시)
if not all_df.empty:
    try:
        pdf_bytes = get_pdf_output(all_df, display_title)
        st.sidebar.download_button(
            label="📥 PDF 저장하기",
            data=pdf_bytes,
            file_name=f"rental_{start_selected}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.sidebar.error(f"PDF 생성 오류: {str(e)}")
else:
    st.sidebar.info("조회된 내역이 없습니다.")

st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)

if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            rows_html = "".join([f"""
                <tr>
                    <td class="small-cell">{r['날짜']}</td><td>{r['장소']}</td><td>{r['시간']}</td>
                    <td class="col-event">{r['행사명']}</td><td class="small-cell">{r['인원']}</td>
                    <td>{r['부서']}</td><td class="small-cell">{r['상태']}</td>
                </tr>""" for _, r in bu_df.iterrows()])
            st.markdown(f'<div class="table-container"><table><thead><tr><th class="small-cell">날짜</th><th>장소</th><th>시간</th><th>행사명</th><th class="small-cell">인원</th><th>부서</th><th class="small-cell">상태</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.write("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
