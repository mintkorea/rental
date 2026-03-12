import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz

# 1. 페이지 설정 (다크모드에서도 흰색 배경 유지)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

st.markdown("""
<style>
    /* 배경 및 기본 텍스트 색상 고정 */
    .stApp { background-color: white !important; color: black !important; }
    
    /* 요일별 색상 */
    .sat { color: #4A90E2 !important; font-weight: bold; } /* 토요일: 청색 */
    .sun-hol { color: #E74C3C !important; font-weight: bold; } /* 일요일/공휴일: 적색 */
    .weekday { color: white !important; } /* 평일: 흰색(배경 대비) */
    
    /* 날짜 헤더 */
    .date-header { 
        background-color: #2E5077; color: white; padding: 10px 15px; 
        border-radius: 5px; margin-top: 25px; display: flex; 
        justify-content: space-between; align-items: center;
    }
    
    /* 테이블 스타일링 (헤더 중앙정렬 및 너비 고정) */
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white; border: 1px solid #ddd; }
    th { background-color: #f8f9fa !important; color: #333 !important; border: 1px solid #ccc !important; text-align: center !important; padding: 10px 2px; font-size: 13px; }
    td { border: 1px solid #eee !important; color: #333 !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; }
    
    /* 결과 없음 박스 */
    .empty-box { text-align: center; padding: 40px; color: #ff4b4b; border: 2px dashed #ff4b4b; border-radius: 10px; margin-top: 20px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 2. 데이터 처리 로직
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
# 공휴일 설정
HOLIDAYS = ["2026-01-01", "2026-03-01", "2026-05-05", "2026-06-06", "2026-08-15", "2026-10-03", "2026-10-09", "2026-12-25"]
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

@st.cache_data(ttl=60)
def fetch_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    d_str = curr.strftime('%Y-%m-%d')
                    w_idx = curr.weekday()
                    # 요일별 CSS 클래스 지정
                    c_class = "weekday"
                    if w_idx == 5: c_class = "sat"
                    elif w_idx == 6 or d_str in HOLIDAYS: c_class = "sun-hol"
                    
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][w_idx],
                        'c_class': c_class,
                        'full_date': d_str,
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

# 3. 사이드바 구성
with st.sidebar:
    st.header("📅 조회 옵션")
    s_d = st.date_input("시작일", value=now_today)
    e_d = st.date_input("종료일", value=s_d)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

# 4. 메인 화면
st.markdown('<h2 style="text-align:center;">🏫 성의교정 대관 현황 조회</h2>', unsafe_allow_html=True)

if sel_bu:
    df = fetch_data(s_d, e_d)
    if not df.empty:
        f_df = df[df['건물명'].isin(sel_bu)].copy()
        if not f_df.empty:
            f_df['건물명'] = pd.Categorical(f_df['건물명'], categories=BUILDING_ORDER, ordered=True)
            f_df = f_df.sort_values(by=['full_date', '건물명', '시간'])

            for date in sorted(f_df['full_date'].unique()):
                d_df = f_df[f_df['full_date'] == date]
                # 날짜 및 요일 컬러 출력
                st.markdown(f'''
                    <div class="date-header">
                        <span>📅 {date}</span>
                        <span class="{d_df.iloc[0]['c_class']}">({d_df.iloc[0]['요일']}요일)</span>
                    </div>
                ''', unsafe_allow_html=True)
                
                for b in sel_bu:
                    b_df = d_df[d_df['건물명'] == b]
                    if not b_df.empty:
                        st.markdown(f'<div style="margin:15px 0 10px 0; font-weight:bold; border-left:5px solid #2E5077; padding-left:10px;">🏢 {b}</div>', unsafe_allow_html=True)
                        # 모바일 대응 표 (너비 조정)
                        table_html = """
                        <table>
                            <thead>
                                <tr>
                                    <th style='width:18%'>장소</th><th style='width:17%'>시간</th><th style='width:29%'>행사명</th>
                                    <th style='width:12%'>인원</th><th style='width:12%'>부서</th><th style='width:12%'>상태</th>
                                </tr>
                            </thead>
                            <tbody>"""
                        for _, r in b_df.iterrows():
                            table_html += f"<tr><td style='text-align:left'>{r['장소']}</td><td style='text-align:center'>{r['시간']}</td><td style='text-align:left'>{r['행사명']}</td><td style='text-align:center'>{r['인원']}</td><td style='text-align:left'>{r['부서']}</td><td style='text-align:center'>{r['상태']}</td></tr>"
                        st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty-box">선택한 건물의 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty-box">조회된 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회할 건물을 선택해주세요.")
