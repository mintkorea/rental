import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 초기 설정 (다크모드 강제 방어)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 목록 (공백 및 매칭 오류 방지용 정비)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

st.markdown("""
<style>
    .stApp { background-color: white !important; color: black !important; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F !important; margin-bottom: 20px; }
    .date-header { background-color: #2E5077 !important; color: white !important; padding: 10px 15px; border-radius: 5px; margin-top: 25px; display: flex; justify-content: space-between; align-items: center; }
    .building-header { font-size: 17px !important; font-weight: 700; margin-top: 20px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333 !important; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white !important; border: 1px solid #ddd !important; }
    th { background-color: #f8f9fa !important; color: #333 !important; border: 1px solid #ccc !important; text-align: center !important; padding: 8px 2px; font-size: 13px; }
    td { border: 1px solid #eee !important; color: #333 !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; background-color: white !important; text-align: center; }
</style>
""", unsafe_allow_html=True)

# 2. 사이드바 설정 (사용자 요청 위치 고정)
with st.sidebar:
    st.header("📅 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

# 3. 데이터 로직 및 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if sel_bu:
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            
            # [핵심] 건물명 공백 제거 매칭
            bu_nm = str(item.get('buNm', '')).replace(" ", "").strip()
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    rows.append({
                        'date': curr.strftime('%Y-%m-%d'),
                        'building': bu_nm,
                        'place': item.get('placeNm', ''),
                        'time': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        'event': item.get('eventNm', ''),
                        'status': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
    except:
        df = pd.DataFrame()

    # 화면에 표 그리기
    if not df.empty:
        for d_str in sorted(df['date'].unique()):
            st.markdown(f'<div class="date-header">📅 {d_str}</div>', unsafe_allow_html=True)
            for b in sel_bu:
                st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                # 필터링 시에도 공백 제거 후 비교
                b_df = df[(df['date'] == d_str) & (df['building'] == b.replace(" ", ""))]
                if not b_df.empty:
                    html = "<table><thead><tr><th>장소</th><th>시간</th><th>행사명</th><th>상태</th></tr></thead><tbody>"
                    for _, r in b_df.iterrows():
                        html += f"<tr><td>{r['place']}</td><td>{r['time']}</td><td>{r['event']}</td><td>{r['status']}</td></tr>"
                    st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
                else:
                    st.info(f"'{b}'의 대관 내역이 없습니다.")
    else:
        st.warning("선택하신 기간에 데이터가 없습니다.")
else:
    st.info("왼쪽 사이드바에서 건물을 선택해 주세요.")
