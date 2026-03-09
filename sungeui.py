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

# 2. CSS 설정 (PC용 표 디자인 유지 + 헤더 흑백 대비 및 중앙정렬)
st.markdown("""
<style>
    .main-title { font-size: 26px !important; font-weight: bold; margin-bottom: 30px; }
    .building-header {
        font-size: 22px !important; font-weight: bold; color: #2E5077;
        margin-top: 25px; margin-bottom: 10px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    .no-data-msg {
        color: #888; font-style: italic; padding: 10px; margin-bottom: 20px;
    }
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .custom-table th, .custom-table td { border: 1px solid #dee2e6; padding: 10px 6px !important; font-size: 14px; vertical-align: middle !important; }
    
    /* 헤더: 중앙 정렬 및 흑백 대비 강화 */
    .custom-table th {
        background-color: #333333 !important; color: #ffffff !important;
        text-align: center !important; font-weight: bold;
    }

    /* 열별 정렬 설정 */
    .custom-table td:nth-child(1) { text-align: center !important; } /* 날짜 */
    .custom-table td:nth-child(2) { text-align: left !important; padding-left: 8px !important; } /* 강의실 */
    .custom-table td:nth-child(3), .custom-table td:nth-child(4) { text-align: center !important; } /* 시작/종료 */
    .custom-table td:nth-child(5) { text-align: left !important; padding-left: 8px !important; word-break: keep-all; } /* 행사명 */
    .custom-table td:nth-child(6) { text-align: left !important; padding-left: 8px !important; } /* 관리부서 */
    .custom-table td:nth-child(7) { text-align: center !important; } /* 상태 */
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🏫 성의교정 시설 대관 실시간 현황</div>', unsafe_allow_html=True)

# 3. 사이드바 설정
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date(2026, 3, 10))
end_selected = col2.date_input("종료일", value=date(2026, 3, 14))

# 4. 데이터 추출 로직 (휴대폰용 소스 참조 방식)
@st.cache_data(ttl=300)
def get_processed_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.strftime('%Y-%m-%d'), "end": e_date.strftime('%Y-%m-%d')}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    try:
        res = requests.get(url, params=params, headers=headers)
        raw_list = res.json().get('res', [])
        
        expanded_rows = []
        for item in raw_list:
            item_start = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_end = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # [참조 로직] 요일 리스트 생성 (월:1 ~ 일:7)
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]

            curr_dt = item_start
            while curr_dt <= item_end:
                # 사용자가 선택한 기간 내의 날짜만 처리
                if s_date <= curr_dt <= e_date:
                    # [참조 로직] 요일 계산 및 필터링
                    target_weekday = str(curr_dt.weekday() + 1)
                    
                    is_today = (item['startDt'] == item['endDt'])
                    if is_today or (target_weekday in allow_days):
                        expanded_rows.append({
                            '날짜': curr_dt.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시작': item.get('startTime', ''),
                            '종료': item.get('endTime', ''),
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '예약확정' if item.get('status') == 'Y' else '신청대기'
                        })
                curr_dt += timedelta(days=1)
        return pd.DataFrame(expanded_rows)
    except:
        return pd.DataFrame()

# 데이터 실행
df = get_processed_data(start_selected, end_selected)

# 5. 결과 출력 (PC용 표 형태)
selected_bu = st.sidebar.multiselect("조회할 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    if not df.empty:
        # [참조 로직] 건물명 공백 제거 후 매칭
        target_bu_clean = bu.replace(" ", "")
        bu_df = df[df['건물명'].str.replace(" ", "").str.contains(target_bu_clean, na=False)].copy()
        
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by=['날짜', '시작'])
            table_display = bu_df.drop(columns=['건물명']).reset_index(drop=True)
            html_table = table_display.to_html(classes='custom-table', index=False, escape=False)
            st.markdown(html_table, unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# 6. 엑셀 다운로드 (사이드바)
if not df.empty:
    st.sidebar.markdown("---")
    download_df = df[df['건물명'].isin(selected_bu)].copy()
    if not download_df.empty:
        download_df['건물명'] = pd.Categorical(download_df['건물명'], categories=BUILDING_ORDER, ordered=True)
        download_df = download_df.sort_values(['건물명', '날짜', '시작'])
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            download_df.to_excel(writer, index=False)
        
        st.sidebar.download_button(
            label="📥 현재 리스트 엑셀 저장",
            data=output.getvalue(),
            file_name=f"대관현황_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
