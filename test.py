import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 스타일 정의
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    /* 상단 여백 확보 (타이틀 잘림 방지) */
    .block-container { padding-top: 4rem !important; padding-bottom: 2rem !important; }
    
    /* 메인 타이틀 스타일 */
    .main-title {
        font-size: 20px !important;
        font-weight: bold;
        color: #333;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
    }
    .main-title span { margin-right: 10px; font-size: 24px; }

    /* 엑셀 다운로드 버튼 (남색 디자인) */
    div.stDownloadButton > button {
        background-color: #1e3a5f !important;
        color: white !important;
        border-radius: 6px !important;
        height: 45px !important;
        font-weight: bold !important;
        width: 100%;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# 기초 설정
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

# --- 사이드바 (변수 정의) ---
with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("모드", ["모바일", "PC"], horizontal=True)

# --- 메인 화면 출력 ---
st.markdown('<div class="main-title"><span>📋</span> 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

# 데이터 호출 (사이드바 변수 사용)
df = get_data(s_date, e_date)

if not df.empty:
    # 엑셀 다운로드
    excel_out = io.BytesIO()
    with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📊 조회 결과 엑셀 파일 다운로드", data=excel_out.getvalue(), file_name=f"현황.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f"""
            <div style="background-color:#555; color:white; padding:8px; border-radius:6px; text-align:center; margin-top:15px; font-weight:bold; font-size:14px;">
                📅 {d_str} | {get_shift(d_obj)}
            </div>
        """, unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            
            if not b_df.empty:
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:flex-end; border-bottom:2px solid #1e3a5f; padding:5px 0; margin-top:15px;">
                        <div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div>
                        <div style="font-size:11px; color:#666;">총 {len(b_df)}건</div>
                    </div>
                """, unsafe_allow_html=True)

                if v_mode == "PC":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
                else:
                    for _, r in b_df.iterrows():
                        # [상태 배지 줄바꿈 방지 적용]
                        st.markdown(f"""
                            <div style="padding:10px 0; border-bottom:1px solid #eee;">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">
                                    <div style="flex:1; min-width:0;">
                                        <div style="font-weight:bold; color:#333; font-size:14px; word-break:break-all;">📍 {r['장소']}</div>
                                    </div>
                                    <div style="text-align:right; flex-shrink:0;">
                                        <div style="font-size:12px; margin-bottom:3px;">
                                            <span style="color:#666;">🕒</span> <span style="color:#e74c3c; font-weight:bold; white-space:nowrap;">{r['시간']}</span>
                                        </div>
                                        <div style="background-color:{'#27ae60' if r['상태']=='확정' else '#95a5a6'}; 
                                                    color:white; padding:2px 6px; border-radius:4px; font-size:10px; 
                                                    display:inline-block; font-weight:bold; white-space:nowrap;">
                                            {r['상태']}
                                        </div>
                                    </div>
                                </div>
                                <div style="font-size:11px; color:#888; margin-top:5px; line-height:1.4;">
                                    📄 {r['행사명']} | {r['부서']}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
