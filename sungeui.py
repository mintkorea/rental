import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 초기 설정 및 CSS (다크모드 완벽 방어)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

st.markdown("""
<style>
    /* 다크모드 방어: 배경 흰색, 글자 검은색 고정 */
    .stApp { background-color: white !important; color: black !important; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F !important; margin-bottom: 20px; }
    
    /* 요일 색상 */
    .sat { color: #4A90E2 !important; font-weight: bold; } /* 토요일: 청색 */
    .sun-hol { color: #E74C3C !important; font-weight: bold; } /* 일요일/공휴일: 적색 */
    
    /* 날짜 헤더 */
    .date-header { 
        background-color: #2E5077 !important; color: white !important; padding: 10px 15px; 
        border-radius: 5px; margin-top: 30px; display: flex; 
        justify-content: space-between; align-items: center;
    }
    
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333 !important; }
    
    /* 테이블 스타일 */
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white !important; border: 1px solid #ddd !important; }
    th { background-color: #f8f9fa !important; color: #333 !important; border: 1px solid #ccc !important; text-align: center !important; padding: 10px 2px; font-size: 13px; }
    td { border: 1px solid #eee !important; color: #333 !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; background-color: white !important; }
    
    /* 건물별 결과 없음 안내 (사용자 요청 사항) */
    .no-building-data { color: #d9534f; font-size: 14px; font-weight: bold; padding: 15px; border: 1px dashed #d9534f; border-radius: 5px; margin-top: 10px; text-align: center; background-color: #fffafa !important; }
</style>
""", unsafe_allow_html=True)

# 2. 데이터 로드 (allowDay 로직 보존)
@st.cache_data(ttl=60)
def get_rental_data(s_date, e_date):
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
            
            # [복구] 사용자님의 핵심 allowDay 필터 로직
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        d_str = curr.strftime('%Y-%m-%d')
                        w_idx = curr.weekday()
                        c_class = "weekday"
                        if w_idx == 5: c_class = "sat"
                        elif w_idx == 6: c_class = "sun-hol"
                        
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][w_idx],
                            'color_class': c_class,
                            'full_date': d_str,
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 사이드바 및 출력 로직
with st.sidebar:
    st.header("📅 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if sel_bu:
    df = get_rental_data(s_date, e_date)
    
    if df.empty:
        st.info("해당 기간에 조회된 전체 대관 내역이 없습니다.")
    else:
        df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
        for date in sorted(df['full_date'].unique()):
            d_df = df[df['full_date'] == date]
            
            st.markdown(f'''
                <div class="date-header">
                    <span>📅 {date}</span>
                    <span class="{d_df.iloc[0]['color_class']}">({d_df.iloc[0]['요일']}요일)</span>
                </div>
            ''', unsafe_allow_html=True)
            
            # 선택된 모든 건물에 대해 루프를 돌며 내역 확인
            for b in sel_bu:
                b_df = d_df[d_df['건물명'] == b]
                st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
                
                if not b_df.empty:
                    table_html = """
                    <table>
                        <thead>
                            <tr>
                                <th style='width:18%'>장소</th><th style='width:17%'>시간</th><th style='width:20%'>행사명</th>
                                <th style='width:10%'>인원</th><th style='width:25%'>부서</th><th style='width:10%'>상태</th>
                            </tr>
                        </thead>
                        <tbody>"""
                    for _, r in b_df.sort_values('시간').iterrows():
                        table_html += f"<tr><td style='text-align:left'>{r['장소']}</td><td style='text-align:center'>{r['시간']}</td><td style='text-align:left'>{r['행사명']}</td><td style='text-align:center'>{r['인원']}</td><td style='text-align:left'>{r['부서']}</td><td style='text-align:center'>{r['상태']}</td></tr>"
                    st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
                else:
                    # [핵심] 의산연 등 선택했지만 결과가 없는 건물에 대한 개별 안내
                    st.markdown(f'<div class="no-building-data">"{b}"에 대한 오늘 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.warning("건물을 선택해 주세요.")
