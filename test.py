import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 전역 변수 설정 (에러 방지를 위해 반드시 최상단에 배치)
# 이 리스트가 st.multiselect보다 위에 있어야 'NameError'가 발생하지 않습니다.
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
KST = pytz.timezone('Asia/Seoul')

# 2. 페이지 설정 및 반응형 CSS (폰트 크기 및 줌 대응)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")

st.markdown("""
<style>
    /* 공통 배경 및 폰트 설정 */
    .stApp { background-color: #f8f9fa; }
    
    /* 날짜 헤더: 가독성을 위해 폰트 크기 키움 */
    .date-container { 
        background-color: #333; color: white; padding: 12px; 
        border-radius: 8px; margin-top: 20px; font-weight: bold; font-size: 1.2rem; 
    }
    
    /* 건물 섹션 헤더 */
    .bu-header { 
        font-size: 1.3rem; font-weight: bold; color: #1e3a5f; 
        padding: 10px 0; border-bottom: 2px solid #1e3a5f; margin: 15px 0 5px 0; 
    }

    /* [세로 모드] 600px 이하: 커스텀 셸 레이아웃 (장소:시간:상태 = 5:3:1.5) */
    @media (max-width: 600px) {
        .desktop-view { display: none !important; }
        .mobile-view { display: block !important; }
        
        .event-shell { border-bottom: 1px solid #dee2e6; padding: 12px 5px; background-color: white; }
        .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
        .col-place { flex: 5; font-size: 16px; font-weight: bold; color: #222; }
        .col-time { flex: 3; font-size: 14px; color: #ff4b4b; font-weight: 600; text-align: center; }
        .col-status { flex: 1.5; font-size: 13px; text-align: right; font-weight: bold; }
        .row-2 { font-size: 15px; color: #444; line-height: 1.4; padding-left: 2px; }
        
        .badge-y { color: #28a745; } /* 확정: 녹색 */
        .badge-n { color: #007bff; } /* 대기: 파란색 */
    }

    /* [가로 모드/PC] 601px 이상: 표 형식 폰트 확대 및 셀 크기 고정 */
    @media (min-width: 601px) {
        .mobile-view { display: none !important; }
        .desktop-view { display: block !important; }
        
        /* 표 폰트 크기 및 행 높이 조정 */
        .stDataFrame div[data-testid="stTable"] { font-size: 16px !important; }
        .stDataFrame td { padding: 12px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 로직 함수 (근무조 계산)
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 4. 데이터 수집 및 필터링
@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
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
                            '부스': str(item.get('boothCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 5. 메인 사이드바 (조회 설정)
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    
    # [에러 해결 핵심] BUILDING_ORDER가 위에서 이미 정의되었으므로 에러가 나지 않습니다.
    sel_bu = st.multiselect(
        "건물 선택", 
        options=BUILDING_ORDER, 
        default=["성의회관", "의생명산업연구원"]
    )

# 6. 데이터 로드 및 화면 출력
df = get_data(s_date, e_date)

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        weekday_name = ["월","화","수","목","금","토","일"][d_obj.weekday()]
        
        # 날짜 및 근무조 헤더
        st.markdown(f'<div class="date-container">📅 {d_str} ({weekday_name}) | 근무조: {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            bu_clean = bu.replace(" ", "")
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu_clean)]
            
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                # --- [세로 모드 뷰: 모바일 커스텀 셸] ---
                mobile_html = ""
                for _, row in b_df.iterrows():
                    s_cls = "badge-y" if row['상태'] == '확정' else "badge-n"
                    mobile_html += f"""
                    <div class="event-shell">
                        <div class="row-1">
                            <div class="col-place">📍 {row['장소']}</div>
                            <div class="col-time">⏰ {row['시간']}</div>
                            <div class="col-status"><span class="{s_cls}">{row['상태']}</span></div>
                        </div>
                        <div class="row-2">📄 {row['행사명']} ({row['인원']}명)</div>
                    </div>"""
                st.markdown(f'<div class="mobile-view">{mobile_html}</div>', unsafe_allow_html=True)
                
                # --- [가로 모드 뷰: 폰트 확대 표] ---
                st.markdown('<div class="desktop-view">', unsafe_allow_html=True)
                st.dataframe(
                    b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], 
                    use_container_width=True, 
                    hide_index=True,
                    column_config={
                        "장소": st.column_config.TextColumn(width="medium"),
                        "시간": st.column_config.TextColumn(width="small"),
                        "행사명": st.column_config.TextColumn(width="large")
                    }
                )
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # 선택한 건물의 내역이 없을 때만 안내 (전체 공백 방지)
                st.caption(f"{bu} 대관 내역이 없습니다.")
else:
    st.info("선택한 날짜에 대관 내역이 없습니다.")
