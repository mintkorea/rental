import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정 및 사이드바 상시 확장
st.set_page_config(
    page_title="성의교정 실시간 대관 현황", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일 (가이드라인 준수: 장소명 1줄 고정)
st.markdown("""
<style>
    .event-shell {{ border-bottom: 1px solid #eee; padding: 12px 5px; background: white; }}
    .row-main {{ display: flex; align-items: center; justify-content: space-between; gap: 5px; }}
    .col-place {{ 
        flex: 5.8; font-weight: 700; color: #1e3a5f; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block;
    }}
    .col-time {{ flex: 2.7; font-size: 13px; color: #d9534f; font-weight: bold; text-align: center; white-space: nowrap; }}
    .col-status {{ flex: 1.5; font-size: 12px; font-weight: bold; text-align: right; }}
    .row-sub {{ font-size: 12px; color: #666; margin-top: 6px; line-height: 1.4; }}
    .main-title {{ font-size: 2.0rem; font-weight: 900; color: #1e3a5f; text-align: center; margin-bottom: 15px; }}
</style>
""", unsafe_allow_html=True)

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    shifts = ['A', 'B', 'C']
    return shifts[diff % 3] + "조"

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
            
            allow_day_raw = str(item.get('allowDay', '')).strip()
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_weekday = str(curr.isoweekday())
                    if not allowed_days or curr_weekday in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': "{0}~{1}".format(item.get('startTime', ''), item.get('endTime', '')),
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 사이드바 구성 (가이드라인 준수: 모바일 기본 세팅)
with st.sidebar:
    st.header("🔍 설정")
    view_mode = st.radio("📺 보기 모드", ["PC 모드", "모바일(세로)"], index=1)
    col1, col2 = st.columns(2)
    with col1: s_date = st.date_input("시작일", value=now_today)
    with col2: e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

st.markdown('<div class="main-title">🏢 성의교정 실시간 대관 현황</div>', unsafe_allow_html=True)

df = get_data(s_date, e_date)

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        date_header = '<div style="background-color:#444; color:white; padding:10px; border-radius:5px; margin-top:20px; font-weight:bold;">'
        date_header += '🗓️ {0} | 근무조: {1}</div>'.format(d_str, get_shift(d_obj))
        st.markdown(date_header, unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                badge = '<span style="background-color:#e1e8f0; padding:2px 10px; border-radius:15px; font-size:14px; font-weight:bold; color:black;">총 {0}건</span>'.format(len(b_df))
                st.markdown('<div style="display:flex; align-items:center; justify-content:space-between; border-bottom:2px solid #1e3a5f; margin-top:15px; padding-bottom:5px;"><h3 style="margin:0; color:#1e3a5f;">🏢 {0}</h3>{1}</div>'.format(bu, badge), unsafe_allow_html=True)
                
                if view_mode == "모바일(세로)":
                    for _, row in b_df.iterrows():
                        st_color = "#28a745" if row['상태'] == "확정" else "#d9534f"
                        # 장소명 길이에 따른 가변 폰트 적용 (가이드라인 준수)
                        p_name = row['장소']
                        p_font = "14px"
                        if len(p_name) > 10: p_font = "12px"
                        if len(p_name) > 14: p_font = "10.5px"

                        # SyntaxError 방지를 위해 .format() 사용
                        html_item = """
                        <div class="event-shell">
                            <div class="row-main">
                                <div class="col-place" style="font-size:{0};">📍 {1}</div>
                                <div class="col-time">🕒 {2}</div>
                                <div class="col-status" style="color:{3}; font-weight:bold;">{4}</div>
                            </div>
                            <div class="row-sub">📄 {5}<br>({6}, {7}명)</div>
                        </div>
                        """.format(p_font, p_name, row['시간'], st_color, row['상태'], row['행사명'], row['부서'], row['인원'])
                        st.markdown(html_item, unsafe_allow_html=True)
                else:
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
else:
    st.info("조회된 내역이 없습니다.")
