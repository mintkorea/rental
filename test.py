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

# 2. 스타일 설정 (폰트 및 모바일 레이아웃)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@700;900&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Noto Sans KR', sans-serif; }
    .main-title { font-size: 1.8rem; font-weight: 900; color: #1e3a5f; text-align: center; margin: 15px 0; }
    .date-container { background: #333; color: white; padding: 10px; border-radius: 8px; margin-bottom: 10px; font-weight: bold; }
    .bu-header { font-size: 1.1rem; font-weight: 700; color: #1e3a5f; padding: 8px 0; border-bottom: 2px solid #1e3a5f; display: flex; justify-content: space-between; align-items: center; }
    .badge-count { background: #eef2f6; color: #1e3a5f; padding: 2px 10px; border-radius: 15px; font-size: 0.8rem; }
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 5px; background: white; margin-bottom: 2px; }
    .row-1 { display: flex; align-items: center; justify-content: space-between; }
    .col-place { flex: 5; font-size: 15px; font-weight: 700; color: #222; }
    .col-time { flex: 4; font-size: 13px; color: #d9534f; text-align: center; font-weight: bold; }
    .col-status { flex: 1.5; font-size: 12px; text-align: right; color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 수집 및 allowDay 필터링 함수
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
            
            # 행사의 시작/종료일 파싱
            item_s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # allowDay 분석 (예: "1,2,3" -> 월,화,수)
            allow_day_str = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_str.split(',') if d.strip().isdigit()]
            
            # 시작일부터 종료일까지 루프를 돌며 선택된 범위 내의 날짜만 추출
            curr = item_s_dt
            while curr <= item_e_dt:
                if s_date <= curr <= e_date:
                    # 요일 체크 (1:월, ..., 7:일)
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
    except:
        return pd.DataFrame()

# 4. 메인 화면 및 사이드바
st.markdown('<div class="main-title">🏢 성의교정 실시간 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    st.divider()
    # 뷰 모드 강제 분리 (중복 노출 방지 핵심)
    view_mode = st.radio("보기 모드 선택", ["📱 모바일", "💻 PC/표"], index=0)

df = get_data(s_date, e_date)

# 5. 결과 출력
if not df.empty:
    # 엑셀 다운로드 (본문 상단)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button(label="📥 엑셀 파일 다운로드", data=output.getvalue(), file_name=f"대관현황_{s_date}.xlsx")

    # 날짜별 정렬 출력
    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-container">📅 {d_str}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            # 건물명 공백 제거 비교
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","").str.contains(bu.replace(" ","")))]
            
            if not b_df.empty:
                st.markdown(f"""<div class="bu-header"><span>🏢 {bu}</span><span class="badge-count">총 {len(b_df)}건</span></div>""", unsafe_allow_html=True)
                
                if "모바일" in view_mode:
                    for _, row in b_df.iterrows():
                        st.markdown(f"""
                        <div class="event-shell">
                            <div class="row-1">
                                <div class="col-place">📍 {row['장소']}</div>
                                <div class="col-time">⏰ {row['시간']}</div>
                                <div class="col-status">{row['상태']}</div>
                            </div>
                            <div style="font-size:14px; color: #666; margin-top:4px;">📄 {row['행사명']} ({row['인원']}명)</div>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], use_container_width=True, hide_index=True)
else:
    st.warning("📅 선택한 범위에 대관 내역이 없습니다.")
