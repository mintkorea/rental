import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import pytz
from fpdf import FPDF
import io

# 1. 초기 설정 (기존 레이아웃 및 설정 유지)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 스타일 (정렬 및 헤더 디자인 수정)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .report-header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
    th { text-align: center !important; background-color: #f8f9fa; }
    td { vertical-align: middle !important; }
    /* 짧은 필드들 중앙 정렬 */
    .center-text { text-align: center !important; }
</style>
""", unsafe_allow_html=True)

# 3. 3교대 근무조 로직 (13일=A, 14일=B, 15일=C)
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    shifts = ['A', 'B', 'C']
    return f"{shifts[diff % 3]}조"

# 4. 데이터 로드 (기존 로직 100% 유지)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res.raise_for_status()
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '요일_idx': curr.weekday(),
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': item.get('peopleCount', '') or '-',
                            '부스': str(item.get('boothCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 5. 엑셀 생성 함수 (사이드바용)
def create_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
    return output.getvalue()

# 6. 메인 UI 및 로직
s_date = st.sidebar.date_input("시작일", value=now_today)
e_date = st.sidebar.date_input("종료일", value=s_date)
sel_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_data(s_date, e_date)

# 요일 색상 및 근무조 처리
wd_idx = s_date.isoweekday()
wd_name = ['','월','화','수','목','금','토','일'][wd_idx]
if wd_idx == 6: color_wd = f"<span style='color:blue'>{wd_name}</span>"
elif wd_idx == 7: color_wd = f"<span style='color:red'>{wd_name}</span>"
else: color_wd = wd_name

shift_info = get_shift(s_date)

# 헤더 출력
st.markdown(f"""
    <div class="report-header">
        <h2 style='margin-bottom:5px;'>성의교정 대관 현황</h2>
        <p style='font-size:1.1rem; color:#555;'>
            {s_date.strftime("%Y. %m. %d")}({color_wd}) &nbsp; | &nbsp; 근무조 : {shift_info}
        </p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)].copy()
    
    # 사이드바 엑셀 다운로드 복구
    with st.sidebar:
        st.write("---")
        if not f_df.empty:
            excel_data = create_excel(f_df)
            st.download_button("📥 엑셀 다운로드", data=excel_data, file_name=f"rental_{s_date}.xlsx")

    # 본문 데이터 출력
    for date_val in sorted(f_df['full_date'].unique()):
        d_df = f_df[f_df['full_date'] == date_val]
        for b in sel_bu:
            b_df = d_df[d_df['건물명'] == b]
            st.markdown(f"#### 📍 {b}")
            if not b_df.empty:
                # 짧은 필드 중앙 정렬 반영하여 표 노출
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
