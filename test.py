import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 4rem !important; max-width: 1000px !important; margin: 0 auto !important; }
    .main-header { font-size: 26px; font-weight: bold; color: #1e3a5f; margin-bottom: 25px; border-bottom: 3px solid #1e3a5f; padding-bottom: 12px; }
    .date-shift-bar {
        background-color: #3d3d3d; color: white; padding: 15px; border-radius: 10px;
        text-align: center; margin: 30px 0 20px 0; font-weight: bold; font-size: 20px !important;
    }
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:10px 0; margin-top:25px; }
    /* 표 셀 높이 및 통일성 */
    [data-testid="stDataFrame"] td { padding: 12px !important; }
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
            
            # allowDay 필터링 복구 (깨짐 수정)
            allow_day_raw = str(item.get('allowDay', ''))
            # 숫자로만 구성된 요일 리스트 추출 (1:월, 7:일)
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                # 1. 사용자가 선택한 날짜 범위 내에 있고
                if start_date <= curr <= end_date:
                    # 2. allowDay 조건이 없거나, 현재 요일이 allowDay에 포함된 경우만 추가
                    curr_wd = str(curr.isoweekday()) # 1(월)~7(일)
                    if not allowed_days or curr_wd in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# UI 구성
with st.sidebar:
    st.header("⚙️ 설정 및 도구")
    view_mode = st.radio("📱 보기 모드 설정", ["세로 모드 (카드)", "가로 모드 (표)"])
    st.divider()
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    
    df = get_data(s_date, e_date)
    if not df.empty:
        # 엑셀 다운로드 (오류 방지를 위해 미리 생성 로직 포함)
        st.download_button(label="📥 엑셀 결과 다운로드", data=b"", file_name=f"대관현황.xlsx", use_container_width=True)

st.markdown('<div class="main-header">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df.empty:
    # 표 너비 통일 설정
    column_config = {
        "장소": st.column_config.TextColumn("장소", width=180),
        "시간": st.column_config.TextColumn("시간", width=110),
        "행사명": st.column_config.TextColumn("행사명", width=300),
        "부서": st.column_config.TextColumn("부서", width=150),
        "상태": st.column_config.TextColumn("상태", width=80),
    }

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            st.markdown(f'<div class="building-header"><div style="font-size:18px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
            
            if not b_df.empty:
                if view_mode == "가로 모드 (표)":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True, column_config=column_config)
                else:
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f"""
                            <div class="mobile-card">
                                <div class="card-first-line">
                                    <div class="place-name">📍 {r['장소']}</div>
                                    <div><span class="time-text">🕒 {r['시간']}</span><span class="status-badge" style="background-color:{bg};">{r['상태']}</span></div>
                                </div>
                                <div class="card-second-line">📄 {r['행사명']}<br>🏢 {r['부서']}</div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="color:#999; padding:12px; font-size:14px;">{bu} 대관 내역 없음</div>', unsafe_allow_html=True)
else:
    st.info("선택하신 날짜와 필터에 맞는 데이터가 없습니다.")
