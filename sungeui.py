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

# 2. CSS 설정 (Pandas 스타일 렌더링용)
st.markdown("""
<style>
    .block-container { padding-top: 4rem !important; }
    .main-title { font-size: 26px !important; font-weight: bold; margin-bottom: 20px; color: #1E3A5F; }
    .building-header {
        font-size: 20px !important; font-weight: bold; color: #2E5077;
        margin-top: 25px; margin-bottom: 12px; padding-left: 5px; border-left: 5px solid #2E5077;
    }
    
    /* [핵심] 테이블 스타일링: HTML 노출 방지를 위해 Pandas 스타일 객체와 연동 */
    .rendered_html table { width: 100%; border-collapse: collapse; }
    .rendered_html th { 
        background-color: #333 !important; color: white !important; 
        text-align: center !important; font-weight: bold; 
    }
    .rendered_html td { text-align: left; border: 1px solid #dee2e6; font-size: 14px; }
    
    /* 시간 두 줄 표시를 위한 스타일 */
    .time-cell { line-height: 1.2; text-align: center !important; display: block; white-space: pre-wrap; }

    @media (max-width: 768px) {
        .rendered_html td, .rendered_html th { font-size: 12px !important; padding: 4px 2px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 설정 (기본값: 오늘)
st.sidebar.header("🔍 기간 설정")
col1, col2 = st.sidebar.columns(2)
today = date.today()
start_selected = col1.date_input("시작일", value=today)
end_selected = col2.date_input("종료일", value=today)

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
                        # [변경] HTML 대신 줄바꿈 문자(\n)를 사용하여 두 줄 표시 유도
                        time_val = f"{item.get('startTime', '')}\n{item.get('endTime', '')}"
                        expanded_rows.append({
                            '날짜': curr_dt.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': time_val,
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
            
            # [해결책] HTML 태그를 직접 쓰지 않고 Pandas의 스타일 기능을 이용해 출력
            display_df = bu_df.drop(columns=['건물명', 'raw_start']).reset_index(drop=True)
            
            # 스타일 적용: 헤더 중앙 정렬 및 시간 셀 줄바꿈 허용
            st.write(
                display_df.style.set_properties(**{
                    'text-align': 'left',
                    'white-space': 'pre-wrap', # \n을 두 줄로 렌더링
                    'border': '1px solid #dee2e6'
                }).set_table_styles([
                    {'selector': 'th', 'props': [('background-color', '#333'), ('color', 'white'), ('text-align', 'center')]},
                    {'selector': 'td:nth-child(1)', 'props': [('text-align', 'center')]}, # 날짜 중앙
                    {'selector': 'td:nth-child(3)', 'props': [('text-align', 'center')]}, # 시간 중앙
                    {'selector': 'td:nth-child(6)', 'props': [('text-align', 'center')]}  # 상태 중앙
                ]).to_html(),
                unsafe_allow_html=True
            )
            
            bu_df['건물명'] = bu
            export_list.append(bu_df)
        else:
            st.markdown('<div style="color:#888;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#888;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

# 6. 엑셀 다운로드
if export_list:
    df_export = pd.concat(export_list)
    df_export['건물명'] = pd.Categorical(df_export['건물명'], categories=BUILDING_ORDER, ordered=True)
    df_export = df_export.sort_values(by=['건물명', '날짜', 'raw_start'])
    
    # 엑셀은 사람이 보기 편하게 시간 포맷 수정
    df_export['시간'] = df_export['시간'].str.replace('\n', ' ~ ')
    
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export[['날짜', '건물명', '강의실', '시간', '행사명', '관리부서', '상태']].to_excel(writer, index=False)
    st.sidebar.download_button("📥 검색 결과 엑셀 저장", output.getvalue(), f"대관현황_{date.today()}.xlsx")
