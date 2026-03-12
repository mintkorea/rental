import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 통합 관리", layout="wide", initial_sidebar_state="expanded")

# 2. CSS: 셀 헤더 중앙 정렬 및 가독성 스타일
st.markdown("""
    <style>
    th { text-align: center !important; background-color: #f0f2f6 !important; }
    td { white-space: normal !important; word-break: break-all !important; vertical-align: middle !important; }
    .title-box { background-color: #1E3A5F; padding: 20px; border-radius: 10px; color: white; text-align: center; margin-bottom: 25px; }
    .date-info { font-size: 1.2rem; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 3. 데이터 수집 및 색상 로직
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        wd_idx = target_date.isoweekday() # 월1~일7
        
        # 요일 색상 결정
        wd_name = ['','월','화','수','목','금','토','일'][wd_idx]
        if wd_idx == 6: # 토요일
            display_wd = f":blue[{wd_name}]"
        elif wd_idx == 7: # 일요일
            display_wd = f":red[{wd_name}]"
        else:
            display_wd = wd_name

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
        if not rows: return pd.DataFrame(), display_wd
        df = pd.DataFrame(rows)
        df['b_idx'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
        return df.sort_values(by=['b_idx', '_tm']).drop(columns=['_tm']), display_wd
    except: return pd.DataFrame(), ""

# 4. 사이드바
with st.sidebar:
    st.header("⚙️ 관리 메뉴")
    date_in = st.date_input("조회 날짜 선택", value=now_today)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:3])
    st.write("---")
    st.info("💡 엑셀 출력 시 모든 상세 정보가 포함됩니다.")

# 5. 메인 화면 구성
df, colored_wd = get_data(date_in)
formatted_date = date_in.strftime("%Y. %m. %d")

st.markdown(f"""
    <div class="title-box">
        <h2 style='margin:0;'>🏫 성의교정 대관 현황</h2>
        <div class="date-info">{formatted_date}({colored_wd}) | 근무조 : A조</div>
    </div>
    """, unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)]
    for b_name in BUILDING_ORDER:
        if b_name in sel_bu:
            b_data = f_df[f_df['건물명'] == b_name]
            st.markdown(f"#### 📍 {b_name}")
            if not b_data.empty:
                st.dataframe(
                    b_data[['장소', '시간', '행사명', '부서', '부스', '인원', '상태']], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "장소": st.column_config.TextColumn("🏠 장소", width="medium"),
                        "시간": st.column_config.TextColumn("⏰ 시간", width="small", help="중앙정렬", validate=None),
                        "행사명": st.column_config.TextColumn("📝 행사명", width="large"),
                        "부서": st.column_config.TextColumn("🏢 주관부서", width="medium"),
                        "부스": st.column_config.TextColumn("🎪 부스", width="min"),
                        "인원": st.column_config.TextColumn("👥 인원", width="min"),
                        "상태": st.column_config.TextColumn("✅ 상태", width="min"),
                    }
                )
            else:
                st.caption(f"{b_name} 대관 내역이 없습니다.")
else:
    st.warning("조회된 데이터가 없습니다.")
