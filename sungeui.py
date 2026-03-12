import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import io

# 1. 페이지 설정 (PC 와이드 모드 고정)
st.set_page_config(
    page_title="성의교정 대관 통합 관리", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 2. 반응형 및 가독성 스타일
st.markdown("""
    <style>
    td { white-space: normal !important; word-break: break-all !important; vertical-align: middle !important; }
    .block-container { padding-top: 2rem; }
    [data-testid="stSidebar"] { min-width: 250px; }
    /* 표 제목행 배경색 강조 */
    thead tr th { background-color: #f0f2f6 !important; }
    </style>
    """, unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 3. 엑셀 리포트 생성 (부서명 포함 전체 데이터)
def create_excel_report(df):
    if df.empty: return None
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='일일대관현황')
        workbook = writer.book
        worksheet = writer.sheets['일일대관현황']
        
        hdr_fmt = workbook.add_format({'bold':True, 'bg_color':'#D9E1F2', 'border':1, 'align':'center'})
        cell_fmt = workbook.add_format({'border':1, 'align':'center'})
        wrap_fmt = workbook.add_format({'border':1, 'align':'left', 'text_wrap':True})
        
        for i, col in enumerate(df.columns):
            worksheet.write(0, i, col, hdr_fmt)
            # 열 너비 최적화
            if col in ['행사명', '부서']: width = 30
            elif col == '장소': width = 20
            else: width = 12
            worksheet.set_column(i, i, width, wrap_fmt if width > 20 else cell_fmt)
    return output.getvalue()

# 4. 데이터 수집 및 로직 (allowDay & 부서명 추출)
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        target_weekday = target_date.isoweekday()

        for item in raw:
            # allowDay 요일 필터링
            allow_days = str(item.get('allowDay', ''))
            if allow_days and allow_days != 'None' and str(target_weekday) not in allow_days:
                continue
            
            rows.append({
                '날짜': target_date.isoformat(),
                '요일': ['','월','화','수','목','금','토','일'][target_weekday],
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '부서': item.get('mgDeptNm', '') or '-', # 부서명 추가
                '인원': str(item.get('peopleCount', '0')),
                '부스': str(item.get('boothCount', '0')),
                '상태': '확정' if item.get('status') == 'Y' else '대기',
                '_tm': item.get('startTime', '00:00')
            })
        if not rows: return pd.DataFrame()
        df = pd.DataFrame(rows)
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        return df.sort_values(by=['b_idx', '_tm']).drop(columns=['_tm'])
    except: return pd.DataFrame()

# 5. 사이드바 (조회 및 엑셀)
with st.sidebar:
    st.header("🔍 관리자 메뉴")
    date_in = st.date_input("날짜 선택", value=now_today)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    
    st.write("---")
    full_df = get_data(date_in)
    
    if not full_df.empty:
        st.subheader("💾 데이터 내보내기")
        filtered_for_excel = full_df[full_df['건물명'].isin(sel_bu)]
        excel_bin = create_excel_report(filtered_for_excel)
        st.download_button(
            label="📥 엑셀 파일 다운로드",
            data=excel_bin,
            file_name=f"대관현황_{date_in}.xlsx",
            use_container_width=True
        )

# 6. 메인 화면 (PC 최적화 대시보드)
st.header(f"🏛️ {date_in} ({['','월','화','수','목','금','토','일'][date_in.isoweekday()]}) 대관 현황")

if not full_df.empty:
    f_df = full_df[full_df['건물명'].isin(sel_bu)]
    
    for b_name in BUILDING_ORDER:
        if b_name in sel_bu:
            b_data = f_df[f_df['건물명'] == b_name]
            st.markdown(f"#### 📍 {b_name}")
            
            if not b_data.empty:
                # [최종 열 구성] 장소, 시간, 행사명, 부서, 부스, 인원, 상태
                st.dataframe(
                    b_data[['장소', '시간', '행사명', '부서', '부스', '인원', '상태']], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "장소": st.column_config.TextColumn("🏠 장소", width="medium"),
                        "시간": st.column_config.TextColumn("⏰ 시간", width="small"),
                        "행사명": st.column_config.TextColumn("📝 행사명", width="large"),
                        "부서": st.column_config.TextColumn("🏢 주관부서", width="medium"),
                        "부스": st.column_config.TextColumn("🎪 부스", width="min"),
                        "인원": st.column_config.TextColumn("👥 인원", width="min"),
                        "상태": st.column_config.TextColumn("✅ 상태", width="min"),
                    }
                )
            else:
                st.caption(f"{b_name} 내역 없음")
else:
    st.warning("데이터가 존재하지 않습니다.")
