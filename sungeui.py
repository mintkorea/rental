import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# CSS 설정: 강의실/관리부서 너비 확장 및 줄바꿈 방지 최적화
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
    .custom-table th {
        background-color: #f8f9fa;
        text-align: center !important;
        font-weight: bold;
    }

    /* --- 열별 너비 재조정 --- */
    /* 1. 날짜: 고정 */
    .custom-table th:nth-child(1), .custom-table td:nth-child(1) { 
        width: 95px; text-align: center !important; 
    }
    
    /* 2. 강의실: 줄바꿈 방지를 위해 너비 확장 (기존 12% -> 18%) */
    .custom-table th:nth-child(2), .custom-table td:nth-child(2) { 
        width: 18%; text-align: left !important; padding-left: 8px !important; 
    }
    
    /* 3. 시작 & 4. 종료: 고정 */
    .custom-table th:nth-child(3), .custom-table td:nth-child(3),
    .custom-table th:nth-child(4), .custom-table td:nth-child(4) { 
        width: 60px; text-align: center !important; white-space: nowrap; 
    }
    
    /* 5. 행사명: 나머지 공간 활용 (자동 조절) */
    .custom-table th:nth-child(5), .custom-table td:nth-child(5) { 
        width: auto; text-align: left !important; padding-left: 8px !important; 
        word-break: keep-all; /* 단어 단위 줄바꿈으로 가독성 향상 */
    }
    
    /* 6. 관리부서: 줄바꿈 방지를 위해 너비 확장 (기존 12% -> 18%) */
    .custom-table th:nth-child(6), .custom-table td:nth-child(6) { 
        width: 18%; text-align: left !important; padding-left: 8px !important; 
    }
    
    /* 7. 상태: 고정 */
    .custom-table th:nth-child(7), .custom-table td:nth-child(7) { 
        width: 80px; text-align: center !important; 
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 실시간 현황</div>', unsafe_allow_html=True)

# 2. 사이드바 설정
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date(2026, 3, 10))
end_selected = col2.date_input("종료일", value=date(2026, 3, 14))

# 3. 데이터 로드
@st.cache_data(ttl=300)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {
        "mode": "getReservedData",
        "start": s_date.strftime('%Y-%m-%d'),
        "end": e_date.strftime('%Y-%m-%d')
    }
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(url, params=params, headers=headers)
        return pd.DataFrame(res.json().get('res', []))
    except:
        return pd.DataFrame()

df_raw = get_data(start_selected, end_selected)

if not df_raw.empty:
    # 데이터 전처리 및 날짜 필터링 보정
    df = df_raw[['startDt','buNm','placeNm','startTime','endTime','eventNm','mgDeptNm','status']].copy()
    
    # 서버 응답 데이터에서 선택한 기간만 엄격하게 필터링
    df['startDt'] = pd.to_datetime(df['startDt']).dt.date
    df = df[(df['startDt'] >= start_selected) & (df['startDt'] <= end_selected)]
    
    df.columns = ['날짜', '건물명', '강의실', '시작', '종료', '행사명', '관리부서', '상태']
    df['상태'] = df['상태'].map({'Y': '예약확정', 'N': '신청대기'}).fillna('기타')
    df['건물명'] = df['건물명'].str.strip()

    all_bu = sorted(df['건물명'].unique())
    selected_bu = st.sidebar.multiselect("조회할 건물", options=all_bu, default=all_bu)

    # 4. 건물별 출력
    for bu in selected_bu:
        bu_df = df[df['건물명'] == bu].sort_values(by=['날짜','시작'])
        if not bu_df.empty:
            st.markdown(f'<div class="building-header">🏢 {bu} (총 {len(bu_df)}건)</div>', unsafe_allow_html=True)
            table_df = bu_df.drop(columns=['건물명']).reset_index(drop=True)
            
            # HTML 변환 및 출력
            html_table = table_df.to_html(classes='custom-table', index=False, escape=False)
            st.markdown(html_table, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

    # 5. 엑셀 다운로드
    st.sidebar.markdown("---")
    final_view = df[df['건물명'].isin(selected_bu)].sort_values(by=['건물명','날짜','시작'])
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
    st.info("선택하신 기간 및 건물에 대한 데이터가 없습니다.")
