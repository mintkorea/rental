import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정 (다크모드 방지 및 레이아웃)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 스타일 설정 (화이트 배경 및 깔끔한 테이블)
st.markdown("""
<style>
    .stApp { background-color: white; color: black; }
    .main-title { font-size: 22px; font-weight: bold; text-align: center; margin-bottom: 20px; color: #1E3A5F; }
    .date-header { font-size: 18px; font-weight: bold; color: #1E3A5F; padding: 10px 0; margin-top: 30px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 16px; font-weight: bold; margin-top: 15px; margin-bottom: 5px; color: #2E5077; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 10px; color: black; }
    th { background-color: #f2f2f2; border: 1px solid #ddd; padding: 8px; font-size: 13px; text-align: center; }
    td { border: 1px solid #eee; padding: 8px; font-size: 13px; text-align: center; }
    .no-data { color: #d9534f; font-size: 13px; padding: 5px 0; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 allowDay 요일 필터링 (핵심 로직)
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
            
            # allowDay 요일 추출 (1:월, 7:일)
            allow_days = [int(d.strip()) for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            start_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            end_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            curr = start_dt
            while curr <= end_dt:
                if s_date <= curr <= e_date:
                    # 요일 필터링 적용
                    curr_weekday = curr.weekday() + 1
                    if not allow_days or curr_weekday in allow_days:
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
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. PDF 생성 함수
def create_pdf(df, selected_bu):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    if os.path.exists("NanumGothic.ttf"):
        pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
        pdf.set_font("Nanum", size=10)
    
    for date_val in sorted(df['full_date'].unique()):
        pdf.add_page()
        date_df = df[df['full_date'] == date_val]
        pdf.set_font("Nanum", size=14)
        pdf.cell(0, 10, f"대관 현황 - {date_val}", ln=True, align='C')
        
        for bu in selected_bu:
            bu_df = date_df[date_df['건물명'] == bu]
            pdf.set_font("Nanum", size=11)
            pdf.cell(0, 10, f"■ {bu}", ln=True)
            if bu_df.empty:
                pdf.set_font("Nanum", size=9)
                pdf.cell(0, 8, "대관 내역이 없습니다.", ln=True)
            else:
                pdf.set_font("Nanum", size=9)
                # 간략화된 테이블 헤더 및 데이터 추가 로직...
                for _, r in bu_df.iterrows():
                    pdf.cell(0, 7, f"[{r['장소']}] {r['시간']} | {r['행사명']}", ln=True)
    return pdf.output(dest='S').encode('latin1')

# 5. UI 및 출력
st.sidebar.title("⚙️ 설정")
s_d = st.sidebar.date_input("시작일", value=now_today)
e_d = st.sidebar.date_input("종료일", value=s_d)
bul_list = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]
sel_bu = st.sidebar.multiselect("건물 선택", bul_list, default=["성의회관", "의생명산업연구원"])

df = get_data(s_d, e_d)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# 날짜별 루프
for d in pd.date_range(s_d, e_d).strftime('%Y-%m-%d'):
    st.markdown(f'<div class="date-header">📅 {d}</div>', unsafe_allow_html=True)
    day_df = df[df['full_date'] == d] if not df.empty else pd.DataFrame()
    
    for bu in sel_bu:
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        bu_df = day_df[day_df['건물명'] == bu] if not day_df.empty else pd.DataFrame()
        
        if not bu_df.empty:
            st.write(bu_df[['장소', '시간', '행사명', '인원', '부서', '상태']].to_html(index=False, escape=False), unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

# PDF 다운로드 버튼
if not df.empty:
    st.sidebar.download_button("📥 PDF 다운로드", data=create_pdf(df, sel_bu), file_name="rental.pdf")
