import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io
from fpdf import FPDF
import os

# 1. 초기 설정 및 건물 순서 고정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 출력 순서 (PDF/엑셀/화면 공통)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. PDF 수준의 엑셀 자동 편집 함수
def create_excel_premium(df):
    if df.empty: return None
    output = io.BytesIO()
    
    # 건물 순서대로 데이터 정렬
    df['sort_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
    df = df.sort_values(by=['날짜', 'sort_idx', '시간']).drop(columns=['sort_idx'])

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook = writer.book
        worksheet = writer.sheets['대관현황']

        # PDF급 서식 정의
        hdr_fmt = workbook.add_format({'bold':True, 'bg_color':'#D9E1F2', 'border':1, 'align':'center', 'valign':'vcenter'})
        cell_fmt = workbook.add_format({'border':1, 'align':'center', 'valign':'vcenter'})
        left_fmt = workbook.add_format({'border':1, 'align':'left', 'valign':'vcenter', 'text_wrap':True})

        # 헤더 적용 및 열 너비 설정 (PDF 가독성 기준)
        columns_config = [('날짜',12), ('요일',6), ('건물명',15), ('장소',18), ('시간',15), ('행사명',45), ('인원',8), ('부서',18), ('상태',10)]
        for i, (name, width) in enumerate(columns_config):
            worksheet.write(0, i, name, hdr_fmt)
            # 행사명(i=5)은 왼쪽 정렬 및 자동 줄바꿈 적용
            worksheet.set_column(i, i, width, left_fmt if i == 5 else cell_fmt)
            
    return output.getvalue()

# 3. 데이터 로드 (에러 방지 강화)
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
            # 날짜별 데이터 처리 로직 (기본 로직 유지)
            rows.append({'날짜': item['startDt'], '건물명': item['buNm'], ...}) 
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

# 4. 사이드바 및 메인 화면 복구
st.sidebar.title("📅 대관 조회 설정")
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

# 에러 없이 데이터 가져오기
df = get_data(s_date, e_date)

if df is not None and not df.empty:
    filtered_df = df[df['건물명'].isin(sel_bu)]
    with st.sidebar:
        st.write("---")
        # PDF 수준으로 편집된 엑셀 다운로드
        excel_data = create_excel_premium(filtered_df)
        if excel_data:
            st.download_button("📥 PDF급 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx")
else:
    # 데이터가 없을 때 사이드바가 사라지지 않도록 경고 문구 표시
    st.sidebar.info("선택한 조건에 대관 내역이 없습니다.")

st.markdown('<h2 style="text-align:center;">🏫 성의교정 대관 현황</h2>', unsafe_allow_html=True)
# ... (이하 화면 표 출력 로직)
