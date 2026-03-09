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

# 2. CSS 설정 (상단 여백 및 열 너비 조정)
st.markdown("""
<style>
    .block-container { padding-top: 3.5rem !important; }
    .main-title { 
        font-size: 28px !important; 
        font-weight: bold; 
        margin-top: 10px; margin-bottom: 25px; color: #1E3A5F;
    }
    .building-header {
        font-size: 22px !important; font-weight: bold; color: #2E5077;
        margin-top: 10px; margin-bottom: 12px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    .no-data-msg { color: #888; font-style: italic; padding: 10px; margin-bottom: 20px; }
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .custom-table th, .custom-table td { border: 1px solid #dee2e6; padding: 10px 6px !important; font-size: 14px; vertical-align: middle !important; }
    .custom-table th { background-color: #333333 !important; color: #ffffff !important; text-align: center !important; font-weight: bold; }

    /* 열 너비 설정 */
    .custom-table th:nth-child(1), .custom-table td:nth-child(1) { width: 90px; text-align: center !important; } 
    .custom-table th:nth-child(2), .custom-table td:nth-child(2) { width: 15%; text-align: left !important; padding-left: 8px !important; } 
    .custom-table th:nth-child(3), .custom-table td:nth-child(3),
    .custom-table th:nth-child(4), .custom-table td:nth-child(4) { width: 55px; text-align: center !important; } 
    .custom-table th:nth-child(5), .custom-table td:nth-child(5) { width: auto; text-align: left !important; padding-left: 8px !important; word-break: break-all; } 
    .custom-table th:nth-child(6), .custom-table td:nth-child(6) { width: 15%; text-align: left !important; padding-left: 8px !important; } 
    .custom-table th:nth-child(7), .custom-table td:nth-child(7) { width: 75px; text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date.today())
end_selected = col2.date_input("종료일", value=date.today())

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
    except:
        return pd.DataFrame()

df_all = get_processed_data(start_selected, end_selected)

# 5. 결과 출력 및 다운로드 데이터 준비
selected_bu = st.sidebar.multiselect("조회할 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 화면 출력 및 엑셀용 리스트 초기화
export_list = []

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    
    # 건물명 공백 제거 매칭
    target_bu_clean = bu.replace(" ", "")
    if not df_all.empty:
        bu_df = df_all[df_all['건물명'].str.replace(" ", "").str.contains(target_bu_clean, na=False)].copy()
        
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by=['날짜', '시작'])
            # 웹 화면 출력
            table_display = bu_df.drop(columns=['건물명']).reset_index(drop=True)
            st.markdown(table_display.to_html(classes='custom-table', index=False, escape=False), unsafe_allow_html=True)
            
            # 엑셀 저장용 데이터에 추가 (건물명 포함)
            bu_df['건물명'] = bu # 명칭 통일
            export_list.append(bu_df)
        else:
            st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

# 6. 엑셀 다운로드 처리 (선택된 순서와 데이터 반영)
if export_list:
    df_export = pd.concat(export_list)
    # 엑셀에서도 건물 순서를 BUILDING_ORDER 기준으로 고정
    df_export['건물명'] = pd.Categorical(df_export['건물명'], categories=BUILDING_ORDER, ordered=True)
    df_export = df_export.sort_values(by=['건물명', '날짜', '시작'])
    
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False)
    
    st.sidebar.download_button(
        label="📥 현재 검색 결과 엑셀 저장",
        data=output.getvalue(),
        file_name=f"성의교정_대관현황_{title_date}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
