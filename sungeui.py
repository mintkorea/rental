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

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 설정
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 5px; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 10px 0; margin-top: 30px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 15px; margin-bottom: 5px; border-left: 5px solid #2E5077; padding-left: 10px; }
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 8px 4px; font-size: 13px; font-weight: bold; text-align: center; }
    td { border: 1px solid #eee; padding: 8px 6px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }
    .no-data-msg { padding: 12px; color: #d9534f; font-size: 13px; background-color: #fffafa; border: 1px solid #ffe3e3; border-radius: 5px; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 allowDay 요일 필터링 (화면 & PDF 공용)
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
            allow_days = [int(d.strip()) for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            start_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            end_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = start_dt
            while curr <= end_dt:
                if s_date <= curr <= e_date:
                    curr_weekday = curr.weekday() + 1
                    if not allow_days or curr_weekday in allow_days:
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
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. PDF 생성 함수 (allowDay가 적용된 데이터 기반)
def create_filtered_pdf(df, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    if os.path.exists(font_path):
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    
    # 데이터가 있는 날짜만 루프
    for date_val in sorted(df['full_date'].unique()):
        date_df = df[df['full_date'] == date_val]
        # 선택된 건물 중 데이터가 있는 건물이 있는지 확인
        exist_bu = [b for b in selected_buildings if not date_df[date_df['건물명'] == b].empty]
        if not exist_bu: continue
        
        pdf.add_page()
        weekday_str = date_df.iloc[0]['요일']
        pdf.set_font("Nanum", size=16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val} {weekday_str}요일)", ln=True, align='C')
        
        for bu in exist_bu:
            bu_df = date_df[date_df['건물명'] == bu]
            pdf.set_font("Nanum", size=12)
            pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
            pdf.set_text_color(0, 0, 0)
            
            # 헤더
            cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 50), ("상태", 15)]
            pdf.set_fill_color(240, 240, 240)
            pdf.set_font("Nanum", size=10)
            for txt, width in cols:
                pdf.cell(width, 9, txt, border=1, align='C', fill=True)
            pdf.ln()
            
            # 데이터 행
            pdf.set_font("Nanum", size=9)
            for _, row in bu_df.iterrows():
                pdf.cell(40, 9, str(row['장소'])[:20], border=1, align='C')
                pdf.cell(35, 9, str(row['시간']), border=1, align='C')
                pdf.cell(115, 9, " " + str(row['행사명'])[:50], border=1, align='L')
                pdf.cell(12, 9, str(row['인원']), border=1, align='C')
                pdf.cell(50, 9, str(row['부서'])[:20], border=1, align='C')
                pdf.cell(15, 9, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(3)
    return bytes(pdf.output())

# 5. 메인 UI 및 출력
st.sidebar.title("📅 대관 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(start_selected, end_selected)

# 사이드바에 PDF 버튼 배치
if not all_df.empty:
    with st.sidebar:
        try:
            pdf_data = create_filtered_pdf(all_df, selected_bu)
            st.download_button(label="📥 날짜별 PDF 저장", data=pdf_data, file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
        except: st.error("PDF 생성 대기 중...")

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# 메인 화면 출력 (이전과 동일)
date_range = pd.date_range(start_selected, end_selected).strftime('%Y-%m-%d')
for date_str in date_range:
    d_obj = datetime.strptime(date_str, '%Y-%m-%d')
    w_str = ['월','화','수','목','금','토','일'][d_obj.weekday()]
    st.markdown(f'<div class="date-header">📅 {date_str} ({w_str}요일)</div>', unsafe_allow_html=True)
    day_df = all_df[all_df['full_date'] == date_str] if not all_df.empty else pd.DataFrame()
    for bu in selected_bu:
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        bu_df = day_df[day_df['건물명'] == bu] if not day_df.empty else pd.DataFrame()
        if not bu_df.empty:
            header_html = """<div class="table-container"><table><thead><tr>
                            <th style="width:15%;">장소</th><th style="width:15%;">시간</th>
                            <th style="width:40%;">행사명</th><th style="width:7%;">인원</th>
                            <th style="width:15%;">부서</th><th style="width:8%;">상태</th>
                            </tr></thead><tbody>"""
            rows_html = "".join([f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in bu_df.iterrows()])
            st.markdown(header_html + rows_html + "</tbody></table></div>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
