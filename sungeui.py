import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 수집 로직 (기존과 동일)
@st.cache_data(ttl=60)
def get_clean_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            item_start = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_end = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = max(s_date, item_start)
            last = min(e_date, item_end)
            while curr <= last:
                def clean(t): return str(t).replace("<", "&lt;").replace(">", "&gt;").strip() if t else ""
                rows.append({
                    '날짜': curr.strftime('%Y-%m-%d'),
                    '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                    '건물명': clean(item.get('buNm', '')),
                    '장소': clean(item.get('placeNm', '')),
                    '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                    '행사명': clean(item.get('eventNm', '')),
                    '인원': clean(item.get('peopleCount', '')),
                    '부서': clean(item.get('mgDeptNm', '')),
                    '상태': '확정' if item.get('status') == 'Y' else '대기'
                })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates()
    except: return pd.DataFrame()

# 3. 사이드바 구성
with st.sidebar:
    st.header("⚙️ 조회 및 저장")
    s_day = st.date_input("시작일", value=now_today)
    e_day = st.date_input("종료일", value=s_day + timedelta(days=2))
    selected_bu = st.multiselect("건물", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    
    # 데이터 불러오기
    df = get_clean_data(s_day, e_day)
    
    if not df.empty:
        # [해결책] 엑셀이 불편하시다면 HTML로 추출하여 PDF 저장을 돕는 기능
        st.markdown("---")
        st.subheader("📄 결과물 저장")
        
        # 필터링된 데이터
        final_df = df[df['건물명'].isin(selected_bu)].sort_values(['날짜', '건물명'])
        
        # 엑셀(CSV) 다운로드 버튼 (UTF-8-SIG로 한글 깨짐 방지)
        csv_data = final_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 엑셀(CSV) 다운로드", data=csv_data, file_name=f"대관현황_{s_day}.csv", mime="text/csv")
        
        st.info("💡 엑셀을 열고 상단의 **[편집 사용]**을 누르면 자유롭게 수정하실 수 있습니다.")

# 4. 메인 화면 출력 (웹 확인용)
st.markdown(f'<h2 style="text-align:center;">🏫 {s_day} ~ {e_day} 대관 현황</h2>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(selected_bu)].sort_values(['날짜', '건물명'])
    # 웹 화면에는 보기 좋게 표로 출력
    st.table(f_df) 
else:
    st.info("조회된 내역이 없습니다.")
