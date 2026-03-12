import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 관리", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 정렬 순서 고정 (리스트 순서대로 정렬됨)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 모바일용 엑셀 자동화 (큰 글씨 + 행 높이 확대)
def create_excel_automated(df):
    if df.empty: return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook, worksheet = writer.book, writer.sheets['대관현황']
        
        # 모바일용 서식 (줌 없이도 읽히는 12~13pt)
        hdr_fmt = workbook.add_format({'bold':True, 'font_size':13, 'bg_color':'#D9E1F2', 'border':1, 'align':'center', 'valign':'vcenter'})
        cell_fmt = workbook.add_format({'font_size':12, 'border':1, 'align':'center', 'valign':'vcenter'})
        wrap_fmt = workbook.add_format({'font_size':12, 'border':1, 'align':'left', 'valign':'vcenter', 'text_wrap':True})
        
        worksheet.set_default_row(30) # 행 높이 크게
        cols_spec = [('날짜',14), ('요일',7), ('건물명',16), ('장소',20), ('시간',18), ('행사명',45), ('인원',8), ('부서',18), ('상태',10)]
        for i, (name, width) in enumerate(cols_spec):
            worksheet.write(0, i, name, hdr_fmt)
            worksheet.set_column(i, i, width, wrap_fmt if name == '행사명' else cell_fmt)
    return output.getvalue()

# 3. 데이터 추출 및 "강제 정렬" 로직
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            dt_str = (item.get('startDt') or item.get('start')).split('T')[0]
            d_obj = datetime.strptime(dt_str, '%Y-%m-%d').date()
            if s_date <= d_obj <= e_date:
                rows.append({
                    '날짜': dt_str,
                    '요일': ['월','화','수','목','금','토','일'][d_obj.weekday()],
                    '건물명': str(item.get('buNm', '')).strip(),
                    '장소': item.get('placeNm', '') or '-',
                    '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                    '행사명': item.get('eventNm', '') or '-',
                    '인원': str(item.get('peopleCount', '-')),
                    '부서': item.get('mgDeptNm', '') or '-',
                    '상태': '확정' if item.get('status') == 'Y' else '대기',
                    '_dt_obj': d_obj, # 정렬용
                    '_time': item.get('startTime', '00:00') # 정렬용
                })
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        # [정렬 자동화] 1순위:날짜순, 2순위:건물순서, 3순위:시간순
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        df = df.sort_values(by=['_dt_obj', 'b_idx', '_time'])
        return df.drop(columns=['_dt_obj', '_time', 'b_idx'])
    except: return pd.DataFrame()

# 4. 화면 레이아웃 (모바일 가독성 극대화)
st.sidebar.title("📅 대관 설정")
s_in = st.sidebar.date_input("시작일", value=now_today)
e_in = st.sidebar.date_input("종료일", value=s_in)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(s_in, e_in)

st.markdown(f'<h2 style="text-align:center;">🏫 대관 현황 리스트</h2>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    with st.sidebar:
        st.write("---")
        ex_bin = create_excel_automated(f_df)
        st.download_button("📥 모바일 전용 엑셀 받기", data=ex_bin, file_name=f"대관_{s_in}.xlsx", use_container_width=True)
    
    # [화면 노가다 방지] 인덱스 번호 숨기기 + 가로 넓게 사용
    st.dataframe(f_df, use_container_width=True, hide_index=True)
else:
    st.warning("조회된 데이터가 없습니다.")
