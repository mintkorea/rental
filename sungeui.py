import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 현황", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 노출 순서 고정
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 엑셀 자동화 (전체 항목 포함 및 서식 적용)
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
        # 엑셀 열 너비 (전체 항목 기준)
        widths = [13, 6, 15, 18, 15, 40, 7, 15, 8]
        for i, width in enumerate(widths):
            worksheet.set_column(i, i, width, wrap_fmt if i == 5 else cell_fmt)
    return output.getvalue()

# 3. 데이터 추출 및 정렬 로직
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

# 4. 화면 레이아웃
st.sidebar.title("📅 설정")
date_in = st.sidebar.date_input("조회 날짜", value=now_today)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(date_in, date_in)

st.markdown(f"### 🗓️ {date_in} 대관 상세")

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    
    with st.sidebar:
        st.write("---")
        ex_bin = create_excel_automated(f_df)
        st.download_button("📥 전체 내역 엑셀 다운로드", data=ex_bin, file_name=f"대관_{date_in}.xlsx", use_container_width=True)

    # 건물별 순차 노출
    for b_name in BUILDING_ORDER:
        if b_name in sel_bu: # 필터링에서 선택된 건물만 표시
            st.markdown(f"#### 📍 {b_name}")
            b_data = f_df[f_df['건물명'] == b_name]
            
            if not b_data.empty:
                # 요청사항 반영: 시간-장소-행사명 순서 및 인원/상태 추가
                display_cols = ['시간', '장소', '행사명', '인원', '부서', '상태']
                st.dataframe(b_data[display_cols], use_container_width=True, hide_index=True)
            else:
                # 대관 정보가 없는 경우 메시지 노출
                st.info(f"해당 일자에 {b_name} 대관 내역이 없습니다.")
else:
    st.warning("조회된 전체 데이터가 없습니다.")
