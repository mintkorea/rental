import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import pytz
import io

# 1. 페이지 설정 및 줌(Zoom) 활성화
st.set_page_config(page_title="성의교정 실시간 대관 현황", layout="wide", initial_sidebar_state="expanded")
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">', unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일: 상단 여백 확보 및 타이틀 잘림 방지
st.markdown("""
<style>
    /* 상단 여백 3.5rem으로 확대하여 타이틀 잘림 절대 방지 */
    .block-container { padding-top: 3.5rem !important; }
    .main-title { 
        font-size: 24px !important; font-weight: 800; color: #1e3a5f; 
        text-align: center; margin-bottom: 25px; word-break: keep-all; line-height: 1.4;
    }
    .date-header { background: #4a4a4a; color: white; padding: 12px; border-radius: 6px; margin: 20px 0 10px 0; font-weight: 700; text-align: center; }
    .bu-header { font-size: 1.1rem !important; font-weight: 800; color: #1e3a5f; padding: 12px 0 5px 0; border-bottom: 2.5px solid #1e3a5f; margin-bottom: 10px; }
    
    /* 모바일 리스트 레이아웃 */
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 0; }
    .row-main { display: grid; grid-template-columns: 5fr 3.5fr 1.5fr; align-items: center; width: 100%; }
    .col-place { font-weight: 700; color: #1e3a5f; font-size: 14px; }
    .col-time { font-size: 12px; color: #e74c3c; font-weight: 700; text-align: center; }
    .col-status { font-size: 12px; font-weight: 900; text-align: right; color: #27ae60; }
    
    /* 버튼 스타일 */
    div.stDownloadButton > button { width: 100% !important; background-color: #1e3a5f !important; color: white !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return "{0}조".format(['A', 'B', 'C'][diff % 3])

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
            if start_date <= s_dt <= end_date:
                rows.append({
                    'full_date': s_dt.strftime('%Y-%m-%d'),
                    '건물명': str(item.get('buNm', '')).strip(),
                    '장소': item.get('placeNm', '') or '-',
                    '시간': "{0}~{1}".format(item.get('startTime', ''), item.get('endTime', '')),
                    '행사명': item.get('eventNm', '') or '-',
                    '부서': item.get('mgDeptNm', '') or '-',
                    '부스': str(item.get('boothCount', '0')),
                    '상태': '확정' if item.get('status') == 'Y' else '대기'
                })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def create_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('현황')
        # 관리자 지시 규격: 행 높이 35, 테두리 고정
        fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'font_size': 10, 'text_wrap': True})
        hdr = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        curr = 0
        for d_str in sorted(df['full_date'].unique()):
            worksheet.set_row(curr, 35)
            worksheet.merge_range(curr, 0, curr, 5, f"🗓️ {d_str} | {get_shift(datetime.strptime(d_str, '%Y-%m-%d').date())}", hdr)
            curr += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr, 35)
                        worksheet.merge_range(curr, 0, curr, 5, f"📍 {bu}", fmt)
                        curr += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr, 35)
                            worksheet.write_row(curr, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['부스'], r['상태']], fmt)
                            curr += 1
    return output.getvalue()

# --- 사이드바 필터 ---
with st.sidebar:
    st.header("⚙️ 관리 설정")
    start_d = st.date_input("조회 시작일", now_today)
    end_d = st.date_input("조회 종료일", now_today)
    sel_bu = st.multiselect("건물 필터", BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("모드 전환", ["모바일", "PC"], horizontal=True)

# --- 메인 영역 ---
st.markdown('<div class="main-title">🏛️ 성의교정 실시간 대관 현황</div>', unsafe_allow_html=True)

df = get_data(start_d, end_d)

if not df.empty:
    st.download_button("📊 조회 결과 엑셀 다운로드 (규격 준수)", data=create_excel(df, sel_bu), 
                       file_name=f"대관현황_{start_d}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-header">{d_str} | {get_shift(datetime.strptime(d_str, "%Y-%m-%d").date())}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">📍 {bu}</div>', unsafe_allow_html=True)
                if v_mode == "PC":
                    # PC 모드: 인덱스 숫자 제거(hide_index=True)
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '부스', '상태']], hide_index=True, use_container_width=True)
                else:
                    for _, r in b_df.iterrows():
                        st.markdown(f"""<div class="event-shell">
                            <div class="row-main">
                                <div class="col-place">{r['장소']}</div>
                                <div class="col-time">{r['시간']}</div>
                                <div class="col-status">{r['상태']}</div>
                            </div>
                            <div style="font-size:12px; color:gray; margin-top:5px;">{r['행사명']} ({r['부서']}, 부스 {r['부스']}개)</div>
                        </div>""", unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
