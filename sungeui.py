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

# 2. 반응형 CSS 설정 (모바일 인식 폰트 리사이징 및 셸 조정)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 10px; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 10px 0; margin-top: 25px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 15px; margin-bottom: 8px; border-left: 5px solid #2E5077; padding-left: 10px; }
    
    .table-container { width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; min-width: 650px; } /* 모바일 가로 스크롤 보장 */
    
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px 4px; font-size: 13px; font-weight: bold; text-align: center; }
    td { border: 1px solid #eee; padding: 10px 6px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }

    /* [셸 너비 고정] 전체 합 100% */
    .w-place { width: 15%; }
    .w-time { width: 15%; }
    .w-event { width: 38%; }
    .w-people { width: 8%; }
    .w-dept { width: 16%; }
    .w-status { width: 8%; }

    /* [모바일 전용 스타일] 화면 너비가 768px 이하일 때 자동 적용 */
    @media only screen and (max-width: 768px) {
        .main-title { font-size: 18px !important; }
        .date-header { font-size: 16px !important; }
        .building-header { font-size: 14px !important; }
        th { font-size: 11px !important; padding: 6px 2px !important; }
        td { font-size: 11px !important; padding: 6px 3px !important; }
        
        /* 모바일에서는 표가 너무 좁아지지 않게 최소 너비 유지 */
        table { min-width: 600px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 처리 함수 (기존 로직 유지)
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
            allowed_weekdays = []
            if item.get('allowDay'):
                allowed_weekdays = [int(d.strip()) for d in str(item['allowDay']).split(',') if d.strip()]
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    curr_weekday = curr.weekday() + 1 
                    if not allowed_weekdays or curr_weekday in allowed_weekdays:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
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

# 4. PDF 생성 함수 (기존 유지)
def create_split_pdf(df, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        pdf.set_font("Nanum", size=16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val})", ln=True, align='C')
        for bu in selected_buildings:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            pdf.set_font("Nanum", size=11)
            pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
            pdf.set_text_color(0, 0, 0)
            cols = [("장소", 38), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 52), ("상태", 15)]
            pdf.set_font("Nanum", size=9)
            for txt, width in cols: pdf.cell(width, 9, txt, border=1, align='C', fill=False)
            pdf.ln()
            for _, row in bu_df.iterrows():
                pdf.cell(38, 8, str(row['장소'])[:20], border=1, align='C')
                pdf.cell(35, 8, str(row['시간']), border=1, align='C')
                pdf.cell(115, 8, " " + str(row['행사명'])[:50], border=1, align='L')
                pdf.cell(12, 8, str(row['인원']), border=1, align='C')
                pdf.cell(52, 8, str(row['부서'])[:20], border=1, align='C')
                pdf.cell(15, 8, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(2)
    return bytes(pdf.output())

# 5. 메인 출력 로직
st.sidebar.title("📅 대관 조회")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

if not all_df.empty:
    with st.sidebar:
        try:
            pdf_data = create_split_pdf(all_df, selected_bu)
            st.download_button(label="📥 PDF 저장 (날짜별 분리)", data=pdf_data, file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
        except: pass

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                # 반응형 셸 넓이가 적용된 테이블 생성
                table_html = f"""
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th class="w-place">장소</th>
                                <th class="w-time">시간</th>
                                <th class="w-event">행사명</th>
                                <th class="w-people">인원</th>
                                <th class="w-dept">부서</th>
                                <th class="w-status">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, r in bu_df.iterrows():
                    table_html += f"""
                            <tr>
                                <td>{r['장소']}</td>
                                <td>{r['시간']}</td>
                                <td style='text-align:left;'>{r['행사명']}</td>
                                <td>{r['인원']}</td>
                                <td>{r['부서']}</td>
                                <td>{r['상태']}</td>
                            </tr>
                    """
                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
