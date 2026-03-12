import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정 (줌 기능 복구 및 레이아웃 유지)
st.set_page_config(
    page_title="성의교정 대관 조회", 
    layout="wide",
    initial_sidebar_state="expanded"
)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정: 표 열 너비 고정, 2줄 허용, 줌 복구, 요일 색상
st.markdown("""
<style>
    /* 줌 및 모바일 대응 복구 */
    html { zoom: 100%; }
    
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 5px; }
    .date-header { font-size: 18px !important; font-weight: 800; padding: 10px 0; margin-top: 30px; border-bottom: 2px solid #eee; }
    .date-sat { color: #007BFF !important; } /* 토요일: 청색 */
    .date-sun { color: #FF0000 !important; } /* 일요일/공휴일: 적색 */
    
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 15px; margin-bottom: 5px; border-left: 5px solid #2E5077; padding-left: 10px; }

    /* 표 크기 강제 고정 로직 */
    .table-container { width: 100%; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    th, td { border: 1px solid rgba(128, 128, 128, 0.2); padding: 4px 2px; text-align: center; vertical-align: middle; overflow: hidden; }
    
    /* 열별 너비 설정 */
    th:nth-child(1), td:nth-child(1) { width: 16%; } /* 장소 (4) */
    th:nth-child(2), td:nth-child(2) { width: 110px; } /* 시간 (최소여백) */
    th:nth-child(3), td:nth-child(3) { width: 45%; } /* 행사명 (기준) */
    th:nth-child(4), td:nth-child(4) { width: 45px; }  /* 인원 (최소여백) */
    th:nth-child(5), td:nth-child(5) { width: 20%; } /* 부서 (5) */
    th:nth-child(6), td:nth-child(6) { width: 50px; }  /* 상태 (최소여백) */

    /* 데이터 넘침 처리: 2줄 허용 및 폰트 축소 */
    td { font-size: 12px; line-height: 1.2; word-break: break-all; }
    td:nth-child(1), td:nth-child(3), td:nth-child(5) { 
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        font-size: 11px; /* 넘치는 항목 폰트 미세하게 축소 */
    }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 (기존 성공 소스 로직 100% 유지)
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
            allowed_weekdays = [int(d.strip()) for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_weekdays or (curr.weekday() + 1) in allowed_weekdays:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'w_num': curr.weekday(),
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}-{item.get('endTime', '')}",
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

# 4. PDF 생성 (기존 로직 유지)
def create_split_pdf(df, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        pdf.set_font("Nanum", size=15)
        pdf.cell(0, 10, f"대관 현황 ({date_val} {date_df.iloc[0]['요일']})", ln=True, align='C')
        for bu in selected_buildings:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            pdf.set_font("Nanum", size=11); pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 8, f"■ {bu}", ln=True); pdf.set_text_color(0, 0, 0)
            pdf.set_font("Nanum", size=8)
            # PDF 표 헤더
            cols = [("장소", 35), ("시간", 30), ("행사명", 110), ("인원", 10), ("부서", 45), ("상태", 15)]
            for txt, w in cols: pdf.cell(w, 8, txt, border=1, align='C', fill=False)
            pdf.ln()
            for _, r in bu_df.iterrows():
                pdf.cell(35, 7, str(r['장소'])[:18], border=1)
                pdf.cell(30, 7, str(r['시간']), border=1, align='C')
                pdf.cell(110, 7, " " + str(r['행사명'])[:45], border=1)
                pdf.cell(10, 7, str(r['인원']), border=1, align='C')
                pdf.cell(45, 7, str(r['부서'])[:20], border=1)
                pdf.cell(15, 7, str(r['상태']), border=1, align='C')
                pdf.ln()
    return bytes(pdf.output())

# 5. UI
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

if not all_df.empty:
    with st.sidebar:
        try:
            pdf_data = create_split_pdf(all_df, selected_bu)
            st.download_button("📥 PDF 저장", data=pdf_data, file_name=f"rental_{start_selected}.pdf")
        except: pass

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        w_num = day_df.iloc[0]['w_num']
        color_class = "date-sat" if w_num == 5 else ("date-sun" if w_num == 6 else "")
        st.markdown(f'<div class="date-header {color_class}">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                rows_html = ""
                for _, r in bu_df.iterrows():
                    rows_html += f"""
                    <tr>
                        <td>{r['장소']}</td>
                        <td>{r['시간']}</td>
                        <td style='text-align:left;'>{r['행사명']}</td>
                        <td>{r['인원']}</td>
                        <td>{r['부서']}</td>
                        <td>{r['상태']}</td>
                    </tr>
                    """
                st.markdown(f'<div class="table-container"><table><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>인원</th><th>부서</th><th>상태</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
