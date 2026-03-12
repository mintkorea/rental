import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import base64

# 1. 초기 설정 및 CSS (다크모드 완벽 방어)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

st.markdown("""
<style>
    .stApp { background-color: white !important; color: black !important; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F !important; margin-bottom: 20px; }
    .sat { color: #4A90E2 !important; font-weight: bold; }
    .sun-hol { color: #E74C3C !important; font-weight: bold; }
    .date-header { 
        background-color: #2E5077 !important; color: white !important; padding: 10px 15px; 
        border-radius: 5px; margin-top: 30px; display: flex; 
        justify-content: space-between; align-items: center;
    }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333 !important; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white !important; border: 1px solid #ddd !important; }
    th { background-color: #f8f9fa !important; color: #333 !important; border: 1px solid #ccc !important; text-align: center !important; padding: 10px 2px; font-size: 13px; }
    td { border: 1px solid #eee !important; color: #333 !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; background-color: white !important; }
    .no-building-data { color: #d9534f !important; font-size: 14px; font-weight: bold; padding: 15px; border: 1px dashed #d9534f !important; border-radius: 5px; margin-top: 10px; text-align: center; background-color: #fffafa !important; }
</style>
""", unsafe_allow_html=True)

# 2. PDF 생성 함수
def create_pdf(df, selected_buildings):
    pdf = FPDF()
    pdf.add_page()
    # 주의: PDF 한글 폰트 경로가 필요합니다. 시스템에 있는 폰트 경로로 수정하세요.
    # 예: pdf.add_font('Nanum', '', 'NanumGothic.ttf', unicode=True)
    # 여기서는 구조만 잡습니다.
    pdf.set_font("Arial", size=12) 
    pdf.cell(200, 10, txt="Songeui Campus Rental Status", ln=1, align='C')
    
    for date in sorted(df['full_date'].unique()):
        pdf.cell(200, 10, txt=f"Date: {date}", ln=1, align='L')
        d_df = df[df['full_date'] == date]
        for b in selected_buildings:
            b_df = d_df[d_df['건물명'] == b]
            pdf.cell(200, 10, txt=f" Building: {b}", ln=1, align='L')
            if not b_df.empty:
                for _, r in b_df.iterrows():
                    line = f" - {r['시간']} | {r['장소']} | {r['행사명']}"
                    pdf.cell(200, 8, txt=line.encode('latin-1', 'replace').decode('latin-1'), ln=1)
            else:
                pdf.cell(200, 8, txt="  No Data", ln=1)
    return pdf.output(dest='S').encode('latin-1')

# 3. 데이터 로드 (allowDay 로직 보존)
@st.cache_data(ttl=60)
def get_rental_data(s_date, e_date):
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
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        w_idx = curr.weekday()
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][w_idx],
                            'color_class': "sat" if w_idx == 5 else ("sun-hol" if w_idx == 6 else "weekday"),
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
    except: return pd.DataFrame()

# 4. 메인 화면
with st.sidebar:
    st.header("📅 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if sel_bu:
    df = get_rental_data(s_date, e_date)
    if not df.empty:
        # PDF 다운로드 버튼
        pdf_data = create_pdf(df, sel_bu)
        st.download_button(label="📄 PDF로 내보내기", data=pdf_data, file_name=f"rental_{s_date}.pdf", mime="application/pdf")
        
        df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
        for date in sorted(df['full_date'].unique()):
            d_df = df[df['full_date'] == date]
            st.markdown(f'''<div class="date-header"><span>📅 {date}</span><span class="{d_df.iloc[0]['color_class']}">({d_df.iloc[0]['요일']}요일)</span></div>''', unsafe_allow_html=True)
            for b in sel_bu:
                b_df = d_df[d_df['건물명'] == b]
                st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                if not b_df.empty:
                    table_html = "<table><thead><tr><th style='width:18%'>장소</th><th style='width:17%'>시간</th><th style='width:20%'>행사명</th><th style='width:10%'>인원</th><th style='width:25%'>부서</th><th style='width:10%'>상태</th></tr></thead><tbody>"
                    for _, r in b_df.sort_values('시간').iterrows():
                        table_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="no-building-data">"{b}"에 대한 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.info("조회된 내역이 없습니다.")
