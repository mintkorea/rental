import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 초기 설정 (다크모드 방어 및 배경색 고정)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 목록 (공백 등을 최대한 제거하고 매칭하기 위해 구성)
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
    .no-data-box { color: #d9534f !important; font-size: 13px; padding: 15px; border: 1px dashed #d9534f !important; border-radius: 5px; text-align: center; background-color: #fffafa !important; }
</style>
""", unsafe_allow_html=True)

# 2. 왼쪽 사이드바 (사용자님 요청 위치 사수)
with st.sidebar:
    st.header("📅 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

# 3. 데이터 로드 및 매칭 로직 (공백 제거 매칭 도입)
@st.cache_data(ttl=60)
def load_data(start, end):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start.isoformat(), "end": end.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        data_list = []
        for item in raw:
            if not item.get('startDt'): continue
            
            # 건물명에서 공백을 모두 제거하여 '의생명산업연구원'으로 통일
            raw_bu_nm = str(item.get('buNm', '')).replace(" ", "")
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # allowDay 로직
            allow_day_raw = str(item.get('allowDay', ''))
            allowed = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw.lower() != 'none' else []
            
            curr = s_dt
            while curr <= e_dt:
                if start <= curr <= end:
                    if not allowed or (curr.weekday() + 1) in allowed:
                        data_list.append({
                            'date': curr.strftime('%Y-%m-%d'),
                            'building': raw_bu_nm, 
                            'place': item.get('placeNm', ''),
                            'time': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            'event': item.get('eventNm', ''),
                            'count': item.get('peopleCount', '-') or '-',
                            'dept': item.get('mgDeptNm', '-') or '-',
                            'status': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(data_list)
    except:
        return pd.DataFrame()

# 4. 화면 출력 (루프 구조 전면 수정)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if sel_bu:
    df = load_data(s_date, e_date)
    date_range = pd.date_range(s_date, e_date).strftime('%Y-%m-%d')
    
    for d_str in date_range:
        current_date_obj = datetime.strptime(d_str, '%Y-%m-%d')
        yoil = ['월','화','수','목','금','토','일'][current_date_obj.weekday()]
        st.markdown(f'<div class="date-header"><span>📅 {d_str}</span><span>({yoil}요일)</span></div>', unsafe_allow_html=True)
        
        for b in sel_bu:
            st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
            
            # 검색할 때도 공백을 제거하고 매칭하여 오류 차단
            search_b = b.replace(" ", "")
            if not df.empty:
                filtered = df[(df['date'] == d_str) & (df['building'] == search_b)]
            else:
                filtered = pd.DataFrame()

            if not filtered.empty:
                # 데이터가 있으면 테이블 출력
                html = "<table><thead><tr><th style='width:18%'>장소</th><th style='width:15%'>시간</th><th>행사명</th><th style='width:8%'>인원</th><th style='width:20%'>부서</th><th style='width:8%'>상태</th></tr></thead><tbody>"
                for _, r in filtered.sort_values('time').iterrows():
                    html += f"<tr><td style='text-align:left'>{r['place']}</td><td>{r['time']}</td><td style='text-align:left'>{r['event']}</td><td>{r['count']}</td><td style='text-align:left'>{r['dept']}</td><td>{r['status']}</td></tr>"
                st.markdown(html + "</tbody></table>", unsafe_allow_html=True)
            else:
                # 데이터가 없으면 '내역 없음' 상자 출력
                st.markdown(f'<div class="no-data-box">"{b}"에 대한 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("왼쪽 사이드바에서 건물을 선택해 주세요.")
