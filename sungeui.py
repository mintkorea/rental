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

# 3. CSS 설정: 홈페이지 셀 너비 최적화 (불필요한 공백 제거)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 24px !important; font-weight: 800; color: #000; margin-bottom: 20px; text-align: center; }
    .building-header { font-size: 18px !important; font-weight: 700; color: #000; margin-top: 25px; margin-bottom: 8px; }
    
    /* 웹 테이블 레이아웃 최적화 */
    table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; }
    th { background-color: #f2f2f2 !important; color: #333 !important; border: 1px solid #ccc !important; padding: 8px 4px !important; font-size: 13px; }
    td { border: 1px solid #eee !important; padding: 8px 4px !important; text-align: center; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    
    /* 홈페이지 컬럼별 너비 강제 지정 (행사명 최대화) */
    th:nth-child(1), td:nth-child(1) { width: 70px; }  /* 날짜 */
    th:nth-child(2), td:nth-child(2) { width: 120px; } /* 장소 */
    th:nth-child(3), td:nth-child(3) { width: 100px; } /* 시간 */
    th:nth-child(4), td:nth-child(4) { width: auto; text-align: left; } /* 행사명 (유동적) */
    th:nth-child(5), td:nth-child(5) { width: 50px; }  /* 인원 */
    th:nth-child(6), td:nth-child(6) { width: 120px; } /* 부서 */
    th:nth-child(7), td:nth-child(7) { width: 60px; }  /* 상태 */
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
                            '날짜': curr.strftime('%m-%d'), # 연도 제외하여 슬림하게
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}", # 공백 제거
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

# 5. PDF 생성 함수 (시간 줄이고 행사명 늘림)
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
            pdf.cell(0, 10, f"{bu}(2026-{date})", ln=True) # PDF엔 연도 포함
            
            # PDF 컬럼 너비 재설정 (전체 합 277mm)
            # 장소(40), 시간(30로 축소), 행사명(117로 확장), 인원(10), 부서(60), 상태(20)
            pdf.set_fill_color(220, 220, 220)
            pdf.set_font("Nanum", size=10)
            cols = [("장소", 40), ("시간", 30), ("행사명", 117), ("인원", 10), ("부서", 60), ("상태", 20)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()

            pdf.set_font("Nanum", size=9)
            for _, row in bu_df.iterrows():
                pdf.cell(40, 10, str(row['장소']), border=1, align='C')
                pdf.cell(30, 10, str(row['시간']), border=1, align='C')
                pdf.cell(117, 10, " " + str(row['행사명']), border=1, align='L') # 좌측 여백 살짝
                pdf.cell(10, 10, str(row['인원']), border=1, align='C')
                pdf.cell(60, 10, str(row['부서']), border=1, align='C')
                pdf.cell(20, 10, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(6)
            
    return pdf.output()

# --- 실행 로직 ---
st.sidebar.title("🔍 검색 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

if start_selected == end_selected:
    display_title = f"성의교정 대관 현황 ({start_selected})"
else:
    display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

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
            # 웹 화면 출력용 컬럼 순서
            st.markdown(bu_df[['날짜', '장소', '시간', '행사명', '인원', '부서', '상태']].to_html(index=False, escape=False), unsafe_allow_html=True)
        else:
            st.write("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
