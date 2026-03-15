import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일 고도화
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@500;700;900&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Noto Sans KR', sans-serif; }
    
    /* [모바일 셸 레이아웃 개선] */
    .event-shell { border-bottom: 1px solid #eee; padding: 15px 5px; background: white; }
    .row-1 { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
    
    /* 장소 영역을 대폭 넓히고(flex 7), 시간 영역은 최소화(flex 3) */
    .col-place { flex: 7; font-size: 16px; font-weight: 700; color: #1e3a5f; line-height: 1.3; }
    .col-time { 
        flex: 3; font-size: 13px; color: #d9534f; text-align: right; 
        font-weight: bold; white-space: nowrap; margin-top: 2px;
    }
    
    /* 행사명 영역 폰트 조절 */
    .row-2 { font-size: 14.5px; color: #555; margin-top: 6px; line-height: 1.4; word-break: keep-all; }

    /* [PC 표 모드 개선] */
    /* 표 안의 텍스트가 잘리지 않고 자동 줄바꿈(2행 이상) 되도록 강제 설정 */
    .stDataFrame div[data-testid="stTable"] td {
        white-space: normal !important;
        word-break: break-all !important;
        font-size: 14px !important;
        line-height: 1.2 !important;
    }
    
    .main-title { font-size: 1.8rem; font-weight: 900; color: #1e3a5f; text-align: center; margin: 15px 0; }
    .date-container { background: #333; color: white; padding: 12px; border-radius: 8px; margin-bottom: 10px; font-weight: bold; }
    .bu-header { font-size: 1.1rem; font-weight: 700; color: #1e3a5f; padding: 10px 0; border-bottom: 2px solid #1e3a5f; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 수집 (allowDay 필터링 포함)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.strftime('%Y-%m-%d'), "end": e_date.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            item_s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_day_str = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_str.split(',') if d.strip().isdigit()]
            
            curr = item_s_dt
            while curr <= item_e_dt:
                if s_date <= curr <= e_date:
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

# 4. 화면 구성
st.markdown('<div class="main-title">🏢 성의교정 실시간 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    view_mode = st.radio("보기 모드 선택", ["📱 모바일(셸)", "💻 PC/표"], index=0)

df = get_data(s_date, e_date)

if not df.empty:
    # 엑셀 다운로드
    excel_data = io.BytesIO()
    with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button(label="📥 엑셀 파일 다운로드", data=excel_data.getvalue(), file_name=f"대관현황_{s_date}.xlsx")

    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-container">📅 {d_str}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","").str.contains(bu.replace(" ","")))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu} <small>(총 {len(b_df)}건)</small></div>', unsafe_allow_html=True)
                
                if "모바일" in view_mode:
                    for _, row in b_df.iterrows():
                        st.markdown(f"""
                        <div class="event-shell">
                            <div class="row-1">
                                <div class="col-place">📍 {row['장소']}</div>
                                <div class="col-time">⏰ {row['시간']}</div>
                            </div>
                            <div class="row-2">📄 {row['행사명']} ({row['부서']}, {row['인원']}명) <b style="color:{'#28a745' if row['상태']=='확정' else '#d9534f'}">[{row['상태']}]</b></div>
                        </div>""", unsafe_allow_html=True)
                else:
                    # 표 형식에서 자동 개행(Column Configuration) 적용
                    st.dataframe(
                        b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], 
                        use_container_width=True, hide_index=True,
                        column_config={
                            "행사명": st.column_config.TextColumn("행사명", width="large", help="긴 제목은 자동 줄바꿈됩니다."),
                            "장소": st.column_config.TextColumn("장소", width="medium")
                        }
                    )
else:
    st.info("해당 날짜에 대관 내역이 없습니다.")
