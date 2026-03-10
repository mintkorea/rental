import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# 2. CSS 설정 (웹 화면 최적화)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 4px solid #2E5077; padding-left: 8px; margin-bottom: 10px; }
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 550px; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 4px; font-size: 10px; }
    td { border: 1px solid #eee; padding: 6px; font-size: 11px; text-align: center; }
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

# 4. 건물별로 표를 나누어 PDF 생성하는 함수
def create_split_pdf(df, title_text, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
    pdf.add_page()
    
    # 메인 타이틀
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    for bu in selected_buildings:
        bu_df = df[df['건물명'] == bu]
        
        # 건물명 헤더
        pdf.set_font("Nanum", size=12)
        pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
        
        # 표 헤더 설정
        cols = [("장소", 40), ("시간", 30), ("행사명", 110), ("인원", 15), ("부서", 52), ("상태", 10)]
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Nanum", size=10)
        for txt, width in cols:
            pdf.cell(width, 8, txt, border=1, align='C', fill=True)
        pdf.ln()

        # 표 내용
        pdf.set_font("Nanum", size=9)
        if not bu_df.empty:
            for _, row in bu_df.iterrows():
                pdf.cell(40, 8, str(row['장소']), border=1, align='C')
                pdf.cell(30, 8, str(row['시간']), border=1, align='C')
                pdf.cell(110, 8, " " + str(row['행사명']), border=1, align='L')
                pdf.cell(15, 8, str(row['인원']), border=1, align='C')
                pdf.cell(52, 8, str(row['부서']), border=1, align='C')
                pdf.cell(10, 8, str(row['상태']), border=1, align='C')
                pdf.ln()
        else:
            pdf.cell(257, 8, "대관 내역이 없습니다.", border=1, align='C')
            pdf.ln()
        
        pdf.ln(10) # 건물 간 간격

    # 에러 방지를 위한 바이트 변환
    return bytes(pdf.output())

# 5. 메인 UI
st.sidebar.title("📅 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

all_df = get_data(start_selected, end_selected)
display_title = f"성의교정 대관 현황 ({start_selected})" if start_selected == end_selected else f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

# 🚀 즉시 다운로드 버튼 (사이드바)
if not all_df.empty:
    try:
        pdf_data = create_split_pdf(all_df, display_title, selected_bu)
        st.sidebar.download_button(
            label="📥 PDF 즉시 다운로드",
            data=pdf_data,
            file_name=f"rental_{start_selected}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.sidebar.error(f"PDF 생성 중 오류 발생: {e}")
else:
    st.sidebar.info("조회된 내역이 없습니다.")

# 웹 화면 출력
st.markdown(f'<div class="main-title">{display_title}</div>', unsafe_allow_html=True)
if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            rows_html = "".join([f"<tr><td>{r['날짜']}</td><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in bu_df.iterrows()])
            st.markdown(f'<div class="table-container"><table><thead><tr><th>날짜</th><th>장소</th><th>시간</th><th>행사명</th><th>인원</th><th>부서</th><th>상태</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.info("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
