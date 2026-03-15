import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 좌우 여백 10 고정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
<style>
    /* 페이지 좌우 여백 10 */
    .block-container { padding-left: 10px !important; padding-right: 10px !important; padding-top: 1rem !important; }
    
    /* PC 모드 표: 장소/부서 2행 노출 보장 */
    div[data-testid="stDataFrame"] td {
        white-space: normal !important;
        word-break: keep-all !important;
        line-height: 1.2 !important;
    }
    /* 모바일 디자인 복구: 타이틀 및 여백 */
    h3 { margin-top: 20px !important; margin-bottom: 10px !important; font-size: 1.5rem !important; }
    h4 { margin-top: 15px !important; margin-bottom: 5px !important; color: #1e3a5f !important; }
</style>
""", unsafe_allow_html=True)

# 줌 기능 유지
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
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    rows.append({
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '부스': str(item.get('boothCount', '0')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기',
                        'is_period': s_dt != e_dt
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        hdr_fmt = workbook.add_format({'bold': True, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True})
        
        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['부스'], r['상태']], cell_fmt)
                            curr_row += 1
                        curr_row += 1
        worksheet.set_column('A:A', 20)
        worksheet.set_column('B:B', 14) # 시간 셸 +2 확대
        worksheet.set_column('C:C', 35)
        worksheet.set_column('D:D', 18)
    return output.getvalue()

# --- 화면 출력 ---
with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("모드", ["모바일", "PC"], horizontal=True)

df = get_data(s_date, e_date)

if not df.empty:
    with st.sidebar:
        st.download_button("📥 엑셀 다운로드", data=create_formatted_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f"### 📅 {d_str} | {get_shift(d_obj)}")
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                st.markdown(f"#### 📍 {bu}")
                if v_mode == "PC":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], 
                                 use_container_width=True, hide_index=True,
                                 column_config={
                                     "장소": st.column_config.TextColumn("장소", width="medium"),
                                     "시간": st.column_config.TextColumn("시간", width=140),
                                     "부서": st.column_config.TextColumn("부서", width="medium")
                                 })
                else:
                    # 모바일 디자인 복구 (16:05 원본 스타일)
                    for _, r in b_df.iterrows():
                        st.markdown(f"""
                        <div style="border-bottom:1px solid #eee; padding:8px 0;">
                            <div style="display:flex; justify-content:space-between;">
                                <strong>📍 {r['장소']}</strong>
                                <span style="color:#e74c3c; font-size:13px; font-weight:bold;">🕒 {r['시간']}</span>
                            </div>
                            <div style="font-size:12px; color:#666;">{r['행사명']} ({r['부서']}, {r['인원']}명)</div>
                        </div>
                        """, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
