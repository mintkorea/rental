import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 고정된 건물 순서 정의
BUILDING_ORDER = [
    "성의회관",
    "의생명산업연구원",
    "옴니버스파크",
    "옴니버스파크 의과대학",
    "옴니버스파크 간호대학",
    "대학본관",
    "서울성모별관"
]

# CSS 설정
st.markdown("""
<style>
    .main-title {
        font-size: 26px !important;
        font-weight: bold;
        margin-bottom: 30px;
    }
    .building-header {
        font-size: 22px !important;
        font-weight: bold;
        color: #2E5077;
        margin-top: 25px;
        margin-bottom: 10px;
        padding-left: 5px;
        border-left: 5px solid #2E5077;
    }
    .no-data-msg {
        color: #666;
        font-style: italic;
        padding: 10px;
        border: 1px dashed #ccc;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        table-layout: fixed;
    }
    .custom-table th, .custom-table td {
        border: 1px solid #dee2e6;
        padding: 10px 6px !important;
        font-size: 14px;
        vertical-align: middle !important;
    }
    
    /* 헤더: 중앙 정렬 및 고대비 색상 적용 */
    .custom-table th {
        background-color: #333333 !important;
        color: #ffffff !important;
        text-align: center !important;
        font-weight: bold;
    }

    /* --- 열별 너비 및 정렬 설정 --- */
    /* 1. 날짜 */
    .custom-table th:nth-child(1), .custom-table td:nth-child(1) { width: 95px; text-align: center !important; }
    /* 2. 강의실 */
    .custom-table th:nth-child(2), .custom-table td:nth-child(2) { width: 18%; text-align: left !important; padding-left: 8px !important; }
    /* 3. 시작 & 4. 종료 */
    .custom-table th:nth-child(3), .custom-table td:nth-child(3),
    .custom-table th:nth-child(4), .custom-table td:nth-child(4) { width: 60px; text-align: center !important; white-space: nowrap; }
    /* 5. 행사명 */
    .custom-table th:nth-child(5), .custom-table td:nth-child(5) { width: auto; text-align: left !important; padding-left: 8px !important; word-break: keep-all; }
    /* 6. 관리부서 */
    .custom-table th:nth-child(6), .custom-table td:nth-child(6) { width: 18%; text-align: left !important; padding-left: 8px !important; }
    /* 7. 상태 */
    .custom-table th:nth-child(7), .custom-table td:nth-child(7) { width: 80px; text-align: center !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 실시간 현황</div>', unsafe_allow_html=True)

# 2. 사이드바 설정
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date(2026, 3, 10))
end_selected = col2.date_input("종료일", value=date(2026, 3, 14))

# 3. 데이터 로드 및 처리
@st.cache_data(ttl=300)
def get_processed_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {
        "mode": "getReservedData",
        "start": s_date.strftime('%Y-%m-%d'),
        "end": e_date.strftime('%Y-%m-%d')
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, params=params, headers=headers)
        raw_list = res.json().get('res', [])
        
        expanded_rows = []
        for item in raw_list:
            item_start = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_end = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            allow_days = []
            if item.get('allowDay'):
                allow_days = [int(d.strip()) for d in str(item['allowDay']).split(',') if d.strip()]

            curr_dt = item_start
            while curr_dt <= item_end:
                if s_date <= curr_dt <= e_date:
                    py_wd = curr_dt.weekday()
                    server_wd = 1 if py_wd == 6 else py_wd + 2
                    if not allow_days or server_wd in allow_days:
                        row = item.copy()
                        row['actualDate'] = curr_dt
                        expanded_rows.append(row)
                curr_dt += timedelta(days=1)
        return pd.DataFrame(expanded_rows)
    except:
        return pd.DataFrame()

df_raw = get_processed_data(start_selected, end_selected)

# 4. 결과 표출
selected_bu = st.sidebar.multiselect("조회할 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

if not df_raw.empty:
    df = df_raw[['actualDate','buNm','placeNm','startTime','endTime','eventNm','mgDeptNm','status']].copy()
    df.columns = ['날짜', '건물명', '강의실', '시작', '종료', '행사명', '관리부서', '상태']
    df['상태'] = df['상태'].map({'Y': '예약확정', 'N': '신청대기'}).fillna('기타')
    df['건물명'] = df['건물명'].str.strip()

    for bu in selected_bu:
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        bu_df = df[df['건물명'] == bu].sort_values(by=['날짜', '시작'])
        
        if not bu_df.empty:
            table_display = bu_df.drop(columns=['건물명']).reset_index(drop=True)
            html_table = table_display.to_html(classes='custom-table', index=False, escape=False)
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

    # 5. 엑셀 다운로드
    st.sidebar.markdown("---")
    final_view = df[df['건물명'].isin(selected_bu)].copy()
    final_view['건물명'] = pd.Categorical(final_view['건물명'], categories=BUILDING_ORDER, ordered=True)
    final_view = final_view.sort_values(by=['건물명', '날짜', '시작'])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_view.to_excel(writer, index=False)

    st.sidebar.download_button(
        label="📥 현재 리스트 엑셀 저장",
        data=output.getvalue(),
        file_name=f"대관현황_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    # 데이터 자체가 없는 경우 모든 선택 건물에 대해 메시지 표시
    for bu in selected_bu:
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    st.info("해당 기간에 전체 예약 데이터가 존재하지 않습니다.")
