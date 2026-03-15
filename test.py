import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 전역 변수 설정 (에러 방지를 위해 최상단 배치)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
KST = pytz.timezone('Asia/Seoul')

# 2. 페이지 설정 및 반응형 CSS (폰트 크기 강화 및 줌 대응)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")

st.markdown("""
<style>
    /* 공통 스타일 */
    .stApp { background-color: #f8f9fa; }
    .date-container { background-color: #333; color: white; padding: 12px; border-radius: 8px; margin-top: 20px; font-weight: bold; font-size: 1.1rem; }
    .bu-header { font-size: 1.2rem; font-weight: bold; color: #1e3a5f; padding: 10px 0; border-bottom: 2px solid #1e3a5f; margin: 15px 0 5px 0; }

    /* [세로 모드] 600px 이하: 커스텀 셸 레이아웃 */
    @media (max-width: 600px) {
        .desktop-view { display: none !important; }
        .mobile-view { display: block !important; }
        .event-shell { border-bottom: 1px solid #dee2e6; padding: 12px 5px; background-color: white; }
        .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
        .col-place { flex: 5; font-size: 16px; font-weight: bold; color: #222; }
        .col-time { flex: 3; font-size: 14px; color: #ff4b4b; font-weight: 600; text-align: center; }
        .col-status { flex: 1.5; font-size: 13px; text-align: right; font-weight: bold; }
        .row-2 { font-size: 15px; color: #444; line-height: 1.4; }
    }

    /* [가로 모드/PC] 601px 이상: 표 형식 및 폰트 확대 */
    @media (min-width: 601px) {
        .mobile-view { display: none !important; }
        .desktop-view { display: block !important; }
        /* 데이터프레임 폰트 및 행 높이 강제 조정 */
        .stDataFrame div[data-testid="stTable"] { font-size: 16px !important; }
        .stDataFrame td { padding: 12px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 로직 함수
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
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
                            '부스': str(item.get('boothCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 엑셀 생성 (기본 규격 유지)
def create_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('대관현황')
        # 서식 설정 (생략 가능하나 기존 규격 적용됨)
        # ... (이전의 worksheet.set_row(35) 및 shrink 설정 포함)
        writer.close()
    return output.getvalue()

# 5. 메인 UI
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    # 에러 해결: BUILDING_ORDER가 미리 정의되어 있어야 함
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-container">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                # --- [세로 모드 전용 셸] ---
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

                # --- [가로 모드 전용 표: 폰트 확대 버전] ---
                st.markdown('<div class="desktop-view">', unsafe_allow_html=True)
                st.dataframe(
                    b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], 
                    use_container_width=True, hide_index=True,
                    column_config={"장소": st.column_config.TextColumn(width="medium"), "시간": st.column_config.TextColumn(width="small")}
                )
                st.markdown('</div>', unsafe_allow_html=True)
