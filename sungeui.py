import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 출력 순서 고정 (이 순서대로 정렬됨)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. PDF 수준의 프리미엄 엑셀 생성 함수
def create_excel_styled(df):
    if df.empty: return None
    output = io.BytesIO()
    
    # 건물 순서 정렬 로직
    df['sort_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
    df = df.sort_values(by=['날짜', 'sort_idx', '시간']).drop(columns=['sort_idx'])

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook = writer.book
        worksheet = writer.sheets['대관현황']

        # 고급 서식 정의
        hdr_fmt = workbook.add_format({'bold':True, 'bg_color':'#D9E1F2', 'border':1, 'align':'center', 'valign':'vcenter'})
        cell_fmt = workbook.add_format({'border':1, 'align':'center', 'valign':'vcenter'})
        wrap_fmt = workbook.add_format({'border':1, 'align':'left', 'valign':'vcenter', 'text_wrap':True})

        # 컬럼별 너비 및 서식 지정 (PDF 가독성 재현)
        cols_spec = [('날짜',12), ('요일',6), ('건물명',15), ('장소',18), ('시간',15), ('행사명',45), ('인원',8), ('부서',18), ('상태',10)]
        for i, (name, width) in enumerate(cols_spec):
            worksheet.write(0, i, name, hdr_fmt)
            # 행사명은 줄바꿈 서식, 나머지는 가운데 정렬
            worksheet.set_column(i, i, width, wrap_fmt if i == 5 else cell_fmt)
            
    return output.getvalue()

# 3. 데이터 로드 (매칭 오류 수정 버전)
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
            # 날짜 및 데이터 파싱 (안정성 강화)
            dt_str = item.get('startDt')
            d_obj = datetime.strptime(dt_str, '%Y-%m-%d')
            rows.append({
                '날짜': dt_str,
                '요일': ['월','화','수','목','금','토','일'][d_obj.weekday()],
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '인원': str(item.get('peopleCount', '-')),
                '부서': item.get('mgDeptNm', '') or '-',
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame()

# 4. UI 및 사이드바 제어
st.sidebar.title("📅 대관 조회 설정")
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

df = get_data(s_date, e_date)

# 데이터가 있을 때만 다운로드 버튼 노출
if not df.empty:
    filtered_df = df[df['건물명'].isin(sel_bu)]
    if not filtered_df.empty:
        with st.sidebar:
            st.write("---")
            excel_data = create_excel_styled(filtered_df)
            st.download_button("📥 PDF급 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx")
        
        # 화면 출력
        st.markdown(f'<h2 style="text-align:center;">🏫 {s_date} 대관 현황</h2>', unsafe_allow_html=True)
        # (기존의 table 출력 로직을 여기에 넣으시면 됩니다)
        st.dataframe(filtered_df, use_container_width=True) # 임시 표 출력
    else:
        st.info("선택한 건물의 대관 내역이 없습니다.")
else:
    st.warning("해당 날짜에 조회된 데이터가 없습니다.")
