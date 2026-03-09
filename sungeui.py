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
    
    /* 테이블 스타일: 헤더 중앙 정렬 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .custom-table th { 
        background-color: #333333 !important; color: #ffffff !important; 
        text-align: center !important; font-weight: bold; padding: 10px 4px;
    }
    .custom-table td { border: 1px solid #dee2e6; padding: 8px 4px !important; font-size: 14px; vertical-align: middle !important; }

    /* 열 너비 설정 (PC) */
    .col-date { width: 95px; }
    .col-place { width: 15%; }
    .col-time { width: 70px; }
    .col-event { width: auto; }
    .col-dept { width: 15%; }
    .col-status { width: 80px; }

    /* 모바일 대응: 가로 768px 이하 */
    @media (max-width: 768px) {
        .custom-table { table-layout: auto; }
        .custom-table th, .custom-table td { font-size: 12px; padding: 6px 2px !important; }
        .time-wrapper { line-height: 1.2; display: block; text-align: center; }
        .col-date { width: 70px !important; }
        .col-status { width: 65px !important; }
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
                        # 모바일 두 줄 표시를 위한 시간 포맷팅
                        t_start = item.get('startTime', '')
                        t_end = item.get('endTime', '')
                        time_display = f'<div class="time-wrapper">{t_start}<br>{t_end}</div>'
                        
                        expanded_rows.append({
                            '날짜': curr_dt.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': time_display,
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '예약확정' if item.get('status') == 'Y' else '신청대기',
                            'raw_start': t_start,
                            'raw_end': t_end
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
            
            # 중요: HTML 테이블 직접 구성 (st.markdown + unsafe_allow_html=True)
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
                        <td>{row['강의실']}</td>
                        <td>{row['시간']}</td>
                        <td>{row['행사명']}</td>
                        <td>{row['관리부서']}</td>
                        <td style="text-align:center;">{row['상태']}</td>
                    </tr>
                """
            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)
            export_list.append(bu_df)
        else:
            st.markdown('<div style="color:#888; font-style:italic;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#888; font-style:italic;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

# 6. 엑셀 다운로드 (데이터 정제 후 저장)
if export_list:
    df_export = pd.concat(export_list)
    df_export['건물명'] = pd.Categorical(df_export['건물명'], categories=BUILDING_ORDER, ordered=True)
    df_export = df_export.sort_values(by=['건물명', '날짜', 'raw_start'])
    
    # 엑셀용 시간 컬럼 재생성 (HTML 태그 제거)
    df_export['시간(정리)'] = df_export['raw_start'] + " ~ " + df_export['raw_end']
    excel_data = df_export[['날짜', '건물명', '강의실', '시간(정리)', '행사명', '관리부서', '상태']]
    
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        excel_data.to_excel(writer, index=False)
    st.sidebar.download_button("📥 현재 결과 엑셀 저장", output.getvalue(), f"대관현황_{date.today()}.xlsx")
