import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 요약", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 엑셀 자동화 (엑셀에는 전체 정보를 다 담아 보고서로 활용)
def create_excel_automated(df):
    if df.empty: return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook, worksheet = writer.book, writer.sheets['대관현황']
        hdr_fmt = workbook.add_format({'bold':True, 'font_size':12, 'bg_color':'#D9E1F2', 'border':1, 'align':'center'})
        cell_fmt = workbook.add_format({'font_size':11, 'border':1, 'align':'center'})
        wrap_fmt = workbook.add_format({'font_size':11, 'border':1, 'align':'left', 'text_wrap':True})
        worksheet.set_default_row(28)
        # 엑셀 열 너비 설정
        for i, width in enumerate([13, 6, 15, 18, 15, 40, 7, 15, 8]):
            worksheet.set_column(i, i, width, wrap_fmt if i == 5 else cell_fmt)
    return output.getvalue()

# 3. 데이터 추출 및 정렬
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
                    '날짜': dt_str, '요일': ['월','화','수','목','금','토','일'][d_obj.weekday()],
                    '건물명': str(item.get('buNm', '')).strip(),
                    '장소': item.get('placeNm', '') or '-',
                    '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                    '행사명': item.get('eventNm', '') or '-',
                    '인원': str(item.get('peopleCount', '-')),
                    '부서': item.get('mgDeptNm', '') or '-',
                    '상태': '확정' if item.get('status') == 'Y' else '대기',
                    '_dt': d_obj, '_tm': item.get('startTime', '00:00')
                })
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        return df.sort_values(by=['_dt', 'b_idx', '_tm'])
    except: return pd.DataFrame()

# 4. 화면 레이아웃 (모바일 가시성 극대화)
st.sidebar.title("📅 설정")
s_in = st.sidebar.date_input("날짜", value=now_today)
sel_bu = st.sidebar.multiselect("건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(s_in, s_in) # 시작일=종료일로 고정 (조회 편의성)

st.markdown(f"### 🗓️ {s_in} 대관 요약")

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    
    with st.sidebar:
        st.write("---")
        ex_bin = create_excel_automated(f_df)
        st.download_button("📥 전체 엑셀 다운로드", data=ex_bin, file_name=f"대관_{s_in}.xlsx", use_container_width=True)

    # [중요] 건물별로 정보를 걸러서 '핵심 정보'만 노출
    for b_name in BUILDING_ORDER:
        if b_name in f_df['건물명'].values:
            b_data = f_df[f_df['건물명'] == b_name]
            
            st.markdown(f"#### 📍 {b_name}")
            
            # 모바일 화면 공간 확보를 위해 불필요한 열 제거
            # 날짜, 요일, 건물명은 이미 상단에 있으므로 표에서 제외
            display_df = b_data[['시간', '장소', '행사명', '부서']].copy()
            
            # 표 출력
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True # 인덱스 번호 숨기기
            )
else:
    st.info("조회된 데이터가 없습니다.")
