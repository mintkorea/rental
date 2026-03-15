import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">', unsafe_allow_html=True)

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

# --- 화면 출력부 (남색 디자인 적용) ---
with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(s_date, e_date)

if not df.empty:
    # [사진 2번 디자인] 진한 남색 배경의 엑셀 다운로드 버튼
    st.markdown("""
        <style>
        div.stDownloadButton > button {
            background-color: #1e3a5f !important;
            color: white !important;
            border-radius: 8px !important;
            height: 50px !important;
            font-weight: bold !important;
            font-size: 16px !important;
            border: none !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.download_button("📊 조회 결과 엑셀 파일 다운로드", data="...", file_name=f"현황.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        # [사진 2번 디자인] 진한 회색 날짜 바
        st.markdown(f"""
            <div style="background-color:#4d4d4d; color:white; padding:10px; border-radius:8px; text-align:center; margin-bottom:20px; font-weight:bold;">
                📅 {d_str} | {get_shift(d_obj)}
            </div>
        """, unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                # [사진 2번 디자인] 건물명 바 + 총 N건 표시
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:5px 0; margin-top:15px;">
                        <div style="font-size:18px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div>
                        <div style="font-size:12px; color:#666;">총 {len(b_df)}건</div>
                    </div>
                """, unsafe_allow_html=True)
                
                for _, r in b_df.iterrows():
                    # [사진 2번 디자인] 장소(핀), 시간(시계), 행사명(문서) 아이콘 레이아웃
                    st.markdown(f"""
                        <div style="padding:10px 0; border-bottom:1px solid #eee;">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <div style="font-weight:bold; color:#333;">📍 {r['장소']}</div>
                                <div style="font-size:13px;">
                                    <span style="color:#666;">🕒</span> <span style="color:#e74c3c; font-weight:bold;">{r['시간']}</span>
                                    <span style="color:#27ae60; margin-left:10px; font-weight:bold;">{r['상태']}</span>
                                </div>
                            </div>
                            <div style="font-size:12px; color:#888; margin-top:4px; display:flex; align-items:flex-start;">
                                <span style="margin-right:5px;">📄</span>
                                <div>{r['행사명']} ({r['부서']})</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
