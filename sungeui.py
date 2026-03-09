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

# 2. CSS 설정 (여백 및 열 너비 조정)
st.markdown("""
<style>
    /* 상단 여백 최소화 */
    .block-container { padding-top: 2rem !important; }
    
    .main-title { 
        font-size: 26px !important; 
        font-weight: bold; 
        margin-bottom: 20px; 
        color: #1E3A5F;
    }
    .building-header {
        font-size: 22px !important; font-weight: bold; color: #2E5077;
        margin-top: 10px; margin-bottom: 10px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    .no-data-msg { color: #888; font-style: italic; padding: 10px; margin-bottom: 20px; }
    
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .custom-table th, .custom-table td { border: 1px solid #dee2e6; padding: 10px 6px !important; font-size: 14px; vertical-align: middle !important; }
    
    /* 헤더: 중앙 정렬 및 흑백 대비 강화 */
    .custom-table th {
        background-color: #333333 !important; color: #ffffff !important;
        text-align: center !important; font-weight: bold;
    }

    /* --- [열 너비 설정] --- */
    .custom-table th:nth-child(1), .custom-table td:nth-child(1) { width: 90px; text-align: center !important; } 
    .custom-table th:nth-child(2), .custom-table td:nth-child(2) { width: 15%; text-align: left !important; padding-left: 8px !important; } 
    .custom-table th:nth-child(3), .custom-table td:nth-child(3),
    .custom-table th:nth-child(4), .custom-table td:nth-child(4) { width: 55px; text-align: center !important; white-space: nowrap; } 
    .custom-table th:nth-child(5), .custom-table td:nth-child(5) { width: auto; text-align: left !important; padding-left: 8px !important; word-break: break-all; } 
    .custom-table th:nth-child(6), .custom-table td:nth-child(6) { width: 15%; text-align: left !important; padding-left: 8px !important; } 
    .custom-table th:nth-child(7), .custom-table td:nth-child(7) { width: 75px; text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date(2026, 3, 10))
end_selected = col2.date_input("종료일", value=date(2026, 3, 14))

# 메인 타이틀 동적 생성 로직
if start_selected == end_selected:
    title_date = start_selected.strftime('%Y-%m-%d')
else:
    title_date = f"{start_selected.strftime('%Y-%m-%d')} ~ {end_selected.strftime('%Y-%m-%d')}"

st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({title_date})</div>', unsafe_allow_html=True)

# 4. 데이터 추출 로직
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
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]

            curr_dt = item_start
            while curr_dt <= item_end:
                if s_date <= curr_dt <= e_date:
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

df = get_processed_data(start_selected, end_selected)

# 5. 결과 출력
selected_bu = st.sidebar.multiselect("조회할 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    if not df.empty:
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

# 6. 엑셀 다운로드
if not df.empty:
    st.sidebar.markdown("---")
    final_view = df.copy()
    if not final_view.empty:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            final_view.to_excel(writer, index=False)
        st.sidebar.download_button(
            label="📥 현재 리스트 엑셀 저장",
            data=output.getvalue(),
            file_name=f"성의교정_대관현황_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
