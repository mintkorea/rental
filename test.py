import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 전역 설정 (에러 방지를 위해 변수를 최상단에 배치)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
KST = pytz.timezone('Asia/Seoul')

st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")

# 2. 고도화된 스타일 (중복 노출 방지 핵심 로직 포함)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@500;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    .stApp { background-color: #f8f9fa; }

    /* 메인 타이틀 수정 */
    .main-title { 
        font-size: 1.7rem; font-weight: 800; color: #1e3a5f; 
        text-align: center; margin: 25px 0; letter-spacing: -0.7px; line-height: 1.3;
    }
    
    /* [중복 노출 차단 전용 미디어 쿼리] */
    /* 가로 모드일 때는 모바일 뷰를 아예 삭제 */
    @media (min-width: 768px) {
        .mobile-only { display: none !important; }
        .desktop-only { display: block !important; }
    }
    /* 세로 모드일 때는 데스크톱 표를 아예 삭제 */
    @media (max-width: 767px) {
        .desktop-only { display: none !important; }
        .mobile-only { display: block !important; }
    }

    /* 날짜/근무조 헤더 */
    .date-container { background: #333; color: white; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-weight: bold; font-size: 1.1rem; }
    
    /* 건물 헤더 */
    .bu-header { 
        font-size: 1.2rem; font-weight: 700; color: #1e3a5f; 
        padding: 10px 0; border-bottom: 2px solid #1e3a5f; 
        display: flex; justify-content: space-between; align-items: center; margin-top: 15px;
    }
    .badge-count { background: #eef2f6; color: #1e3a5f; padding: 3px 12px; border-radius: 20px; font-size: 0.9rem; font-weight: 500; }

    /* 모바일 전용 셸 스타일 */
    .event-shell { border-bottom: 1px solid #eee; padding: 15px 5px; background: white; }
    .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
    .col-place { flex: 5; font-size: 16px; font-weight: 700; color: #222; }
    .col-time { flex: 3.5; font-size: 14px; color: #d9534f; font-weight: 600; text-align: center; }
    .col-status { flex: 1.5; font-size: 13px; text-align: right; color: #28a745; font-weight: bold; }
    .row-2 { font-size: 15px; color: #555; line-height: 1.4; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 함수
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

# 4. 상단 메인 타이틀 및 본문 엑셀 버튼
st.markdown('<div class="main-title">🏢 성의교정<br>실시간 대관 현황</div>', unsafe_allow_html=True)

# 5. 사이드바 설정
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

# 6. 본문 출력
if not df.empty:
    # 엑셀 다운로드 버튼 (본문 상단에 배치하여 시인성 확보)
    # create_excel_file() 함수가 정의되어 있다면 여기에 st.download_button 추가
    
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-container">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                # 건물 헤더 + 행사 건수
                st.markdown(f"""
                <div class="bu-header">
                    <span>🏢 {bu}</span>
                    <span class="badge-count">총 {len(b_df)}건</span>
                </div>
                """, unsafe_allow_html=True)
                
                # --- [모바일 전용 뷰: 세로] ---
                mobile_html = '<div class="mobile-only">'
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

                # --- [데스크톱 전용 뷰: 가로] ---
                st.markdown('<div class="desktop-only">', unsafe_allow_html=True)
                st.dataframe(
                    b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], 
                    use_container_width=True, hide_index=True,
                    column_config={
                        "장소": st.column_config.TextColumn(width="medium"),
                        "시간": st.column_config.TextColumn(width="small"),
                        "행사명": st.column_config.TextColumn(width="large")
                    }
                )
                st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
