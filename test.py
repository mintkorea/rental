import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정 및 전역 변수
st.set_page_config(page_title="성의교정 대관 현황", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 스타일 설정 (타이틀 폰트 및 가독성 개선)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@700;900&display=swap');
    .stApp { background-color: #f8f9fa; font-family: 'Noto Sans KR', sans-serif; }
    
    .main-title { 
        font-size: 1.8rem; font-weight: 900; color: #1e3a5f; 
        text-align: center; margin: 15px 0; line-height: 1.2;
    }
    
    .date-container { background: #333; color: white; padding: 12px; border-radius: 8px; margin-bottom: 10px; font-weight: bold; }
    .bu-header { 
        font-size: 1.1rem; font-weight: 700; color: #1e3a5f; 
        padding: 8px 0; border-bottom: 2px solid #1e3a5f; 
        display: flex; justify-content: space-between; align-items: center;
    }
    .badge-count { background: #eef2f6; color: #1e3a5f; padding: 2px 10px; border-radius: 15px; font-size: 0.8rem; }

    /* 모바일 셸 스타일 */
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 5px; background: white; margin-bottom: 2px; }
    .row-1 { display: flex; align-items: center; justify-content: space-between; }
    .col-place { flex: 5; font-size: 15px; font-weight: 700; color: #222; }
    .col-time { flex: 4; font-size: 13px; color: #d9534f; text-align: center; font-weight: bold; }
    .col-status { flex: 1.5; font-size: 12px; text-align: right; color: #28a745; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 3. 엑셀 생성 함수
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
    return output.getvalue()

# 4. 데이터 수집 함수 (API 대응 강화)
@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.strftime('%Y-%m-%d'), "end": end_date.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
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
    except:
        return pd.DataFrame()

# 5. 메인 UI 및 사이드바
st.markdown('<div class="main-title">🏢 성의교정 실시간<br>대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=datetime.now(KST).date())
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    
    st.divider()
    # [핵심] 사용자가 직접 모드를 선택하게 하여 중복 노출을 원천 차단
    view_mode = st.radio("보기 모드 설정", ["📱 모바일용(셸)", "💻 PC/패드용(표)"], index=0)

df = get_data(s_date, e_date)

# 6. 결과 출력 부분
if not df.empty:
    # 엑셀 다운로드 버튼 (최상단 배치)
    st.download_button(label="📥 전체 내역 엑셀 다운로드", data=to_excel(df), file_name=f"대관현황_{s_date}.xlsx", mime="application/vnd.ms-excel")

    # 날짜별 루프
    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-container">📅 {d_str}</div>', unsafe_allow_html=True)
        
        # 건물별 루프
        for bu in sel_bu:
            # 건물명 공백 제거 비교로 필터링 정확도 상승
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","").str.contains(bu.replace(" ","")))]
            
            if not b_df.empty:
                st.markdown(f'<div class="bu-header"><span>🏢 {bu}</span><span class="badge-count">총 {len(b_df)}건</span></div>', unsafe_allow_html=True)
                
                # 사용자가 선택한 모드 하나만 렌더링 (중복 노출 절대 불가)
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
    st.warning("선택한 날짜나 건물에 대관 내역이 없습니다. (조회 설정을 확인해 주세요)")
