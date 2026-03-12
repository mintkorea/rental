import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 현황", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 엑셀 자동화 (모든 데이터 포함 및 서식 적용)
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
        widths = [13, 6, 15, 18, 15, 40, 7, 18, 10]
        for i, width in enumerate(widths):
            worksheet.set_column(i, i, width, wrap_fmt if i == 5 else cell_fmt)
    return output.getvalue()

# 3. 데이터 수집 (기간 대관 완벽 대응)
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {
        "mode": "getReservedData", 
        "start": (target_date - timedelta(days=1)).isoformat(), 
        "end": (target_date + timedelta(days=1)).isoformat()
    }
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            s_dt = (item.get('startDt') or item.get('start')).split('T')[0]
            e_dt = (item.get('endDt') or item.get('end') or s_dt).split('T')[0]
            s_obj = datetime.strptime(s_dt, '%Y-%m-%d').date()
            e_obj = datetime.strptime(e_dt, '%Y-%m-%d').date()
            
            if s_obj <= target_date <= e_obj:
                rows.append({
                    '날짜': target_date.isoformat(),
                    '요일': ['월','화','수','목','금','토','일'][target_date.weekday()],
                    '건물명': str(item.get('buNm', '')).strip(),
                    '장소': item.get('placeNm', '') or '-',
                    '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                    '행사명': item.get('eventNm', '') or '-',
                    '인원': str(item.get('peopleCount', '0')),
                    '부서': item.get('mgDeptNm', '') or '-',
                    '상태': '확정' if item.get('status') == 'Y' else '대기',
                    '_tm': item.get('startTime', '00:00')
                })
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        return df.sort_values(by=['b_idx', '_tm']).drop_duplicates()
    except: return pd.DataFrame()

# 4. 화면 구성
st.sidebar.title("📅 대관 설정")
date_in = st.sidebar.date_input("날짜 선택", value=now_today)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(date_in)

st.markdown(f"### 🗓️ {date_in} 대관 리스트")

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    
    with st.sidebar:
        st.write("---")
        ex_bin = create_excel_automated(f_df)
        st.download_button("📥 전체 엑셀 다운로드", data=ex_bin, file_name=f"대관_{date_in}.xlsx", use_container_width=True)

    for b_name in BUILDING_ORDER:
        if b_name in sel_bu:
            st.markdown(f"#### 📍 {b_name}")
            b_data = f_df[f_df['건물명'] == b_name]
            
            if not b_data.empty:
                # [요청반영] 장소 - 시간 - 행사명 순서로 재배치
                display_cols = ['장소', '시간', '행사명', '인원', '상태', '부서']
                st.dataframe(b_data[display_cols], use_container_width=True, hide_index=True)
            else:
                st.info(f"해당 일자에 {b_name} 대관 내역이 없습니다.")
else:
    st.warning("⚠️ 조회된 데이터가 없습니다.")
