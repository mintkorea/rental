import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

# 1. 페이지 설정: 화면 확대/축소 가능하도록 설정 (기본적으로 Streamlit은 지원하지만 명시적 제어는 CSS/HTML로 보완)
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

# 2. CSS 설정 (중앙 정렬, 반응형 레이아웃, 모바일 시간 2줄 처리)
st.markdown("""
<style>
    /* 상단 여백 및 기본 폰트 설정 */
    .block-container { padding-top: 3.5rem !important; }
    
    .main-title { font-size: 26px !important; font-weight: bold; margin-bottom: 20px; color: #1E3A5F; }
    .building-header {
        font-size: 20px !important; font-weight: bold; color: #2E5077;
        margin-top: 25px; margin-bottom: 12px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    
    .no-data-msg { color: #888; font-style: italic; padding: 10px; margin-bottom: 20px; }
    
    /* 테이블 기본 스타일: 헤더 중앙 정렬 고정 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .custom-table th { 
        background-color: #333333 !important; 
        color: #ffffff !important; 
        text-align: center !important; 
        font-weight: bold; 
        vertical-align: middle !important;
    }
    .custom-table td { border: 1px solid #dee2e6; padding: 8px 4px !important; font-size: 14px; vertical-align: middle !important; }

    /* 열 너비 설정 (기본 PC) */
    .custom-table .col-date { width: 95px; text-align: center !important; }
    .custom-table .col-place { width: 15%; text-align: left !important; }
    .custom-table .col-time { width: 65px; text-align: center !important; }
    .custom-table .col-event { width: auto; text-align: left !important; }
    .custom-table .col-dept { width: 15%; text-align: left !important; }
    .custom-table .col-status { width: 80px; text-align: center !important; }

    /* [모바일/태블릿 반응형 전용] */
    @media (max-width: 768px) {
        .custom-table { table-layout: auto; }
        .custom-table th, .custom-table td { font-size: 12px; padding: 6px 3px !important; }
        
        /* 시간 셀 내의 줄바꿈 허용 (시작/종료를 한 셀에 두 줄로 표시하기 위함) */
        .time-wrapper { display: block; line-height: 1.3; }
        .time-sep { display: none; } /* '-' 기호 숨기기 */
        
        .custom-table .col-date { width: 70px !important; }
        .custom-table .col-status { width: 60px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정 (기본값: 오늘)
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
start_selected = col1.date_input("시작일", value=date.today())
end_selected = col2.date_input("종료일", value=date.today())

# 타이틀 날짜 표시
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
                        # 시작/종료 시간을 모바일 환경을 위해 HTML로 미리 포맷팅
                        time_html = f'<div class="time-wrapper">{item.get("startTime", "")}<span class="time-sep"> - </span><br class="mobile-br">{item.get("endTime", "")}</div>'
                        expanded_rows.append({
                            '날짜': curr_dt.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': time_html,
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '예약확정' if item.get('status') == 'Y' else '신청대기',
                            'raw_start': item.get('startTime', '') # 정렬용
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
            
            # HTML 테이블 생성
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
                        <td style="text-align:center;">{row['시간']}</td>
                        <td>{row['행사명']}</td>
                        <td>{row['관리부서']}</td>
                        <td style="text-align:center;">{row['상태']}</td>
                    </tr>
                """
            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)
            export_list.append(bu_df)
        else:
            st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

# 6. 엑셀 다운로드 (정렬 유지)
if export_list:
    df_export = pd.concat(export_list)
    df_export['건물명'] = pd.Categorical(df_export['건물명'], categories=BUILDING_ORDER, ordered=True)
    df_export = df_export.sort_values(by=['건물명', '날짜', 'raw_start'])
    # 엑셀용 데이터는 HTML 태그 제거
    df_export['시간'] = df_export['raw_start'] + " - " + df_export['시간'].str.extract(r'br.*?>(.*?)</div>')[0]
    
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export[['날짜', '건물명', '강의실', '시간', '행사명', '관리부서', '상태']].to_excel(writer, index=False)
    st.sidebar.download_button("📥 현재 결과 엑셀 저장", output.getvalue(), f"대관현황_{date.today()}.xlsx")
