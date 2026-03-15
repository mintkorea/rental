import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 4rem !important; }
    section[data-testid="stSidebar"] { min-width: 320px !important; }
    .main-title { font-size: 18px !important; font-weight: bold; margin-bottom: 20px; display: flex; align-items: center; }
    .event-card { padding: 12px 0; border-bottom: 1px solid #eee; width: 100%; }
    .first-line { display: flex; justify-content: space-between; align-items: center; gap: 8px; width: 100%; }
    .place-name { flex: 1; min-width: 0; font-weight: bold; color: #333; font-size: 14px; line-height: 1.2; white-space: nowrap; overflow: hidden; }
    .status-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
    .time-text { font-size: 11px; color: #e74c3c; font-weight: bold; white-space: nowrap; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; color: white; white-space: nowrap; }
    .second-line { font-size: 11px; color: #888; margin-top: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .building-header { display:flex; justify-content:space-between; align-items:flex-end; border-bottom:2px solid #1e3a5f; padding:4px 0; margin-top:15px; }
    .count-text { font-size: 14px !important; font-weight: 900 !important; color: #000; }
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
                    # allowDay 엄격 필터링
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
    v_mode = st.radio("모드", ["모바일", "PC"], horizontal=True)

st.markdown('<div class="main-title"><span>📋</span> 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

# 데이터 로드 및 필터링
df = get_data(s_date, e_date)
filtered_df = pd.DataFrame()

if not df.empty and sel_bu:
    sel_bu_keys = [b.replace(" ", "") for b in sel_bu]
    filtered_df = df[df['건물명_key'].isin(sel_bu_keys)].copy()

# --- 결과 출력 로직 (수정 핵심) ---
# 1. 필터링된 데이터가 전혀 없는 경우 (의산연 단독 선택 시 포함)
if filtered_df.empty:
    st.info("대관 내역이 없습니다.")
else:
    # 2. 데이터가 있는 경우 출력
    excel_out = io.BytesIO()
    with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:
        filtered_df[['full_date', '건물명_raw', '장소', '시간', '행사명', '부서', '상태']].to_excel(writer, index=False)
    st.download_button("📊 조회 결과 엑셀 다운로드", data=excel_out.getvalue(), file_name=f"현황.xlsx", use_container_width=True)

    for d_str in sorted(filtered_df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div style="background-color:#555; color:white; padding:7px; border-radius:6px; text-align:center; margin-top:15px; font-weight:bold; font-size:13px;">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            target_key = bu.replace(" ", "")
            b_df = filtered_df[(filtered_df['full_date'] == d_str) & (filtered_df['건물명_key'] == target_key)]
            
            if not b_df.empty:
                st.markdown(f'<div class="building-header"><div style="font-size:15px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
                if v_mode == "PC":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
                else:
                    for _, r in b_df.iterrows():
                        bg_color = '#27ae60' if r['상태']=='확정' else '#95a5a6'
                        st.markdown(f'<div class="event-card"><div class="first-line"><div class="place-name">📍 {r["장소"]}</div><div class="status-right"><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge" style="background-color:{bg_color};">{r["상태"]}</span></div></div><div class="second-line">📄 {r["행사명"]} | {r["부서"]}</div></div>', unsafe_allow_html=True)
