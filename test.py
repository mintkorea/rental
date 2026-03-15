import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 줌/모바일 설정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">', unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 2. 데이터 수집 및 allowDay 엄격 필터링
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
            
            # [핵심] 요일 필터 로직
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 엑셀 생성 함수
def create_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='현황')
    return output.getvalue()

# --- 화면 레이아웃 ---
with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("모드", ["모바일", "PC"], horizontal=True)

df = get_data(s_date, e_date)

if not df.empty:
    # [원본 디자인] 엑셀 다운로드 버튼이 메인 최상단에 위치
    st.download_button("📥 엑셀 다운로드", data=create_excel(df), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div style="background-color:#f1f3f5; padding:10px; border-radius:5px; margin-top:20px;">'
                    f'<h3>
