import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. CSS 설정
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 5px; }
    .date-header { font-size: 18px !important; font-weight: 800; color: #1E3A5F; padding: 10px 0; margin-top: 30px; border-bottom: 2px solid #eee; }
    .building-header { font-size: 15px !important; font-weight: 700; margin-top: 15px; margin-bottom: 5px; border-left: 5px solid #2E5077; padding-left: 10px; }
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 10px; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 8px 4px; font-size: 13px; font-weight: bold; text-align: center; }
    td { border: 1px solid #eee; padding: 8px 6px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }
    /* 강조된 안내 문구 스타일 */
    .no-data-msg { text-align: center; padding: 30px; color: #FF4B4B; font-size: 16px; font-weight: bold; border: 1px dashed #ddd; border-radius: 10px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            allowed_weekdays = [int(d.strip()) for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_weekdays or (curr.weekday() + 1) in allowed_weekdays:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', ''),
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 5. 메인 UI
st.sidebar.title("📅 대관 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

# --- 핵심 로직: 날짜별/건물별 루프 ---
if not all_df.empty:
    # 전체 기간에 대해 날짜별로 처리
    date_range = pd.date_range(start_selected, end_selected).strftime('%Y-%m-%d')
    
    for date_str in date_range:
        day_df = all_df[all_df['full_date'] == date_str]
        # 해당 날짜의 요일 구하기
        d_obj = datetime.strptime(date_str, '%Y-%m-%d')
        w_str = ['월','화','수','목','금','토','일'][d_obj.weekday()]
        
        st.markdown(f'<div class="date-header">📅 {date_str} ({w_str}요일)</div>', unsafe_allow_html=True)
        
        # 사용자가 선택한 건물별로 순회
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
            
            if not bu_df.empty:
                # 테이블 출력
                header_html = """<div class="table-container"><table><thead><tr>
                                <th style="width:15%;">장소</th><th style="width:15%;">시간</th>
                                <th style="width:40%;">행사명</th><th style="width:7%;">인원</th>
                                <th style="width:15%;">부서</th><th style="width:8%;">상태</th>
                                </tr></thead><tbody>"""
                rows_html = "".join([f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in bu_df.iterrows()])
                st.markdown(header_html + rows_html + "</tbody></table></div>", unsafe_allow_html=True)
            else:
                # 내역이 없는 건물에 대해 명시적 표시
                st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    # 데이터 자체가 없는 경우
    st.markdown('<div class="no-data-msg">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
