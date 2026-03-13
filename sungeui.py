import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정 (반드시 최상단에 위치해야 합니다)
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

# 2. 반응형 CSS 설정 (PC는 넓게, 모바일은 스크롤)
st.markdown("""
<style>
    .main-title { font-size: 24px !important; font-weight: 800; color: #1E3A5F; border-bottom: 3px solid #1E3A5F; padding-bottom: 10px; margin-bottom: 20px; }
    .date-container { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; margin-top: 30px; }
    
    /* PC와 모바일 모두를 위한 반응형 표 컨테이너 */
    .table-wrapper { 
        width: 100%; 
        overflow-x: auto; /* 모바일에서 가로 스크롤 허용 */
        margin-bottom: 20px;
    }
    
    .custom-table { 
        width: 100%;       /* PC에서는 꽉 차게 */
        min-width: 800px;  /* 모바일에서도 찌그러지지 않게 최소 너비 확보 */
        border-collapse: collapse; 
        font-size: 14px; 
        table-layout: fixed; 
    }
    
    .custom-table th { background-color: #f1f3f5; font-weight: bold; border: 1px solid #dee2e6; padding: 10px; }
    .custom-table td { border: 1px solid #dee2e6; padding: 10px 8px; text-align: center; vertical-align: middle; word-break: break-all; }
    
    .scroll-hint { text-align: right; color: #999; font-size: 11px; margin-top: -15px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# 3. 로직 및 데이터 처리 (기존 유지)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
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
                if start_date <= curr <= end_date:
                    rows.append({
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '요일': ['','월','화','수','목','금','토','일'][curr.isoweekday()],
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '부스': str(item.get('boothCount', '0')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 엑셀 생성 함수 (기존 유지)
def create_formatted_excel(df, start_date, end_date, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        title_fmt = workbook.add_format({'bold': True, 'font_size': 16, 'align': 'center'})
        # (중략된 엑셀 스타일 코드는 이전과 동일하게 유지)
    return output.getvalue()

# 5. 메인 UI
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
df = get_data(s_date, e_date)

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        wd = ['','월','화','수','목','금','토','일'][d_obj.isoweekday()]
        st.markdown(f'<div class="date-container"><h4>📅 {d_str} ({wd}) | 근무조: {get_shift(d_obj)}</h4></div>', unsafe_allow_html=True)
        
        for b in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'] == b)]
            st.markdown(f"**📍 {b}**")
            if not b_df.empty:
                rows_html = ""
                for _, r in b_df.iterrows():
                    rows_html += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['부서']}</td><td>{r['인원']}</td><td>{r['부스']}</td><td>{r['상태']}</td></tr>"
                
                # HTML 구조: PC에서는 꽉 차고 모바일에서는 800px 보장
                st.markdown(f"""
                <div class="table-wrapper">
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th style="width:12%;">장소</th><th style="width:13%;">시간</th>
                                <th style="width:35%;">행사명</th><th style="width:15%;">부서</th>
                                <th style="width:8%;">인원</th><th style="width:8%;">부스</th><th style="width:9%;">상태</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
                <div class="scroll-hint">↔ 옆으로 밀어서 보기</div>
                """, unsafe_allow_html=True)
            else:
                st.info("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
