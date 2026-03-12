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

# 공휴일 설정 (필요시 추가)
HOLIDAYS = ["2026-01-01", "2026-03-01", "2026-05-05", "2026-08-15", "2026-10-03", "2026-10-09", "2026-12-25"]
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. 웹 화면 CSS (요일 색상 및 모바일 너비 조정)
st.markdown("""
<style>
    .stApp { background-color: #ffffff; color: #000000; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; margin-bottom: 20px; color: #1E3A5F; }
    
    /* 요일 표시 헤더 */
    .date-header { 
        font-size: 18px !important; font-weight: 800; color: white; 
        background-color: #2E5077; padding: 10px 15px; margin-top: 30px; 
        border-radius: 5px; display: flex; justify-content: space-between;
    }
    /* 요일별 색상 클래스 */
    .sat { color: #5D9CEC !important; } /* 토요일 청색 */
    .sun-hol { color: #ED5565 !important; } /* 일요일/공휴일 적색 */
    
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 6px solid #2E5077; padding-left: 12px; color: #333; }
    
    table { width: 100%; border-collapse: collapse; table-layout: fixed; border: 1px solid #ddd; }
    th { background-color: #f2f5f8; border: 1px solid #ccc; padding: 10px 5px; font-size: 13px; color: #333; text-align: center !important; }
    td { border: 1px solid #eee; padding: 10px 5px; font-size: 13px; vertical-align: middle; color: #333; }
    
    .no-data { text-align: center; padding: 40px; font-size: 16px; color: #ff4b4b; border: 2px dashed #ff4b4b; border-radius: 10px; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 요일 판별
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
                    weekday_idx = curr.weekday() # 5:토, 6:일
                    
                    # 색상 클래스 결정
                    color_class = ""
                    if weekday_idx == 5: color_class = "sat"
                    elif weekday_idx == 6 or date_str in HOLIDAYS: color_class = "sun-hol"
                    
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][weekday_idx],
                        'color_class': color_class,
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

# 4. 실행 및 UI
with st.sidebar:
    st.title("📅 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

df = get_data(s_date, e_date)
st.markdown('<div class="main-title">🏫 성의교정 대관 조회 시스템</div>', unsafe_allow_html=True)

if not df.empty:
    f_df = df[df['건물명'].isin(sel_bu)].copy()
    if not f_df.empty:
        f_df['건물명'] = pd.Categorical(f_df['건물명'], categories=BUILDING_ORDER, ordered=True)
        f_df = f_df.sort_values(by=['full_date', '건물명', '시간'])

        for date in sorted(f_df['full_date'].unique()):
            d_df = f_df[f_df['full_date'] == date]
            row0 = d_df.iloc[0]
            # 헤더에 요일 색상 적용
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
                    # 모바일 대응 너비 조정 (인원/상태 동일하게 10% 할당)
                    table_html = """
                    <table>
                        <thead>
                            <tr>
                                <th style='width:18%'>장소</th>
                                <th style='width:17%'>시간</th>
                                <th style='width:35%'>행사명</th>
                                <th style='width:10%'>인원</th>
                                <th style='width:10%'>부서</th>
                                <th style='width:10%'>상태</th>
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
        st.markdown('<div class="no-data">선택한 건물에 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="no-data">조회된 대관 내역이 없습니다.</div>', unsafe_allow_html=True)

