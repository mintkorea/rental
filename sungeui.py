import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 관리", layout="wide", initial_sidebar_state="expanded")

# 2. CSS: 정갈한 디자인 및 중앙 정렬 세팅
st.markdown("""
    <style>
    /* 헤더 및 테이블 스타일 */
    .report-header { border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
    th { text-align: center !important; }
    td { vertical-align: middle !important; }
    /* 짧은 필드 중앙 정렬 강제 (st.dataframe config와 병행) */
    [data-testid="stTable"] td:nth-child(2), 
    [data-testid="stTable"] td:nth-child(5),
    [data-testid="stTable"] td:nth-child(6),
    [data-testid="stTable"] td:nth-child(7) { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# 3. 3교대 근무조 로직 (13일=A, 14일=B, 15일=C)
def get_shift(target_date):
    base_date = date(2026, 3, 13)  # 기준일 (A조)
    diff = (target_date - base_date).days
    shifts = ['A', 'B', 'C']
    return f"{shifts[diff % 3]}조"

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 4. 데이터 수집 및 요일 색상 처리
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        wd_idx = target_date.isoweekday()
        wd_name = ['','월','화','수','목','금','토','일'][wd_idx]
        
        # 요일 색상 (토:파랑 / 일:빨강)
        if wd_idx == 6: color_wd = f"<span style='color:blue'>{wd_name}</span>"
        elif wd_idx == 7: color_wd = f"<span style='color:red'>{wd_name}</span>"
        else: color_wd = wd_name

        for item in raw:
            allow_days = str(item.get('allowDay', ''))
            if allow_days and allow_days != 'None' and str(wd_idx) not in allow_days:
                continue
            rows.append({
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '부서': item.get('mgDeptNm', '') or '-',
                '부스': str(item.get('boothCount', '0')),
                '인원': str(item.get('peopleCount', '0')),
                '상태': '확정' if item.get('status') == 'Y' else '대기',
                '_tm': item.get('startTime', '00:00')
            })
        df = pd.DataFrame(rows)
        if not df.empty:
            df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
            df = df.sort_values(by=['b_idx', '_tm']).drop(columns=['_tm'])
        return df, color_wd
    except: return pd.DataFrame(), ""

# 5. 메인 UI
with st.sidebar:
    st.header("🔍 필터")
    date_in = st.date_input("날짜 선택", value=now_today)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

df, colored_wd = get_data(date_in)
shift_info = get_shift(date_in)

# 상단 헤더 (튀지 않는 정갈한 디자인)
st.markdown(f"""
    <div class="report-header">
        <h2 style='margin-bottom:5px;'>성의교정 대관 현황</h2>
        <p style='font-size:1.1rem; color:#555;'>
            {date_in.strftime("%Y. %m. %d")}({colored_wd}) &nbsp; | &nbsp; 근무조 : {shift_info}
        </p>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    for b_name in BUILDING_ORDER:
        if b_name in sel_bu:
            b_data = f_df[f_df['건물명'] == b_name]
            if not b_data.empty:
                st.markdown(f"**📍 {b_name}**")
                st.dataframe(
                    b_data[['장소', '시간', '행사명', '부서', '부스', '인원', '상태']], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "장소": st.column_config.TextColumn("상세 장소", width="medium"),
                        "시간": st.column_config.TextColumn("시간", width="small"),
                        "행사명": st.column_config.TextColumn("행사명", width="large"),
                        "부서": st.column_config.TextColumn("주관부서", width="medium"),
                        "부스": st.column_config.TextColumn("부스", width="min"),
                        "인원": st.column_config.TextColumn("인원", width="min"),
                        "상태": st.column_config.TextColumn("상태", width="min"),
                    }
                )
            else:
                st.caption(f"{b_name} 내역 없음")
else:
    st.info("조회된 데이터가 없습니다.")
