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

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 가져오기
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

# 3. PDF 생성 (날짜별 페이지 분리 로직 적용)
def create_paged_pdf(df, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
    
    df = df[df['건물명'].isin(selected_buildings)]
    
    # 날짜별로 루프를 돌면서 각 날짜를 새로운 페이지에 배치
    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page() # <--- 핵심: 날짜가 바뀔 때마다 새 페이지 추가
        
        date_df = df[df['full_date'] == date_val]
        weekday_str = date_df.iloc[0]['요일']
        
        # 페이지 상단 날짜 제목
        pdf.set_font("Nanum", size=16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val} {weekday_str}요일)", ln=True, align='C')
        pdf.ln(5)

        for bu in selected_buildings:
            bu_day_df = date_df[date_df['건물명'] == bu]
            if bu_day_df.empty: continue
            
            pdf.set_font("Nanum", size=11)
            pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
            pdf.set_text_color(0, 0, 0)

            # 헤더
            pdf.set_font("Nanum", size=9)
            pdf.set_fill_color(240, 240, 240)
            cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 50), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 8, txt, border=1, align='C', fill=True)
            pdf.ln()

            # 내용
            for _, row in bu_day_df.iterrows():
                pdf.cell(40, 8, str(row['장소']), border=1, align='C')
                pdf.cell(35, 8, str(row['시간']), border=1, align='C')
                pdf.cell(115, 8, " " + str(row['행사명']), border=1, align='L')
                pdf.cell(12, 8, str(row['인원']), border=1, align='C')
                pdf.cell(50, 8, str(row['부서']), border=1, align='C')
                pdf.cell(15, 8, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(5)

    return pdf.output(dest='S').encode('latin-1', 'replace')

# 4. 메인 화면
st.sidebar.title("📅 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(start_selected, end_selected)

if not all_df.empty:
    try:
        pdf_data = create_paged_pdf(all_df, selected_bu)
        st.sidebar.download_button(label="📥 날짜별 PDF 저장", data=pdf_data, file_name=f"rental_{start_selected}.pdf", mime="application/pdf")
    except Exception as e:
        st.sidebar.error(f"PDF 생성 실패: {e}")

st.title("🏫 성의교정 대관 조회")
if not all_df.empty:
    for date_val in sorted(all_df['full_date'].unique()):
        st.subheader(f"📅 {date_val}")
        date_df = all_df[all_df['full_date'] == date_val]
        for bu in selected_bu:
            bu_day_df = date_df[date_df['건물명'] == bu]
            if not bu_day_df.empty:
                st.write(f"**🏢 {bu}**")
                st.dataframe(bu_day_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True)
else:
    st.info("조회된 내역이 없습니다.")
