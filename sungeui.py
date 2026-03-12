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

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정 (여백 및 레이아웃 최적화)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 20px; color: #1E3A5F; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 12px 0; margin-top: 35px; border-bottom: 2px solid #2E5077; }
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 20px; margin-bottom: 8px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333; }
    
    /* 테이블 스타일 최적화: 여백(padding) 확보 */
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; border: 1px solid #dee2e6; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 12px 4px; font-size: 13px; font-weight: bold; text-align: center; color: #495057; }
    td { border: 1px solid #eee; padding: 10px 8px; font-size: 13px; text-align: center; vertical-align: middle; word-break: keep-all; overflow-wrap: break-word; }
    tr:hover { background-color: #fdfdfd; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (기존 유지하되 예외 처리 강화)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res.raise_for_status()
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            allowed_days = [int(d.strip()) for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 4. PDF 생성 함수 (안정성 강화)
def create_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else:
        pdf.set_font("Arial", size=10) # 폰트 없을 경우 대비

    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        pdf.set_font("Nanum", size=16) if os.path.exists(font_path) else pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val})", ln=True, align='C')
        
        for bu in date_df['건물명'].unique():
            bu_df = date_df[date_df['건물명'] == bu]
            pdf.set_text_color(46, 80, 119)
            pdf.set_font("Nanum", size=12) if os.path.exists(font_path) else pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"■ {bu}", ln=True)
            
            # 테이블 헤더
            pdf.set_text_color(0)
            pdf.set_fill_color(240, 240, 240)
            cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 15), ("부서", 45), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 10, txt, border=1, align='C', fill=True)
            pdf.ln()
            
            # 데이터 행
            pdf.set_font("Nanum", size=9) if os.path.exists(font_path) else pdf.set_font("Arial", size=9)
            for _, row in bu_df.iterrows():
                pdf.cell(40, 9, str(row['장소'])[:18], border=1, align='C')
                pdf.cell(35, 9, str(row['시간']), border=1, align='C')
                pdf.cell(115, 9, " " + str(row['행사명'])[:45], border=1, align='L')
                pdf.cell(15, 9, str(row['인원']), border=1, align='C')
                pdf.cell(45, 9, str(row['부서'])[:15], border=1, align='C')
                pdf.cell(15, 9, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(5)
    return pdf.output(dest='S').encode('latin-1', errors='ignore')

# 5. 메인 UI
st.sidebar.title("📅 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

raw_df = get_data(start_selected, end_selected)

if not raw_df.empty:
    # 건물 필터 및 정렬 적용
    filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)].copy()
    filtered_df['건물명'] = pd.Categorical(filtered_df['건물명'], categories=BUILDING_ORDER, ordered=True)
    filtered_df = filtered_df.sort_values(by=['full_date', '건물명', '시간'])

    if not filtered_df.empty:
        with st.sidebar:
            if st.button("📄 PDF 생성 및 준비"):
                try:
                    pdf_bytes = create_pdf(filtered_df)
                    st.download_button("📥 PDF 다운로드", data=pdf_bytes, file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"PDF 생성 오류: {e}")

        st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

        for date in sorted(filtered_df['full_date'].unique()):
            day_df = filtered_df[filtered_df['full_date'] == date]
            st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
            
            for bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                    
                    header_html = """
                    <div class="table-container"><table><thead><tr>
                        <th style="width:15%;">장소</th><th style="width:15%;">시간</th><th style="width:40%;">행사명</th>
                        <th style="width:7%;">인원</th><th style="width:15%;">부서</th><th style="width:8%;">상태</th>
                    </tr></thead><tbody>"""
                    
                    rows_html = "".join([
                        f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td>"
                        f"<td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" 
                        for _, r in bu_df.iterrows()
                    ])
                    st.markdown(header_html + rows_html + "</tbody></table></div>", unsafe_allow_html=True)
    else:
        st.info("선택한 건물에 해당하는 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
