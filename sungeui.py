import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 고정된 건물 순서 정의
BUILDING_ORDER = [
    "성의회관", "의생명산업연구원", "옴니버스파크", 
    "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"
]

# 2. CSS 설정 (HTML 렌더링 및 모바일 최적화)
st.markdown("""
<style>
    /* 상단 잘림 방지 및 확대/축소 고려 */
    .block-container { padding-top: 4rem !important; }
    
    .main-title { font-size: 26px !important; font-weight: bold; margin-bottom: 20px; color: #1E3A5F; }
    .building-header {
        font-size: 20px !important; font-weight: bold; color: #2E5077;
        margin-top: 25px; margin-bottom: 12px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    
    /* 테이블 스타일: 헤더 중앙 정렬 및 선명도 강화 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 30px; }
    .custom-table th { 
        background-color: #333333 !important; color: #ffffff !important; 
        text-align: center !important; font-weight: bold; padding: 12px 4px;
        border: 1px solid #444;
    }
    .custom-table td { 
        border: 1px solid #dee2e6; padding: 10px 6px !important; 
        font-size: 14px; vertical-align: middle !important; 
        word-break: break-all;
    }

    /* 열 너비 설정 (PC) */
    .col-date { width: 110px; }
    .col-place { width: 15%; }
    .col-time { width: 130px; }
    .col-event { width: auto; }
    .col-dept { width: 15%; }
    .col-status { width: 85px; }

    /* 모바일 대응: 가로 768px 이하 */
    @media (max-width: 768px) {
        .custom-table { table-layout: auto; }
        .custom-table th, .custom-table td { font-size: 12px; padding: 8px 4px !important; }
        .col-date { width: 85px !important; }
        .col-time { width: 100px !important; }
        .col-status { width: 70px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정 (기본값: Today)
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date.today())
end_selected = col2.date_input("종료일", value=date.today())

# 메인 타이틀 (날짜/기간 표시)
title_date = start_selected.strftime('%Y-%m-%d') if start_selected == end_selected else f"{start_selected.strftime('%Y-%m-%d')} ~ {end_selected.strftime('%Y-%m-%d')}"
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
                        # 시간 표시 포맷팅 (시작 ~ 종료)
                        time_display = f"{item.get('startTime', '')} ~ {item.get('endTime', '')}"
                        
                        expanded_rows.append({
                            '날짜': curr_dt.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': time_display,
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '예약확정' if item.get('status') == 'Y' else '신청대기',
                            'raw_start': item.get('startTime', '')
                        })
                curr_dt += timedelta(days=1)
        return pd.DataFrame(expanded_rows)
    except: return pd.DataFrame()

df_all = get_processed_data(start_selected, end_selected)

# 5. 결과 출력
selected_bu = st.sidebar.multiselect("조회할 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)
export_list = []

for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    target_bu_clean = bu.replace(" ", "")
    
    if not df_all.empty:
        bu_df = df_all[df_all['건물명'].str.replace(" ", "").str.contains(target_bu_clean, na=False)].copy()
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by=['날짜', 'raw_start'])
            
            # HTML 테이블 생성 (인덱스 제거 버전)
            table_html = f"""
            <table class="custom-table">
                <thead>
                    <tr>
                        <th class="col-date">날짜</th>
                        <th class="col-place">강의실</th>
                        <th class="col-time">시간</th>
                        <th class="col-event">행사명</th>
                        <th class="col-dept">관리부서</th>
                        <th class="col-status">상태</th>
                    </tr>
                </thead>
                <tbody>
            """
            for _, row in bu_df.iterrows():
                table_html += f"""
                    <tr>
                        <td style="text-align:center;">{row['날짜']}</td>
                        <td style="text-align:left;">{row['강의실']}</td>
                        <td style="text-align:center;">{row['시간']}</td>
                        <td style="text-align:left;">{row['행사명']}</td>
                        <td style="text-align:left;">{row['관리부서']}</td>
                        <td style="text-align:center;">{row['상태']}</td>
                    </tr>
                """
            table_html += "</tbody></table>"
            
            # 화면에 실제 HTML 표로 렌더링
            st.markdown(table_html, unsafe_allow_html=True)
            export_list.append(bu_df)
        else:
            st.markdown('<div style="color:#888; font-style:italic; margin-bottom:20px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#888; font-style:italic; margin-bottom:20px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

# 6. 엑셀 다운로드 (사이드바)
if export_list:
    df_export = pd.concat(export_list)
    df_export['건물명'] = pd.Categorical(df_export['건물명'], categories=BUILDING_ORDER, ordered=True)
    df_export = df_export.sort_values(by=['건물명', '날짜', 'raw_start'])
    
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export[['날짜', '건물명', '강의실', '시간', '행사명', '관리부서', '상태']].to_excel(writer, index=False)
    
    st.sidebar.download_button(
        label="📥 결과 엑셀 저장", 
        data=output.getvalue(), 
        file_name=f"성의교정_대관현황_{date.today()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
