import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 레이아웃 교정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    /* 상단 여백 재조정 (잘림 방지) */
    .block-container { padding-top: 2rem !important; padding-bottom: 0rem !important; }
    
    /* 타이틀 디자인 (스크린샷 비율 반영) */
    .main-title {
        font-size: 18px !important;
        font-weight: bold;
        color: #333;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
    }
    .main-title span { margin-right: 8px; font-size: 22px; }

    /* 남색 엑셀 버튼 */
    div.stDownloadButton > button {
        background-color: #1e3a5f !important;
        color: white !important;
        border-radius: 6px !important;
        height: 40px !important;
        font-weight: bold !important;
        font-size: 14px !important;
        border: none !important;
        margin-bottom: 15px;
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

# --- 사이드바 ---
with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("모드", ["모바일", "PC"], horizontal=True)

# --- 메인 화면 ---
# 타이틀 복원 (아이콘 + 텍스트)
st.markdown('<div class="main-title"><span>📋</span> 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

df = get_data(s_date, e_date)

if not df.empty:
    # 엑셀 다운로드 버튼
    excel_out = io.BytesIO()
    with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📊 조회 결과 엑셀 파일 다운로드", data=excel_out.getvalue(), file_name=f"현황.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f"""
            <div style="background-color:#555; color:white; padding:7px; border-radius:6px; text-align:center; margin-bottom:10px; font-weight:bold; font-size:13px;">
                📅 {d_str} | {get_shift(d_obj)}
            </div>
        """, unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            
            st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:4px 0; margin-top:10px;">
                    <div style="font-size:15px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div>
                    <div style="font-size:11px; color:#666;">총 {len(b_df)}건</div>
                </div>
            """, unsafe_allow_html=True)

            if not b_df.empty:
                if v_mode == "PC":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
                else:
                    for _, r in b_df.iterrows():
                        # [핵심 수정] 상태 표시 배지가 밀리지 않도록 고정 폭 레이아웃 적용
                        st.markdown(f"""
                            <div style="padding:8px 0; border-bottom:1px solid #eee; display:flex; flex-direction:column;">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                                    <div style="flex:1; padding-right:10px;">
                                        <div style="font-weight:bold; color:#333; font-size:14px; word-break:break-all;">📍 {r['장소']}</div>
                                    </div>
                                    <div style="text-align:right; flex-shrink:0; width:115px;">
                                        <div style="font-size:12px;"><span style="color:#666;">🕒</span> <span style="color:#e74c3c; font-weight:bold;">{r['시간']}</span></div>
                                        <div style="background-color:{'#27ae60' if r['상태']=='확정' else '#95a5a6'}; color:white; padding:1px 5px; border-radius:3px; font-size:10px; display:inline-block; margin-top:2px; font-weight:bold;">{r['상태']}</div>
                                    </div>
                                </div>
                                <div style="font-size:11px; color:#888; margin-top:4px; display:flex; align-items:flex-start;">
                                    <span style="margin-right:5px;">📄</span>
                                    <div style="word-break:break-all;">{r['행사명']} | {r['부서']}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#bbb; font-size:11px; padding:5px; text-align:center;">내역 없음</div>', unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
