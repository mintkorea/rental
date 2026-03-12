import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 스타일 (중앙 정렬 최적화)
st.markdown("""
<style>
    .report-header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
    th { text-align: center !important; background-color: #f8f9fa; }
    td { vertical-align: middle !important; }
</style>
""", unsafe_allow_html=True)

# 3. 3교대 근무조 로직 (13일=A, 14일=B, 15일=C)
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    shifts = ['A', 'B', 'C']
    return f"{shifts[diff % 3]}조"

# 4. 데이터 로드 (유연한 요일 매칭 적용)
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        # 학교 데이터 요일: 월(1)~일(7) / target_date.isoweekday()와 일치
        current_wd = target_date.isoweekday()

        for item in raw:
            if not item.get('startDt'): continue
            
            # allowDay 필터링 (데이터가 'None'이거나 비어있으면 매일 대관으로 간주)
            allow_day_raw = str(item.get('allowDay', ''))
            if allow_day_raw and allow_day_raw.lower() != 'none':
                allowed_days = [d.strip() for d in allow_day_raw.split(',') if d.strip().isdigit()]
                if str(current_wd) not in allowed_days:
                    continue
            
            rows.append({
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '부서': item.get('mgDeptNm', '') or '-',
                '인원': item.get('peopleCount', '') or '-',
                '부스': str(item.get('boothCount', '0')),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
            df = df.sort_values(by=['b_idx', '시간']).drop(columns=['b_idx'])
        return df
    except: return pd.DataFrame()

# 5. 서식화된 엑셀 생성 (제목줄 및 근무조 포함)
def create_formatted_excel(df, target_date, shift_name):
    output = io.BytesIO()
    date_str = target_date.strftime("%Y. %m. %d")
    wd_name = ['','월','화','수','목','금','토','일'][target_date.isoweekday()]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 데이터 시트 작성 (3행부터 시작)
        df.to_excel(writer, index=False, sheet_name='대관현황', startrow=2)
        
        workbook = writer.book
        worksheet = writer.sheets['대관현황']
        
        # 제목 및 정보 행 작성
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        info_format = workbook.add_format({'font_size': 11, 'align': 'left'})
        header_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        
        worksheet.write('A1', f"성의교정 대관 현황", title_format)
        worksheet.write('A2', f"일자: {date_str}({wd_name})  |  근무조: {shift_name}", info_format)
        
        # 열 너비 조절
        worksheet.set_column('A:B', 20)
        worksheet.set_column('C:C', 40)
        worksheet.set_column('D:G', 15)
        
    return output.getvalue()

# 6. 메인 로직 실행
s_date = st.sidebar.date_input("조회일", value=now_today)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_data(s_date)
shift_info = get_shift(s_date)

# 요일 색상 설정
wd_idx = s_date.isoweekday()
wd_names = ['','월','화','수','목','금','토','일']
if wd_idx == 6: color_wd = f"<span style='color:blue'>{wd_names[wd_idx]}</span>"
elif wd_idx == 7: color_wd = f"<span style='color:red'>{wd_names[wd_idx]}</span>"
else: color_wd = wd_names[wd_idx]

# 화면 헤더
st.markdown(f"""
    <div class="report-header">
        <h2 style='margin-bottom:5px;'>성의교정 대관 현황</h2>
        <p style='font-size:1.1rem; color:#555;'>
            {s_date.strftime("%Y. %m. %d")}({color_wd}) &nbsp; | &nbsp; 근무조 : {shift_info}
        </p>
    </div>
    """, unsafe_allow_html=True)

# 7. 데이터 출력
if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)].copy()
    
    with st.sidebar:
        st.write("---")
        if not f_df.empty:
            excel_data = create_formatted_excel(f_df, s_date, shift_info)
            st.download_button("📥 보고서 양식 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx")

    for b in sel_bu:
        b_df = f_df[f_df['건물명'] == b]
        st.markdown(f"#### 📍 {b}")
        if not b_df.empty:
            st.dataframe(
                b_df[['장소', '시간', '행사명', '부서', '부스', '인원', '상태']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "시간": st.column_config.TextColumn(width="small"),
                    "부스": st.column_config.TextColumn(width="min"),
                    "인원": st.column_config.TextColumn(width="min"),
                    "상태": st.column_config.TextColumn(width="min"),
                }
            )
        else:
            st.info("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
