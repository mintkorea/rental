import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import io

# 1. 초기 설정 및 다크모드 방어 CSS
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

st.markdown("""
<style>
    /* 다크모드 완벽 방어 */
    .stApp { background-color: white !important; color: black !important; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F !important; margin-bottom: 20px; }
    .date-header { background-color: #2E5077 !important; color: white !important; padding: 10px 15px; border-radius: 5px; margin-top: 30px; display: flex; justify-content: space-between; align-items: center; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333 !important; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white !important; border: 1px solid #ddd !important; }
    th { background-color: #f8f9fa !important; color: #333 !important; border: 1px solid #ccc !important; text-align: center !important; padding: 10px 2px; font-size: 13px; }
    td { border: 1px solid #eee !important; color: #333 !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; background-color: white !important; }
    .no-building-data { color: #d9534f !important; font-size: 14px; font-weight: bold; padding: 15px; border: 1px dashed #d9534f !important; border-radius: 5px; margin-top: 10px; text-align: center; background-color: #fffafa !important; }
</style>
""", unsafe_allow_html=True)

# 2. PDF 생성 함수 (fpdf2 + 한글 폰트 적용)
def create_pdf(df, selected_buildings):
    pdf = FPDF()
    pdf.add_page()
    
    # [중요] 한글 폰트 추가 (폰트 파일이 프로젝트 폴더에 있어야 함)
    try:
        # 나눔고딕 등 ttf 파일 경로를 넣어주세요.
        pdf.add_font('Nanum', '', 'NanumGothic.ttf') 
        pdf.set_font('Nanum', size=14)
    except:
        # 폰트가 없을 경우 에러 방지용 기본 설정
        pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="성의교정 대관 현황 리포트", ln=True, align='C')
    pdf.set_font('Nanum', size=10) if 'Nanum' in pdf.fonts else pdf.set_font("Arial", size=10)

    for date in sorted(df['full_date'].unique()):
        pdf.ln(5)
        pdf.set_fill_color(46, 80, 119) # date-header 색상
        pdf.set_text_color(255, 255, 255)
        pdf.cell(190, 10, txt=f" 날짜: {date}", ln=True, fill=True)
        pdf.set_text_color(0, 0, 0)
        
        d_df = df[df['full_date'] == date]
        for b in selected_buildings:
            b_df = d_df[d_df['건물명'] == b]
            pdf.ln(2)
            pdf.set_font('Nanum', 'B', 11) if 'Nanum' in pdf.fonts else pdf.set_font("Arial", 'B', 11)
            pdf.cell(190, 8, txt=f" 건물: {b}", ln=True)
            
            if not b_df.empty:
                pdf.set_font('Nanum', '', 9) if 'Nanum' in pdf.fonts else pdf.set_font("Arial", size=9)
                for _, r in b_df.sort_values('시간').iterrows():
                    line = f"  - {r['시간']} | {r['장소']} | {r['행사명']}"
                    pdf.cell(190, 7, txt=line, ln=True)
            else:
                pdf.set_font('Nanum', '', 9) if 'Nanum' in pdf.fonts else pdf.set_font("Arial", size=9)
                pdf.cell(190, 7, txt="  내역 없음", ln=True)
    
    return pdf.output()

# 3. 데이터 로드 (allowDay 로직 사수)
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

# 4. 사이드바 및 출력
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
        try:
            pdf_bytes = create_pdf(df, sel_bu)
            st.download_button("📄 PDF 다운로드", data=pdf_bytes, file_name=f"rental_{s_date}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"PDF 생성 중 알 수 없는 오류: {e}")

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
else:
    st.warning("조회할 건물을 선택해 주세요.")
