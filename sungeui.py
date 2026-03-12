import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import io

# 1. 초기 설정 및 건물 순서 고정 (이 순서대로 화면에 분리되어 나타납니다)
st.set_page_config(page_title="성의교정 대관 통합 관리", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 사용자가 지정한 건물 정렬 순서
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 엑셀 자동화 (모바일 줌/편집 노가다 방지)
def create_excel_automated(df):
    if df.empty: return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook, worksheet = writer.book, writer.sheets['대관현황']
        
        # 서식 설정 (큰 글씨, 배경색, 테두리)
        hdr_fmt = workbook.add_format({'bold':True, 'font_size':13, 'bg_color':'#D9E1F2', 'border':1, 'align':'center', 'valign':'vcenter'})
        cell_fmt = workbook.add_format({'font_size':12, 'border':1, 'align':'center', 'valign':'vcenter'})
        wrap_fmt = workbook.add_format({'font_size':12, 'border':1, 'align':'left', 'valign':'vcenter', 'text_wrap':True})
        
        worksheet.set_default_row(30) # 행 높이 확대
        cols_spec = [('날짜',14), ('요일',7), ('건물명',16), ('장소',20), ('시간',18), ('행사명',45), ('인원',8), ('부서',18), ('상태',10)]
        
        for i, (name, width) in enumerate(cols_spec):
            worksheet.write(0, i, name, hdr_fmt)
            worksheet.set_column(i, i, width, wrap_fmt if name == '행사명' else cell_fmt)
    return output.getvalue()

# 3. 데이터 추출 및 정렬 로직 (날짜/건물/시간 순서 강제 고정)
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
                    '_dt': d_obj, # 내부 정렬용
                    '_tm': item.get('startTime', '00:00') # 내부 정렬용
                })
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        # 1.날짜순, 2.건물순(BUILDING_ORDER), 3.시간순으로 정렬
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        df = df.sort_values(by=['_dt', 'b_idx', '_tm'])
        return df.drop(columns=['_dt', '_tm', 'b_idx'])
    except:
        return pd.DataFrame()

# 4. 화면 레이아웃 (스크롤 및 셸 노출 문제 해결)
st.sidebar.title("📅 대관 설정")
s_in = st.sidebar.date_input("시작일", value=now_today)
e_in = st.sidebar.date_input("종료일", value=s_in)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(s_in, e_in)

st.markdown(f'<h2 style="text-align:center;">🏫 {s_in} 대관 현황</h2>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    
    # 사이드바 다운로드 버튼
    with st.sidebar:
        st.write("---")
        ex_bin = create_excel_automated(f_df)
        st.download_button("📥 모바일 전용 엑셀 받기", data=ex_bin, file_name=f"대관_{s_in}.xlsx", use_container_width=True)

    # [핵심] 건물별로 섹션을 나누어 노출 (셸 섞임 및 스크롤 문제 해결)
    for b_name in BUILDING_ORDER:
        if b_name in f_df['건물명'].values:
            b_data = f_df[f_df['건물명'] == b_name]
            st.markdown(f"#### 📍 {b_name}") # 건물별 소제목
            # hide_index=True로 0,1,2... 번호 삭제하여 가로 스크롤 최소화
            st.dataframe(b_data, use_container_width=True, hide_index=True)
else:
    st.warning("⚠️ 해당 조건에 맞는 대관 내역이 없습니다.")
