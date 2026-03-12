import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

# 1. 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 순서 정의
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 가져오기 로직 (안정성 강화)
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
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': str(item.get('placeNm', '')), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': str(item.get('eventNm', '')), 
                        '인원': str(item.get('peopleCount', '0')),
                        '부서': str(item.get('mgDeptNm', '')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 3. PDF 생성 (에러 방지용 인코딩 및 페이지 분리)
def create_safe_pdf(df, selected_buildings):
    # 'L'은 가로 모드 (Landscape)
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # 폰트 파일이 레포지토리에 반드시 있어야 합니다.
    try:
        pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
    except:
        # 폰트 로드 실패 시 기본 폰트로 대체 시도
        pass
    
    df_filtered = df[df['건물명'].isin(selected_buildings)]
    
    if df_filtered.empty:
        return None

    # 날짜별로 루프 돌며 페이지 추가
    for date_val in sorted(df_filtered['full_date'].unique()):
        pdf.add_page()
        date_df = df_filtered[df_filtered['full_date'] == date_val]
        weekday = date_df.iloc[0]['요일']
        
        # 타이틀
        pdf.set_font("Nanum", size=16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val} {weekday}요일)", ln=True, align='C')
        pdf.ln(5)

        for bu in selected_buildings:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            
            # 건물명 섹션
            pdf.set_font("Nanum", size=11)
            pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
            pdf.set_text_color(0, 0, 0)

            # 표 헤더
            pdf.set_font("Nanum", size=9)
            pdf.set_fill_color(240, 240, 240)
            headers = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 50), ("상태", 15)]
            for txt, width in headers:
                pdf.cell(width, 8, txt, border=1, align='C', fill=True)
            pdf.ln()

            # 데이터 행 (문자열 강제 변환으로 에러 방지)
            for _, row in bu_df.iterrows():
                pdf.cell(40, 8, row['장소'][:20], border=1, align='C')
                pdf.cell(35, 8, row['시간'], border=1, align='C')
                pdf.cell(115, 8, " " + row['행사명'][:50], border=1, align='L')
                pdf.cell(12, 8, row['인원'], border=1, align='C')
                pdf.cell(50, 8, row['부서'][:15], border=1, align='C')
                pdf.cell(15, 8, row['상태'], border=1, align='C')
                pdf.ln()
            pdf.ln(5)

    # 최종 출력 시 바이트 변환
    return pdf.output(dest='S').encode('latin-1', 'replace')

# 4. 앱 화면 출력
st.sidebar.header("📅 조회 설정")
start_d = st.sidebar.date_input("시작일", value=now_today)
end_d = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

data = get_data(start_d, end_d)

if not data.empty:
    pdf_out = create_safe_pdf(data, selected_bu)
    if pdf_out:
        st.sidebar.download_button(
            label="📥 날짜별 PDF 다운로드", 
            data=pdf_out, 
            file_name=f"rental_{start_d}.pdf", 
            mime="application/pdf"
        )
    else:
        st.sidebar.warning("선택한 건물의 데이터가 없습니다.")
else:
    st.sidebar.info("조회된 데이터가 없습니다.")

st.title("🏫 성의교정 대관 현황")
if not data.empty:
    for date in sorted(data['full_date'].unique()):
        st.subheader(f"📅 {date}")
        day_data = data[data['full_date'] == date]
        for bu in selected_bu:
            bu_data = day_data[day_data['건물명'] == bu]
            if not bu_data.empty:
                st.write(f"**🏢 {bu}**")
                st.table(bu_data[['장소', '시간', '행사명', '인원', '부서', '상태']])
