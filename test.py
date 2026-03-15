import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 전역 설정 및 Viewport (줌 가능하도록 설정)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")

# 변수 사전 정의 (에러 방지)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
KST = pytz.timezone('Asia/Seoul')

# 2. 강력한 모드별 CSS (중복 노출 차단 및 줌 대응)
st.markdown("""
<style>
    /* 전체 배경 */
    .stApp { background-color: #f8f9fa; }

    /* [세로 모드 전용] 768px 미만 */
    @media (max-width: 767px) {
        .view-desktop { display: none !important; }
        .view-mobile { display: block !important; }
        
        .event-shell { border-bottom: 1px solid #dee2e6; padding: 12px 5px; background-color: white; }
        .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
        .col-place { flex: 5; font-size: 16px; font-weight: bold; color: #222; }
        .col-time { flex: 3.5; font-size: 14px; color: #ff4b4b; font-weight: 600; text-align: center; }
        .col-status { flex: 1.5; font-size: 13px; text-align: right; font-weight: bold; color: #28a745; }
        .row-2 { font-size: 14px; color: #555; line-height: 1.5; }
    }

    /* [가로 모드/PC 전용] 768px 이상 */
    @media (min-width: 768px) {
        .view-mobile { display: none !important; }
        .view-desktop { display: block !important; }
        
        /* 표 폰트 및 셸 높이 최적화 */
        .stDataFrame div[data-testid="stTable"] { font-size: 15px !important; }
        .stDataFrame td { height: 45px !important; vertical-align: middle !important; }
    }

    /* 공통 헤더 스타일 */
    .date-container { background: #333; color: white; padding: 12px; border-radius: 8px; margin-top: 20px; font-weight: bold; font-size: 1.1rem; }
    .bu-header { font-size: 1.2rem; font-weight: bold; color: #1e3a5f; padding: 8px 0; border-bottom: 2px solid #1e3a5f; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

# 3. 계산 및 데이터 로직
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent":"Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_day = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 메인 UI 및 사이드바
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

# 5. 화면 출력 부분
if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-container">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                # --- [세로 모드 뷰] ---
                mobile_html = '<div class="view-mobile">'
                for _, row in b_df.iterrows():
                    mobile_html += f"""
                    <div class="event-shell">
                        <div class="row-1">
                            <div class="col-place">📍 {row['장소']}</div>
                            <div class="col-time">⏰ {row['시간']}</div>
                            <div class="col-status">{row['상태']}</div>
                        </div>
                        <div class="row-2">📄 {row['행사명']} ({row['인원']}명)</div>
                    </div>"""
                mobile_html += '</div>'
                st.markdown(mobile_html, unsafe_allow_html=True)

                # --- [가로 모드 뷰] ---
                # 가로 모드 표의 열 너비를 고정하여 셸 크기가 제각각인 것 방지
                st.markdown('<div class="view-desktop">', unsafe_allow_html=True)
                st.dataframe(
                    b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], 
                    use_container_width=True, hide_index=True,
                    column_config={
                        "장소": st.column_config.TextColumn(width="medium"),
                        "시간": st.column_config.TextColumn(width="small"),
                        "행사명": st.column_config.TextColumn(width="large"),
                        "상태": st.column_config.TextColumn(width="small")
                    }
                )
                st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
