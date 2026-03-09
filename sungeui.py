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

# 2. CSS 설정: 모바일 반응형 및 열 너비 최적화
st.markdown("""
<style>
    /* 기본 여백 */
    .block-container { padding-top: 3.5rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
    
    .main-title { font-size: 24px !important; font-weight: bold; margin-bottom: 20px; color: #1E3A5F; }
    .building-header {
        font-size: 20px !important; font-weight: bold; color: #2E5077;
        margin-top: 25px; margin-bottom: 12px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    
    /* 테이블 기본 스타일 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; word-break: keep-all; }
    .custom-table th, .custom-table td { border: 1px solid #dee2e6; padding: 8px 4px !important; font-size: 13px; vertical-align: middle !important; }
    .custom-table th { background-color: #333333 !important; color: #ffffff !important; text-align: center !important; }

    /* 열 너비 설정 (PC 기준) */
    .custom-table th:nth-child(1), .custom-table td:nth-child(1) { width: 85px; text-align: center !important; } /* 날짜 */
    .custom-table th:nth-child(2), .custom-table td:nth-child(2) { width: 15%; text-align: left !important; } /* 강의실 */
    .custom-table th:nth-child(3), .custom-table td:nth-child(3),
    .custom-table th:nth-child(4), .custom-table td:nth-child(4) { width: 50px; text-align: center !important; } /* 시간 */
    .custom-table th:nth-child(5), .custom-table td:nth-child(5) { width: auto; text-align: left !important; } /* 행사명 */
    .custom-table th:nth-child(6), .custom-table td:nth-child(6) { width: 15%; text-align: left !important; } /* 관리부서 */
    .custom-table th:nth-child(7), .custom-table td:nth-child(7) { width: 65px; text-align: center !important; } /* 상태 */

    /* 모바일 반응형 (화면 폭 768px 이하) */
    @media (max-width: 768px) {
        .main-title { font-size: 20px !important; }
        .custom-table { table-layout: auto; } /* 모바일에서는 내용에 맞게 조절 */
        .custom-table th, .custom-table td { font-size: 11px; padding: 6px 2px !important; }
        
        /* 모바일에서 글자 세로 출력 방지 */
        .custom-table td { white-space: normal !important; overflow: visible !important; }
        
        /* 날짜 열 너비 축소 */
        .custom-table th:nth-child(1), .custom-table td:nth-child(1) { width: 65px !important; }
        /* 상태 열 숨기기 선택 (너무 좁을 경우) */
        /* .custom-table th:nth-child(7), .custom-table td:nth-child(7) { display: none; } */
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 및 날짜 설정
st.sidebar.header("🔍 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date.today())
end_selected = col2.date_input("종료일", value=date.today())

title_date = start_selected.strftime('%Y-%m-%d') if start_selected == end_selected else f"{start_selected.strftime('%Y-%m-%d')} ~ {end_selected.strftime('%Y-%m-%d')}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({title_date})</div>', unsafe_allow_html=True)

# 4. 데이터 로직 (생략 없이 유지)
@st.cache_data(ttl=300)
def get_processed_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.strftime('%Y-%m-%d'), "end": e_date.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
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
                    if (item['startDt'] == item['endDt']) or (target_weekday in allow_days):
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
    except: return pd.DataFrame()

df_all = get_processed_data(start_selected, end_selected)

# 5. 결과 표출 및 엑셀 데이터 준비
selected_bu = st.sidebar.multiselect("조회할 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)
export_list = []

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    target_bu_clean = bu.replace(" ", "")
    
    if not df_all.empty:
        bu_df = df_all[df_all['건물명'].str.replace(" ", "").str.contains(target_bu_clean, na=False)].copy()
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by=['날짜', '시작'])
            table_display = bu_df.drop(columns=['건물명']).reset_index(drop=True)
            # 웹 화면 출력
            st.markdown(table_display.to_html(classes='custom-table', index=False, escape=False), unsafe_allow_html=True)
            # 엑셀용 수집
            bu_df['건물명'] = bu
            export_list.append(bu_df)
        else:
            st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

# 6. 엑셀 다운로드 (화면 결과와 동일하게)
if export_list:
    df_export = pd.concat(export_list)
    df_export['건물명'] = pd.Categorical(df_export['건물명'], categories=BUILDING_ORDER, ordered=True)
    df_export = df_export.sort_values(by=['건물명', '날짜', '시작'])
    
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False)
    st.sidebar.download_button(
        label="📥 결과 엑셀 저장",
        data=output.getvalue(),
        file_name=f"대관현황_{title_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
