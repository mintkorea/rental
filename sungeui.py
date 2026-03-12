import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 공휴일 리스트 (사용자 정의 가능)
HOLIDAYS = ["2026-01-01", "2026-03-01", "2026-05-05", "2026-06-06", "2026-08-15", "2026-10-03", "2026-10-09", "2026-12-25"]
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. 웹 화면 CSS (다크모드 방어 및 요일 색상)
st.markdown("""
<style>
    /* 다크모드 강제 방어: 배경은 흰색, 글자는 검은색 */
    .stApp { background-color: #ffffff !important; color: #000000 !important; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; margin-bottom: 20px; color: #1E3A5F; }
    
    /* 요일 표시 헤더 바 */
    .date-header { 
        font-size: 18px !important; font-weight: 800; color: #ffffff !important; 
        background-color: #2E5077; padding: 10px 15px; margin-top: 30px; 
        border-radius: 5px; display: flex; justify-content: space-between;
    }
    /* 요일 색상 설정 */
    .sat { color: #5D9CEC !important; font-weight: bold; } /* 토요일 청색 */
    .sun-hol { color: #FF4B4B !important; font-weight: bold; } /* 일요일/공휴일 적색 */
    .weekday { color: #ffffff !important; } /* 평일 흰색 */
    
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 6px solid #2E5077; padding-left: 12px; color: #333; }
    
    /* 테이블 스타일링 */
    table { width: 100%; border-collapse: collapse; table-layout: fixed; border: 1px solid #ddd; background-color: white; }
    th { background-color: #f2f5f8 !important; border: 1px solid #ccc !important; padding: 10px 2px; font-size: 13px; color: #333 !important; text-align: center !important; }
    td { border: 1px solid #eee !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; color: #333 !important; }
    
    .no-data { text-align: center; padding: 50px; font-size: 18px; color: #666; border: 2px dashed #ccc; border-radius: 10px; margin-top: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 요일 판별 로직
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res.raise_for_status()
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    date_str = curr.strftime('%Y-%m-%d')
                    w_idx = curr.weekday() # 5:토, 6:일
                    
                    # 요일 텍스트 및 색상 클래스
                    w_name = ['월','화','수','목','금','토','일'][w_idx]
                    c_class = "weekday"
                    if w_idx == 5: c_class = "sat"
                    elif w_idx == 6 or date_str in HOLIDAYS: c_class = "sun-hol"
                    
                    rows.append({
                        '요일': w_name,
                        'color_class': c_class,
                        'full_date': date_str,
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': str(item.get('placeNm', '')), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': str(item.get('eventNm', '')), 
                        '인원': str(item.get('peopleCount', '') or '-'),
                        '부서': str(item.get('mgDeptNm', '') or '-'),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 화면 출력부
with st.sidebar:
    st.title("📅 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

st.markdown('<div class="main-title">🏫 성의교정 대관 조회 시스템</div>', unsafe_allow_html=True)

df = get_data(s_date, e_date)

# 건물이 선택되어 있는 경우
if sel_bu:
    if not df.empty:
        f_df = df[df['건물명'].isin(sel_bu)].copy()
        if not f_df.empty:
            f_df['건물명'] = pd.Categorical(f_df['건물명'], categories=BUILDING_ORDER, ordered=True)
            f_df = f_df.sort_values(by=['full_date', '건물명', '시간'])

            for date in sorted(f_df['full_date'].unique()):
                d_df = f_df[f_df['full_date'] == date]
                row0 = d_df.iloc[0]
                # 요일별 컬러 표기 반영된 헤더
                st.markdown(f'''
                    <div class="date-header">
                        <span>📅 {date}</span>
                        <span class="{row0["color_class"]}">({row0["요일"]}요일)</span>
                    </div>
                ''', unsafe_allow_html=True)
                
                for b in sel_bu:
                    b_df = d_df[d_df['건물명'] == b]
                    if not b_df.empty:
                        st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                        # 모바일 인원/상태 너비 동일하게 12% 할당
                        table_html = """
                        <table>
                            <thead>
                                <tr>
                                    <th style='width:18%'>장소</th>
                                    <th style='width:17%'>시간</th>
                                    <th style='width:31%'>행사명</th>
                                    <th style='width:11%'>인원</th>
                                    <th style='width:12%'>부서</th>
                                    <th style='width:11%'>상태</th>
                                </tr>
                            </thead>
                            <tbody>
                        """
                        for _, r in b_df.iterrows():
                            table_html += f"""
                            <tr>
                                <td style='text-align:left'>{r['장소']}</td>
                                <td style='text-align:center'>{r['시간']}</td>
                                <td style='text-align:left'>{r['행사명']}</td>
                                <td style='text-align:center'>{r['인원']}</td>
                                <td style='text-align:left'>{r['부서']}</td>
                                <td style='text-align:center'>{r['상태']}</td>
                            </tr>
                            """
                        st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data">선택한 건물의 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-data">해당 날짜에 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("건물을 하나 이상 선택해주세요.")
