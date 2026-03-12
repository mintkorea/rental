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

# 2. CSS 설정 (다크모드 완벽 대응: 고정 배경색 제거)
st.markdown("""
<style>
    /* 제목 및 헤더 디자인 */
    .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 20px; }
    .date-header { 
        font-size: 19px !important; font-weight: 800; 
        color: #007BFF; padding: 10px 0; margin-top: 40px; 
        border-bottom: 3px solid #007BFF; 
    }
    .building-header { 
        font-size: 16px !important; font-weight: 700; 
        margin-top: 20px; margin-bottom: 10px; 
        border-left: 6px solid #007BFF; padding-left: 12px; 
    }
    
    /* 표 디자인: 인덱스 숫자를 숨기고 시스템 테마 글자색 유지 */
    .stDataFrame { border: 1px solid rgba(128, 128, 128, 0.2); }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 기간 대관 추출 함수
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        
        for item in raw:
            if not item.get('startDt'): continue
            
            # 기간 대관 대응을 위한 시작/종료일 파싱
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # 허용 요일 체크
            allowed = [int(d.strip()) for d in str(item.get('allowDay', '')).split(',') if d.strip()]

            # 기간 내의 모든 날짜를 순회하며 조건에 맞는 날만 추가
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed or (curr.weekday() + 1) in allowed:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
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
            return df.sort_values(by=['날짜', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 4. PDF 생성 함수 (한글 폰트 안전장치 포함)
def create_split_pdf(df, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    has_font = os.path.exists(font_path)
    
    if has_font:
        pdf.add_font("Nanum", "", font_path, uni=True)
        pdf.set_font("Nanum", size=10)
    else:
        pdf.set_font("Arial", size=10)
    
    for date_val in sorted(df['날짜'].unique()):
        pdf.add_page()
        date_df = df[df['날짜'] == date_val]
        
        pdf.set_font_size(16)
        title_text = f"Rental Status - {date_val}" if not has_font else f"대관 현황 - {date_val}"
        pdf.cell(0, 15, title_text, ln=True, align='C')
        pdf.ln(5)

        for bu in selected_buildings:
            bu_df = date_df[date_df['건물명'] == bu]
            if bu_df.empty: continue
            
            pdf.set_font_size(12)
            pdf.cell(0, 10, f"* {bu}", ln=True)
            
            pdf.set_font_size(9)
            for _, row in bu_df.iterrows():
                info = f"  [{row['시간']}] {row['장소']} | {row['행사명'][:30]} | {row['상태']}"
                # latin-1 인코딩 오류 방지
                pdf.cell(0, 8, info.encode('ascii', 'ignore').decode('ascii') if not has_font else info, ln=True)
            pdf.ln(3)
            
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# 5. 메인 UI
st.sidebar.title("📅 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected + timedelta(days=6))
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

# 사이드바 PDF 버튼
if not all_df.empty:
    try:
        pdf_data = create_split_pdf(all_df, selected_bu)
        st.sidebar.download_button("📥 PDF 저장", data=pdf_data, file_name=f"rental_{start_selected}.pdf")
    except:
        st.sidebar.info("PDF를 준비 중입니다...")

# 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    for date in sorted(all_df['날짜'].unique()):
        day_df = all_df[all_df['날짜'] == date]
        st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                # 왼쪽 숫자(Index)를 숨긴 깔끔한 표 출력
                st.dataframe(
                    bu_df[['장소', '시간', '행사명', '인원', '부서', '상태']], 
                    hide_index=True, 
                    use_container_width=True
                )
else:
    st.info("조회된 내역이 없습니다. 기간을 다시 설정해 보세요.")
