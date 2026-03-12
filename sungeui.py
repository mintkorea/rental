import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io
from fpdf import FPDF
import os

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 출력 순서 (PDF/엑셀/화면 공통)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 고도화된 엑셀 편집 함수 (PDF 스타일 적용)
def create_excel_styled(df):
    output = io.BytesIO()
    # 건물 순서대로 정렬
    df['sort_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
    df = df.sort_values(by=['날짜', 'sort_idx', '시간']).drop(columns=['sort_idx'])

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook = writer.book
        worksheet = writer.sheets['대관현황']

        # PDF 스타일 서식 정의
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True})

        # 헤더 서식 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
        
        # 열 너비 자동 조절 (PDF 가독성 기준)
        worksheet.set_column('A:A', 12, cell_fmt)  # 날짜
        worksheet.set_column('B:B', 6, cell_fmt)   # 요일
        worksheet.set_column('C:E', 18, cell_fmt)  # 건물, 장소, 시간
        worksheet.set_column('F:F', 45, left_fmt)  # 행사명 (길게, 줄바꿈)
        worksheet.set_column('G:I', 12, cell_fmt)  # 인원, 부서, 상태
        
    return output.getvalue()

# 3. 데이터 로드 로직 (생략 - 기존과 동일)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    # (기존 데이터 수집 코드 유지)
    ...

# 4. 메인 UI 및 사이드바 복구
st.sidebar.title("📅 대관 조회 설정")
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

df = get_data(s_date, e_date)

if not df.empty:
    filtered_df = df[df['건물명'].isin(sel_bu)]
    
    with st.sidebar:
        st.write("---")
        # 엑셀 다운로드 (자동 편집 완료된 버전)
        st.download_button(
            label="📥 PDF급 엑셀 다운로드",
            data=create_excel_styled(filtered_df),
            file_name=f"대관현황_{s_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# 화면 출력 로직
st.markdown('<h2 style="text-align:center;">🏫 성의교정 대관 현황</h2>', unsafe_allow_html=True)
# (이하 화면 표 출력 로직 유지)
