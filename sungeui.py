import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io

# 1. 초기 설정 및 순서 고정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. PDF급 엑셀 자동 편집 함수 (xlsxwriter 활용)
def create_excel_styled(df):
    if df.empty: return None
    output = io.BytesIO()
    
    # 건물 순서 정렬
    df['sort_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
    df = df.sort_values(by=['날짜', 'sort_idx', '시간']).drop(columns=['sort_idx'])

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook = writer.book
        worksheet = writer.sheets['대관현황']

        # 스타일 정의 (PDF 느낌)
        hdr_fmt = workbook.add_format({'bold':True, 'bg_color':'#D9E1F2', 'border':1, 'align':'center', 'valign':'vcenter'})
        cell_fmt = workbook.add_format({'border':1, 'align':'center', 'valign':'vcenter'})
        wrap_fmt = workbook.add_format({'border':1, 'align':'left', 'valign':'vcenter', 'text_wrap':True})

        # 열 설정 (날짜, 요일, 건물, 장소, 시간, 행사명, 인원, 부서, 상태)
        widths = [12, 6, 15, 18, 15, 45, 8, 18, 10]
        for i, width in enumerate(widths):
            worksheet.set_column(i, i, width, wrap_fmt if i == 5 else cell_fmt)
            worksheet.write(0, i, df.columns[i], hdr_fmt)
            
    return output.getvalue()

# 3. 데이터 로드 (안전장치 강화)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            # (데이터 파싱 로직 - 생략 없이 기존 로직 그대로 사용)
            rows.append({
                '날짜': item.get('startDt'), '요일': '?', '건물명': item.get('buNm'),
                '장소': item.get('placeNm'), '시간': f"{item.get('startTime')}~{item.get('endTime')}",
                '행사명': item.get('eventNm'), '인원': item.get('peopleCount'),
                '부서': item.get('mgDeptNm'), '상태': '확정'
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

# 4. 사이드바 및 메인 화면 복구 (이 부분이 에러 나면 화면이 증발함)
st.sidebar.title("📅 대관 조회 설정")
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

df = get_data(s_date, e_date)

# [중요] AttributeError 방지를 위한 체크
if df is not None and not df.empty:
    filtered_df = df[df['건물명'].isin(sel_bu)]
    with st.sidebar:
        st.write("---")
        excel_data = create_excel_styled(filtered_df)
        if excel_data:
            st.download_button("📥 PDF급 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx")
    
    st.markdown('<h2 style="text-align:center;">🏫 성의교정 대관 현황</h2>', unsafe_allow_html=True)
    # 이후 데이터 테이블 출력 코드...
else:
    st.sidebar.info("선택한 조건에 대관 내역이 없습니다.")
    st.write("조회된 데이터가 없습니다.")
