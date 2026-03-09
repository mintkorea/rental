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

# CSS 설정: 헤더 가독성 및 테이블 최적화
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
    
    /* 헤더: 흑백 배경에서도 글씨가 잘 보이도록 반전 대비 적용 */
    .custom-table th {
        background-color: #333333 !important;
        color: #ffffff !important;
        text-align: center !important;
        font-weight: bold;
    }

    /* --- 열별 너비 재조정 --- */
    .custom-table th:nth-child(1), .custom-table td:nth-child(1) { width: 95px; text-align: center !important; }
    .custom-table th:nth-child(2), .custom-table td:nth-child(2) { width: 18%; text-align: left !important; padding-left: 8px !important; }
    .custom-table th:nth-child(3), .custom-table td:nth-child(3),
    .custom-table th:nth-child(4), .custom-table td:nth-child(4) { width: 60px; text-align: center !important; white-space: nowrap; }
    .custom-table th:nth-child(5), .custom-table td:nth-child(5) { width: auto; text-align: left !important; padding-left: 8px !important; word-break: keep-all; }
    .custom-table th:nth-child(6), .custom-table td:nth-child(6) { width: 18%; text-align: left !important; padding-left: 8px !important; }
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

if not df_raw.empty:
    df = df_raw[['actualDate','buNm','placeNm','startTime','endTime','eventNm','mgDeptNm','status']].copy()
    df.columns = ['날짜', '건물명', '강의실', '시작', '종료', '행사명', '관리부서', '상태']
    df['상태'] = df['상태'].map({'Y': '예약확정', 'N': '신청대기'}).fillna('기타')
    df['건물명'] = df['건물명'].str.strip()

    # --- 건물 순서 고정 로직 ---
    # 데이터에 있는 건물 중 정의된 리스트에 있는 것만 필터링하거나, 
    # 정의된 리스트를 기준으로 정렬 기준(Categorical) 설정
    present_bu = [b for b in BUILDING_ORDER if b in df['건물명'].unique()]
    # 정의되지 않은 건물이 데이터에 있다면 뒤에 붙여줌
    others = [b for b in df['건물명'].unique() if b not in BUILDING_ORDER]
    final_order = present_bu + others

    selected_bu = st.sidebar.multiselect("조회할 건물", options=final_order, default=present_bu)

    # 4. 건물별 출력 (정해진 순서대로)
    for bu in selected_bu:
        bu_df = df[df['건물명'] == bu].sort_values(by=['날짜', '시작'])
        if not bu_df.empty:
            st.markdown(f'<div class="building-header">🏢 {bu} (총 {len(bu_df)}건)</div>', unsafe_allow_html=True)
            table_display = bu_df.drop(columns=['건물명']).reset_index(drop=True)
            
            html_table = table_display.to_html(classes='custom-table', index=False, escape=False)
            st.markdown(html_table, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

    # 5. 엑셀 다운로드 (정렬 유지)
    st.sidebar.markdown("---")
    # 건물명을 Categorical로 변환하여 엑셀 저장 시에도 순서 유지
    df['건물명'] = pd.Categorical(df['건물명'], categories=final_order, ordered=True)
    final_view = df[df['건물명'].isin(selected_bu)].sort_values(by=['건물명', '날짜', '시작'])
    
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
    st.info("선택하신 기간 내에 예약 내역이 없습니다.")
