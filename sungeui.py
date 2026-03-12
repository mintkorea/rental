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

# 건물 리스트 순서 고정 (의과대학, 간호대학 포함)
BUILDING_ORDER = [
    "성의회관", "의생명산업연구원", "옴니버스 파크", 
    "옴니버스파크 의과대학", "옴니버스파크 간호대학", 
    "대학본관", "서울성모별관"
]

# 2. CSS 설정
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 25px; border-left: 5px solid #2E5077; padding-left: 10px; margin-bottom: 10px; }
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 600px; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 6px; font-size: 11px; font-weight: bold; }
    td { border: 1px solid #eee; padding: 8px 6px; font-size: 12px; text-align: center; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 필터링
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
                    curr_weekday = curr.weekday() + 1
                    if not allowed_weekdays or curr_weekday in allowed_weekdays:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
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

# 4. PDF 생성: "날짜별"로 표를 완전히 쪼개는 로직 (핵심)
def create_split_pdf(df, title_text, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
    pdf.add_page()
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    # 선택된 건물만 필터링
    df = df[df['건물명'].isin(selected_buildings)]
    
    if df.empty:
        pdf.cell(0, 10, "조회된 내역이 없습니다.", ln=True, align='C')
    else:
        # 날짜별로 그룹화하여 루프 실행
        for date_val in sorted(df['full_date'].unique()):
            date_df = df[df['full_date'] == date_val]
            weekday_str = date_df.iloc[0]['요일']
            
            # 부제목: "날짜(요일) 대관 현황"
            pdf.set_font("Nanum", size=12)
            pdf.set_fill_color(240, 240, 240)
            pdf.cell(0, 10, f" ▶ {date_val}({weekday_str}) 대관 현황", ln=True, align='L', fill=True)
            pdf.ln(2)

            # 해당 날짜 안에서 건물별로 표 생성
            for bu in selected_buildings:
                bu_day_df = date_df[date_df['건물명'] == bu]
                if bu_day_df.empty: continue
                
                # 건물 소제목
                pdf.set_font("Nanum", size=10)
                pdf.set_text_color(46, 80, 119)
                pdf.cell(0, 8, f"   ■ {bu}", ln=True, align='L')
                pdf.set_text_color(0, 0, 0)

                # 표 헤더
                cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 50), ("상태", 15)]
                pdf.set_fill_color(250, 250, 250)
                pdf.set_font("Nanum", size=9)
                for txt, width in cols:
                    pdf.cell(width, 8, txt, border=1, align='C', fill=True)
                pdf.ln()

                # 표 내용
                for _, row in bu_day_df.iterrows():
                    pdf.cell(40, 8, str(row['장소']), border=1, align='C')
                    pdf.cell(35, 8, str(row['시간']), border=1, align='C')
                    pdf.cell(115, 8, " " + str(row['행사명']), border=1, align='L')
                    pdf.cell(12, 8, str(row['인원']), border=1, align='C')
                    pdf.cell(50, 8, str(row['부서']), border=1, align='C')
                    pdf.cell(15, 8, str(row['상태']), border=1, align='C')
                    pdf.ln()
                pdf.ln(4) # 건물 사이 간격
            pdf.ln(5) # 날짜 사이 간격

    return pdf.output(dest='S').encode('latin-1', 'replace')

# 5. 메인 UI
st.sidebar.title("📅 대관 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(start_selected, end_selected)
display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

if not all_df.empty:
    try:
        pdf_bytes = create_split_pdf(all_df, display_title, selected_bu)
        st.sidebar.download_button(label="📥 PDF 저장", data=pdf_bytes, file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
    except Exception as e:
        st.sidebar.error(f"오류: {e}")
else:
    st.sidebar.info("내역 없음")

st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)
if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        if bu_df.empty: continue
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        rows_html = "".join([f"<tr><td>{r['full_date']}({r['요일']})</td><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in bu_df.iterrows()])
        st.markdown(f'<div class="table-container"><table><thead><tr><th>날짜</th><th>장소</th><th>시간</th><th>행사명</th><th>인원</th><th>부서</th><th>상태</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
