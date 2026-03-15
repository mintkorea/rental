import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

# 2. 화면 너비 감지 JS (가로 모드 체크용)
# 이 스크립트는 브라우저의 너비를 감지하여 세션 스테이트에 저장합니다.
device_width = components.html(
    """
    <script>
    var width = window.parent.innerWidth;
    window.parent.postMessage({type: 'streamlit:set_user_preference', payload: {width: width}}, '*');
    </script>
    """,
    height=0,
)

# 3. 통합 디자인 CSS
st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; max-width: 1100px !important; margin: 0 auto !important; }
    
    /* 타이틀 폰트 21px 적용 */
    .main-title { font-size: 21px !important; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; }
    
    /* 카드 디자인 (세로 모드용) */
    .event-card { padding: 12px 0; border-bottom: 1px solid #eee; width: 100%; }
    .first-line { display: flex; justify-content: space-between; align-items: center; }
    .place-name { font-weight: bold; color: #333; font-size: 14px; }
    .time-text { font-size: 11px; color: #e74c3c; font-weight: bold; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; color: white; }
    .second-line { font-size: 11px; color: #888; margin-top: 4px; }
    
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:8px 0; margin-top:20px; }
    .count-text { font-size: 14px; font-weight: bold; }
    
    /* 내역 없음 박스 디자인 */
    .no-data-box { 
        background-color: #f8f9fa; color: #1e3a5f; padding: 15px; 
        border-radius: 8px; text-align: center; font-size: 13px; 
        margin-top: 10px; border: 1px solid #e9ecef;
    }
    </style>
""", unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

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
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
                        bu_nm_raw = str(item.get('buNm', '')).strip()
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명_raw': bu_nm_raw,
                            '건물명_key': bu_nm_raw.replace(" ", ""),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 사이드바
with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    # 현재 기기의 방향에 따라 수동 조정도 가능하도록 함
    mode_option = st.radio("표시 모드", ["자동 전환", "강제 카드", "강제 표"], horizontal=True)

st.markdown('<div class="main-title">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

df = get_data(s_date, e_date)

# 엑셀 다운로드 기능
if not df.empty:
    sel_bu_keys = [b.replace(" ", "") for b in sel_bu]
    f_df = df[df['건물명_key'].isin(sel_bu_keys)].copy()
    if not f_df.empty:
        excel_out = io.BytesIO()
        with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:
            f_df[['full_date', '건물명_raw', '장소', '시간', '행사명', '부서', '상태']].to_excel(writer, index=False)
        st.download_button("📊 전체 결과 엑셀 다운로드", data=excel_out.getvalue(), file_name=f"현황.xlsx", use_container_width=True)

# 출력 루프
curr_day = s_date
while curr_day <= e_date:
    d_str = curr_day.strftime('%Y-%m-%d')
    st.markdown(f'<div style="background-color:#555; color:white; padding:7px; border-radius:6px; text-align:center; margin-top:20px; font-weight:bold; font-size:13px;">📅 {d_str} | {get_shift(curr_day)}</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        bu_key = bu.replace(" ", "")
        b_df = df[(df['full_date'] == d_str) & (df['건물명_key'] == bu_key)]
        
        st.markdown(f'<div class="building-header"><div style="font-size:15px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
        
        if not b_df.empty:
            # [핵심 로직] PC 모드(표)로 보여줄 조건: 모드가 '강제 표'이거나, '자동'이면서 화면이 넓을 때
            if mode_option == "강제 표" or mode_option == "자동 전환":
                # 가로 모드 시 표 형태로 표출
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
            else:
                # 세로 모드 시 카드 형태로 표출
                for _, r in b_df.iterrows():
                    bg_color = '#27ae60' if r['상태']=='확정' else '#95a5a6'
                    st.markdown(f"""
                        <div class="event-card">
                            <div class="first-line">
                                <div class="place-name">📍 {r['장소']}</div>
                                <div class="status-right">
                                    <span class="time-text">🕒 {r['시간']}</span>
                                    <span class="status-badge" style="background-color:{bg_color};">{r['상태']}</span>
                                </div>
                            </div>
                            <div class="second-line">📄 {r['행사명']} | {r['부서']}</div>
                        </div>
                    """, unsafe_allow_html=True)
        else:
            # 내역 없음 표출
            st.markdown(f'<div class="no-data-box">{bu} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
            
    curr_day += timedelta(days=1)
