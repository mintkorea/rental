import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

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
# 현재 날짜 기준으로 기본값 설정
start_selected = col1.date_input("시작일", value=date(2026, 3, 10))
end_selected = col2.date_input("종료일", value=date(2026, 3, 14))

# 3. 데이터 로드 및 처리 함수
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
        raw_data = res.json().get('res', [])
        
        expanded_rows = []
        for item in raw_data:
            # 시작일과 종료일 파싱
            item_start = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_end = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # allowDay 파싱 (예: "2,3,4" -> [2, 3, 4])
            # 서버 기준 요일: 1(일), 2(월), 3(화), 4(수), 5(목), 6(금), 7(토)
            allow_days = []
            if item.get('allowDay'):
                try:
                    allow_days = [int(d.strip()) for d in str(item['allowDay']).split(',') if d.strip()]
                except ValueError:
                    allow_days = []

            # 기간 내의 모든 날짜를 순회하며 조건 체크
            curr_dt = item_start
            while curr_dt <= item_end:
                # 1. 사용자가 선택한 조회 범위 내에 있는지 확인
                if s_date <= curr_dt <= e_date:
                    # 요일 계산 (Python: 0=월 ~ 6=일) -> (Server: 2=월 ~ 1=일)
                    py_wd = curr_dt.weekday()
                    server_wd = 1 if py_wd == 6 else py_wd + 2
                    
                    # 2. allowDay 조건 확인 (비어있으면 매일로 간주하거나, 해당 요일이 포함되어야 함)
                    if not allow_days or server_wd in allow_days:
                        row = item.copy()
                        row['actualDate'] = curr_dt  # 실제 표시될 날짜
                        expanded_rows.append(row)
                
                curr_dt += timedelta(days=1)
                
        return pd.DataFrame(expanded_rows)
    except Exception as e:
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 데이터 실행
df_expanded = get_processed_data(start_selected, end_selected)

if not df_expanded.empty:
    # 필요한 컬럼만 추출 및 이름 변경
    df = df_expanded[['actualDate','buNm','placeNm','startTime','endTime','eventNm','mgDeptNm','status']].copy()
    df.columns = ['날짜', '건물명', '강의실', '시작', '종료', '행사명', '관리부서', '상태']
    
    # 상태 및 텍스트 정제
    df['상태'] = df['상태'].map({'Y': '예약확정', 'N': '신청대기'}).fillna('기타')
    df['건물명'] = df['건물명'].str.strip()
    
    # 건물 선택 필터
    all_bu = sorted(df['건물명'].unique())
    selected_bu = st.sidebar.multiselect("조회할 건물", options=all_bu, default=all_bu)

    # 4. 건물별 출력
    for bu in selected_bu:
        bu_df = df[df['건물명'] == bu].sort_values(by=['날짜', '시작'])
        if not bu_df.empty:
            st.markdown(f'<div class="building-header">🏢 {bu} (총 {len(bu_df)}건)</div>', unsafe_allow_html=True)
            
            # 테이블용 데이터 (건물명 제외)
            table_display = bu_df.drop(columns=['건물명']).reset_index(drop=True)
            
            # HTML 변환 및 출력
            html_table = table_display.to_html(classes='custom-table', index=False, escape=False)
            st.markdown(html_table, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

    # 5. 엑셀 다운로드
    st.sidebar.markdown("---")
    final_view = df[df['건물명'].isin(selected_bu)].sort_values(by=['날짜', '건물명', '시작'])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        final_view.to_excel(writer, index=False)

    st.sidebar.download_button(
        label="📥 현재 리스트 엑셀 저장",
        data=output.getvalue(),
        file_name=f"성의교정_대관현황_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.info("선택하신 기간 및 건물에 대한 예약 내역이 없습니다.")
