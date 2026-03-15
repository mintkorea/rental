import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import pytz
import io

# 1. 페이지 설정 및 줌 활성화
st.set_page_config(page_title="성의교정 실시간 대관 현황", layout="wide", initial_sidebar_state="expanded")
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">', unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일: 상단 여백 및 PC 모드 표 가독성 극대화
st.markdown("""
<style>
    .block-container { padding-top: 4rem !important; }
    .main-title { 
        font-size: 26px !important; font-weight: 800; color: #1e3a5f; 
        text-align: center; margin-bottom: 30px; word-break: keep-all; 
    }
    .date-header { background: #343a40; color: white; padding: 12px; border-radius: 6px; margin: 25px 0 10px 0; font-weight: 700; text-align: center; }
    .bu-header { font-size: 1.2rem !important; font-weight: 800; color: #1e3a5f; padding: 15px 0 5px 0; border-bottom: 3px solid #1e3a5f; }
    
    /* PC 모드 데이터프레임 폰트 크기 강제 확대 */
    div[data-testid="stDataFrame"] td, div[data-testid="stDataFrame"] th {
        font-size: 16px !important; 
    }
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
        # 관리자 지정 보고서 규격: 행 높이 35, 수직 가운데 정렬
        fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'font_size': 11, 'text_wrap': True})
        hdr = workbook.add_format({'bold': True, 'bg_color': '#D9D9D9', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        curr = 0
        for d_str in sorted(df['full_date'].unique()):
            worksheet.set_row(curr, 35) # 제목행 높이 35
            worksheet.merge_range(curr, 0, curr, 5, f"🗓️ {d_str} | {get_shift(datetime.strptime(d_str, '%Y-%m-%d').date())}", hdr)
            curr += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr, 35) # 건물행 높이 35
                        worksheet.merge_range(curr, 0, curr, 5, f"📍 {bu}", fmt)
                        curr += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr, 35) # 데이터행 높이 35
                            worksheet.write_row(curr, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['부스'], r['상태']], fmt)
                            curr += 1
        worksheet.set_column('A:F', 20) # 열 너비 기본 조정
    return output.getvalue()

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 검색 설정")
    start_d = st.date_input("시작일", now_today)
    end_d = st.date_input("종료일", now_today)
    sel_bu = st.multiselect("건물 필터", BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("보기 모드", ["모바일", "PC"], horizontal=True)

st.markdown('<div class="main-title">🏢 성의교정 실시간 대관 현황</div>', unsafe_allow_html=True)

df = get_data(start_d, end_d)

if not df.empty:
    st.download_button("📥 엑셀 보고서 다운로드 (행 높이 35 규격)", data=create_excel(df, sel_bu), 
                       file_name=f"대관현황_{start_d}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f'<div class="date-header">{d_str} | {get_shift(datetime.strptime(d_str, "%Y-%m-%d").date())}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">📍 {bu}</div>', unsafe_allow_html=True)
                if v_mode == "PC":
                    # PC 모드: 열 너비를 수동으로 지정하여 표마다 제각각인 현상 방지
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '부스', '상태']], 
                                 hide_index=True, 
                                 use_container_width=True,
                                 column_config={
                                     "장소": st.column_config.TextColumn("장소", width="medium"),
                                     "시간": st.column_config.TextColumn("시간", width="small")
                                 })
                else:
                    for _, r in b_df.iterrows():
                        st.markdown(f"""<div style="border-bottom:1px solid #eee; padding:15px 0;">
                            <div style="display:flex; justify-content:space-between; font-weight:700; font-size:15px;">
                                <span>📍 {r['장소']}</span><span style="color:#e74c3c;">🕒 {r['시간']}</span><span style="color:#27ae60;">{r['상태']}</span>
                            </div>
                            <div style="font-size:13px; color:gray; margin-top:8px;">{r['행사명']} ({r['부서']}, 부스 {r['부스']}개)</div>
                        </div>""", unsafe_allow_html=True)
