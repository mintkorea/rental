import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 전역 설정 (에러 방지용 최상단 배치)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
KST = pytz.timezone('Asia/Seoul')

st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")

# 2. CSS - 중복 노출 차단 및 타이틀 폰트 수정
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Black+Han+Sans&family=Noto+Sans+KR:wght@400;700&display=swap');
    
    .stApp { background-color: #f8f9fa; }

    /* 메인 타이틀: 가독성 좋고 굵은 폰트로 수정 */
    .main-title { 
        font-family: 'Black Han Sans', sans-serif;
        font-size: 2.2rem; color: #1e3a5f; 
        text-align: center; margin: 20px 0; line-height: 1.2;
    }
    
    /* [중복 노출 방지 핵심] */
    /* 가로 모드(768px 이상) */
    @media (min-width: 768px) {
        .mobile-view { display: none !important; }
        .desktop-view { display: block !important; }
    }
    /* 세로 모드(767px 이하) */
    @media (max-width: 767px) {
        .desktop-view { display: none !important; }
        .mobile-view { display: block !important; }
    }

    /* 날짜/근무조 헤더 */
    .date-container { background: #333; color: white; padding: 12px; border-radius: 8px; margin-bottom: 10px; font-weight: bold; }
    
    /* 건물 헤더 */
    .bu-header { 
        font-size: 1.2rem; font-weight: 700; color: #1e3a5f; 
        padding: 10px 0; border-bottom: 2px solid #1e3a5f; 
        display: flex; justify-content: space-between; align-items: center;
    }
    .badge-count { background: #eef2f6; color: #1e3a5f; padding: 2px 10px; border-radius: 15px; font-size: 0.85rem; }

    /* 모바일 셸 */
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 5px; background: white; }
    .row-1 { display: flex; align-items: center; justify-content: space-between; }
    .col-place { flex: 5; font-size: 16px; font-weight: 700; }
    .col-time { flex: 3.5; font-size: 14px; color: #d9534f; text-align: center; font-weight: bold; }
    .col-status { flex: 1.5; font-size: 12px; text-align: right; color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 3. 엑셀 생성 함수 (다운로드 기능 복원)
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# 4. 데이터 수집 로직
@st.cache_data(ttl=60)
def get_data(s, e):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s.isoformat(), "end": e.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            rows.append({
                'full_date': item['startDt'],
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '부서': item.get('mgDeptNm', '') or '-',
                '인원': str(item.get('peopleCount', '0')),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 5. 화면 출력
st.markdown('<div class="main-title">🏢 성의교정<br>실시간 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

if not df.empty:
    # 엑셀 다운로드 버튼 (본문 상단 노출)
    st.download_button(label="📥 엑셀 파일 다운로드", data=to_excel(df), file_name="대관현황.xlsx", mime="application/vnd.ms-excel")

    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-container">📅 {d_str}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.contains(bu.replace(" ","")))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header"><span>🏢 {bu}</span><span class="badge-count">총 {len(b_df)}건</span></div>', unsafe_allow_html=True)
                
                # --- 세로 모드 전용 ---
                m_html = '<div class="mobile-view">'
                for _, r in b_df.iterrows():
                    m_html += f'<div class="event-shell"><div class="row-1"><div class="col-place">📍 {r["장소"]}</div><div class="col-time">⏰ {r["시간"]}</div><div class="col-status">{r["상태"]}</div></div><div style="font-size:14px; color: #666; margin-top:5px;">📄 {r["행사명"]} ({r["인원"]}명)</div></div>'
                m_html += '</div>'
                st.markdown(m_html, unsafe_allow_html=True)

                # --- 가로 모드 전용 ---
                st.markdown('<div class="desktop-view">', unsafe_allow_html=True)
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], use_container_width=True, hide_index=True)
                st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
