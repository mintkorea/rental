import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io
from fpdf import FPDF
import os

# 1. 초기 설정 및 순서 정의
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 출력 순서 고정 (화면, PDF, 엑셀 공통)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 가져오기 (요일 필터링 포함)
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
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '', 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '', 
                            '인원': str(item.get('peopleCount', '')) if item.get('peopleCount') else '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 엑셀 자동 편집 함수 (xlsxwriter 활용)
def create_excel_automated(df):
    output = io.BytesIO()
    # 건물 순서대로 정렬
    df['순서'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
    df = df.sort_values(by=['날짜', '순서', '시간']).drop(columns=['순서'])

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook = writer.book
        worksheet = writer.sheets['대관현황']

        # 서식 정의
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True})

        # 헤더 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
        
        # 열 너비 및 셀 서식 자동 적용
        worksheet.set_column('A:A', 12, cell_fmt) # 날짜
        worksheet.set_column('B:B', 5, cell_fmt)  # 요일
        worksheet.set_column('C:E', 18, cell_fmt) # 건물, 장소, 시간
        worksheet.set_column('F:F', 40, left_fmt) # 행사명 (길게, 왼쪽 정렬)
        worksheet.set_column('G:I', 12, cell_fmt) # 인원, 부서, 상태

    return output.getvalue()

# 4. 화면 UI 출력 (생략된 기존 스타일 및 로직 유지)
st.sidebar.title("📅 설정")
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

df = get_data(s_date, e_date)

if not df.empty:
    filtered_df = df[df['건물명'].isin(sel_bu)]
    with st.sidebar:
        # 엑셀 다운로드 버튼
        st.download_button(
            label="📥 편집된 엑셀 다운로드",
            data=create_excel_automated(filtered_df),
            file_name=f"대관현황_{s_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
# ... (이하 화면 출력 코드 생략)
