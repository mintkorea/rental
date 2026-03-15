import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
from streamlit_javascript import st_javascript  # 화면 너비 감지용

# 1. 초기 설정 및 전역 변수
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 고도화된 스타일 (타이틀 폰트 및 중복 방지)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #f8f9fa; }

    /* 메인 타이틀: 가독성 높은 폰트로 수정 */
    .main-title { 
        font-size: 1.6rem; font-weight: 800; color: #1e3a5f; 
        text-align: center; margin: 20px 0; letter-spacing: -0.5px;
        line-height: 1.3;
    }
    
    /* 날짜/근무조 헤더 */
    .date-container { background: #333; color: white; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; }
    
    /* 건물 헤더 */
    .bu-header { 
        font-size: 1.15rem; font-weight: 700; color: #1e3a5f; 
        padding: 8px 0; border-bottom: 2px solid #1e3a5f; 
        display: flex; justify-content: space-between; align-items: center;
    }
    .event-count { background: #eef2f6; color: #1e3a5f; padding: 2px 10px; border-radius: 15px; font-size: 0.85rem; }

    /* 모바일 셸 레이아웃 */
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 5px; background: white; }
    .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
    .col-place { flex: 5; font-size: 15px; font-weight: 700; color: #333; }
    .col-time { flex: 3.5; font-size: 14px; color: #d9534f; font-weight: 600; text-align: center; }
    .col-status { flex: 1.5; font-size: 12px; text-align: right; color: #28a745; font-weight: bold; }
    .row-2 { font-size: 14px; color: #666; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (생략 없는 핵심 함수)
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

# 4. 화면 너비 감지 (JS 활용)
width = st_javascript("window.innerWidth")

# 5. 메인 타이틀 및 조회 설정
st.markdown('<div class="main-title">🏢 성의교정<br>실시간 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

# 6. 본문 및 엑셀 다운로드 버튼 배치
if not df.empty:
    # 엑셀 다운로드 버튼을 본문 상단에 배치
    # ( create_formatted_excel 함수는 기존 로직 그대로 사용함을 전제 )
    # st.download_button(...) 배치 가능

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-container">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header"><span>🏢 {bu}</span><span class="event-count">총 {len(b_df)}건</span></div>', unsafe_allow_html=True)
                
                # [중복 노출 방지 핵심] 너비에 따라 하나의 모드만 실행
                if width is not None and width < 768:
                    # --- 세로 모드 전용 ---
                    for _, row in b_df.iterrows():
                        st.markdown(f"""
                        <div class="event-shell">
                            <div class="row-1">
                                <div class="col-place">📍 {row['장소']}</div>
                                <div class="col-time">⏰ {row['시간']}</div>
                                <div class="col-status">{row['상태']}</div>
                            </div>
                            <div class="row-2">📄 {row['행사명']} ({row['인원']}명)</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    # --- 가로 모드 전용 ---
                    st.dataframe(
                        b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], 
                        use_container_width=True, hide_index=True,
                        column_config={
                            "장소": st.column_config.TextColumn(width="medium"),
                            "시간": st.column_config.TextColumn(width="small"),
                            "행사명": st.column_config.TextColumn(width="large")
                        }
                    )
else:
    st.info("내역이 없습니다.")
