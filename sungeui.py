import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 기본 설정 및 한국 시간 고정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 순서 (스크린샷 기반 업데이트 반영)
BUILDING_ORDER = [
    "성의회관", "의생명산업연구원", "옴니버스 파크", 
    "옴니버스파크 의과대학", "옴니버스파크 간호대학", 
    "대학본관", "서울성모별관"
]

# 2. 데이터 처리 및 요일 필터링 로직
@st.cache_data(ttl=60)
def get_filtered_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            
            # allowDay 추출 (예: "1,2,3" -> [1, 2, 3])
            allow_day_str = str(item.get('allowDay', ''))
            allowed_list = [int(x.strip()) for x in allow_day_str.split(',') if x.strip()]
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            curr = s_dt
            while curr <= e_dt:
                # 1) 조회 기간 범위 내에 있는가?
                if s_date <= curr <= e_date:
                    # 2) 요일 조건이 맞는가? (월:1 ~ 일:7)
                    curr_weekday = curr.weekday() + 1
                    if not allowed_list or curr_weekday in allowed_list:
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

# 3. PDF 생성 (날짜별 페이지 강제 분리)
def create_paged_pdf(df, selected_buildings):
    font_path = os.path.join(os.getcwd(), "NanumGothic.ttf")
    if not os.path.exists(font_path): return None

    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", font_path, uni=True)
    
    df_filtered = df[df['건물명'].isin(selected_buildings)]
    if df_filtered.empty: return None

    # 날짜별 루프 - 무조건 새 페이지에서 시작
    for date_val in sorted(df_filtered['full_date'].unique()):
        pdf.add_page()
        date_df = df_filtered[df_filtered['full_date'] == date_val]
        
        pdf.set_font("Nanum", size=16)
        pdf.cell(0, 15, f"성의교정 대관 현황 ({date_val} {date_df.iloc[0]['요일']}요일)", ln=True, align='C')
        pdf.ln(5)

        for bu in selected_buildings:
            bu_day_df = date_df[date_df['건물명'] == bu]
            if bu_day_df.empty: continue
            
            pdf.set_font("Nanum", size=11)
            pdf.set_text_color(46, 80, 119)
            pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
            pdf.set_text_color(0, 0, 0)

            pdf.set_font("Nanum", size=9)
            pdf.set_fill_color(242, 242, 242)
            # 가독성을 위해 너비 미세 조정 (장소/행사명)
            cols = [("장소", 40), ("시간", 35), ("행사명", 110), ("인원", 10), ("부서", 50), ("상태", 15)]
            for txt, width in cols:
                pdf.cell(width, 8, txt, border=1, align='C', fill=True)
            pdf.ln()

            for _, row in bu_day_df.iterrows():
                pdf.cell(40, 8, row['장소'][:20], border=1, align='C')
                pdf.cell(35, 8, row['시간'], border=1, align='C')
                pdf.cell(110, 8, " " + row['행사명'][:50], border=1, align='L')
                pdf.cell(10, 8, row['인원'], border=1, align='C')
                pdf.cell(50, 8, row['부서'][:20], border=1, align='C')
                pdf.cell(15, 8, row['상태'], border=1, align='C')
                pdf.ln()
            pdf.ln(5)

    return pdf.output()

# 4. 메인 UI (모바일 대응)
st.sidebar.header("📅 조회 범위 설정")
s_d = st.sidebar.date_input("시작일", value=now_today)
e_d = st.sidebar.date_input("종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

data = get_filtered_data(s_d, e_d)

# PDF 다운로드 버튼 섹션
if not data.empty:
    try:
        pdf_res = create_paged_pdf(data, selected_bu)
        if pdf_res:
            st.sidebar.download_button(
                label="📥 날짜별 PDF 저장", 
                data=bytes(pdf_res), 
                file_name=f"rental_{s_d}.pdf", 
                mime="application/pdf"
            )
    except Exception as e:
        st.sidebar.error(f"PDF 생성 오류: {e}")

# 화면 출력 섹션
st.markdown(f"### 🏫 성의교정 대관 현황")
if not data.empty:
    for date in sorted(data['full_date'].unique()):
        day_df = data[data['full_date'] == date]
        st.info(f"📅 {date} ({day_df.iloc[0]['요일']})")
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.write(f"**🏢 {bu}**")
                # 모바일 가독성을 위해 데이터프레임 대신 테이블 사용
                st.table(bu_df[['장소', '시간', '행사명', '부서', '상태']])
else:
    st.warning("조회된 대관 내역이 없습니다.")
