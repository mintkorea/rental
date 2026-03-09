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
    .main-title { font-size: 26px !important; font-weight: bold; margin-bottom: 30px; }
    .building-header {
        font-size: 22px !important; font-weight: bold; color: #2E5077;
        margin-top: 25px; margin-bottom: 10px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    .no-data-msg {
        color: #888; font-style: italic; padding: 15px; 
        border: 1px dashed #ddd; border-radius: 5px; margin-bottom: 20px;
    }
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    .custom-table th, .custom-table td { border: 1px solid #dee2e6; padding: 10px 6px !important; font-size: 14px; vertical-align: middle !important; }
    
    /* 헤더: 중앙 정렬 및 흑백 대비 강화 */
    .custom-table th {
        background-color: #333333 !important; color: #ffffff !important;
        text-align: center !important; font-weight: bold;
    }

    /* 열별 정렬 및 너비 */
    .custom-table td:nth-child(1) { text-align: center !important; } /* 날짜 */
    .custom-table td:nth-child(2) { text-align: left !important; padding-left: 10px !important; } /* 강의실 */
    .custom-table td:nth-child(3), .custom-table td:nth-child(4) { text-align: center !important; } /* 시간 */
    .custom-table td:nth-child(5) { text-align: left !important; padding-left: 10px !important; } /* 행사명 */
    .custom-table td:nth-child(6) { text-align: left !important; padding-left: 10px !important; } /* 부서 */
    .custom-table td:nth-child(7) { text-align: center !important; } /* 상태 */
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 실시간 현황</div>', unsafe_allow_html=True)

# 2. 사이드바 설정
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date(2026, 3, 10))
end_selected = col2.date_input("종료일", value=date(2026, 3, 14))

# 3. 데이터 로드 및 정밀 처리 함수
@st.cache_data(ttl=300)
def get_processed_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {
        "mode": "getReservedData",
        "start": s_date.strftime('%Y-%m-%d'),
        "end": e_date.strftime('%Y-%m-%d')
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    try:
        res = requests.get(url, params=params, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        raw_list = data.get('res', [])
        
        if not raw_list:
            return pd.DataFrame()

        expanded_rows = []
        for item in raw_list:
            try:
                # 날짜 파싱 (에러 방지를 위한 처리)
                item_start = datetime.strptime(item.get('startDt', ''), '%Y-%m-%d').date()
                item_end = datetime.strptime(item.get('endDt', ''), '%Y-%m-%d').date()
                
                # 요일 파싱 (1:일, 2:월 ... 7:토)
                allow_days = []
                raw_allow = str(item.get('allowDay', ''))
                if raw_allow and raw_allow != 'None':
                    allow_days = [int(d.strip()) for d in raw_allow.split(',') if d.strip().isdigit()]

                curr_dt = item_start
                while curr_dt <= item_end:
                    # 선택한 조회 기간 내에 있는 날짜만 처리
                    if s_date <= curr_dt <= e_date:
                        py_wd = curr_dt.weekday() # 0:월 ~ 6:일
                        server_wd = 1 if py_wd == 6 else py_wd + 2
                        
                        # 요일 조건 확인
                        if not allow_days or server_wd in allow_days:
                            new_row = {
                                '날짜': curr_dt.strftime('%Y-%m-%d'),
                                '건물명': str(item.get('buNm', '')).strip(),
                                '강의실': item.get('placeNm', ''),
                                '시작': item.get('startTime', ''),
                                '종료': item.get('endTime', ''),
                                '행사명': item.get('eventNm', ''),
                                '관리부서': item.get('mgDeptNm', ''),
                                '상태': '예약확정' if item.get('status') == 'Y' else '신청대기'
                            }
                            expanded_rows.append(new_row)
                    curr_dt += timedelta(days=1)
            except Exception:
                continue # 개별 데이터 오류 시 해당 행 건너뜀
                
        return pd.DataFrame(expanded_rows)
    except Exception as e:
        st.error(f"데이터 연동 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# 데이터 실행
df = get_processed_data(start_selected, end_selected)

# 4. 결과 출력 로직
selected_bu = st.sidebar.multiselect("조회할 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # 해당 건물 데이터 필터링
        bu_df = df[df['건물명'] == bu].sort_values(by=['날짜', '시작'])
        
        if not bu_df.empty:
            # 출력용 테이블 (건물명 열은 제외)
            display_df = bu_df.drop(columns=['건물명'])
            html_table = display_df.to_html(classes='custom-table', index=False, escape=False)
            # 헤더 중앙 정렬 강제 적용을 위한 처리
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# 5. 엑셀 다운로드 (사이드바)
if not df.empty:
    st.sidebar.markdown("---")
    # 선택된 건물만 포함하여 엑셀 생성
    download_df = df[df['건물명'].isin(selected_bu)].copy()
    # 건물 순서대로 정렬하기 위해 Categorical 적용
    download_df['건물명'] = pd.Categorical(download_df['건물명'], categories=BUILDING_ORDER, ordered=True)
    download_df = download_df.sort_values(['건물명', '날짜', '시작'])
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        download_df.to_excel(writer, index=False)
    
    st.sidebar.download_button(
        label="📥 현재 리스트 엑셀 저장",
        data=output.getvalue(),
        file_name=f"성의교정_대관현황_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
