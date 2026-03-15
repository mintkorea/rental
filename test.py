import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import pytz
import io

# 1. 페이지 설정 (브라우저 타이틀)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 웹 화면 CSS (여백 및 간격 최소화)
st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    header {visibility: hidden;}
    .main-title { font-size: 24px; font-weight: bold; color: #1E3A5F; text-align: center; margin: 0; padding: 5px 0; }
    .date-bar { background-color: #343a40; color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 10px; }
    .bu-header { font-size: 16px; font-weight: bold; color: #1E3A5F; margin: 10px 0 5px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; }

    /* 카드 포맷: 시간 우측 배치 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 8px 12px; margin-bottom: 5px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex-shrink: 0; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 12px; }
    .status-badge { padding: 1px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; min-width: 38px; text-align: center; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    
    .row-2 { font-size: 12px; color: #555; border-top: 1px solid #f8f9fa; margin-top: 4px; padding-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (에러 방지 강화)
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": d.isoformat(), "end": d.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            rows.append({
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', '') or '-',
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', '') or '-',
                '부서': item.get('mgDeptNm', '') or '-',
                '인원': str(item.get('peopleCount', '0')),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except Exception: return pd.DataFrame()

# 4. 엑셀 출력 (인쇄 설정: 여백 10, 타이틀 18pt)
def create_excel(df, selected_buildings, d_str, shift):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        worksheet.set_margins(left=0.39, right=0.39) # 좌우여백 10
        
        title_fmt = workbook.add_format({'bold':True, 'font_size':18, 'align':'center', 'valign':'vcenter'})
        sub_fmt = workbook.add_format({'bold':True, 'font_size':11, 'align':'right'})
        hdr_fmt = workbook.add_format({'bold':True, 'bg_color':'#333333', 'font_color':'white', 'align':'center', 'valign':'vcenter', 'border':1})
        bu_fmt = workbook.add_format({'bold':True, 'font_size':11, 'bg_color':'#EBF1F8', 'border':1, 'valign':'vcenter'})
        cell_fmt = workbook.add_format({'border':1, 'align':'center', 'valign':'vcenter', 'text_wrap':True, 'shrink':True})
        
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", title_fmt)
        worksheet.set_row(0, 30)
        worksheet.merge_range('A2:F2', f"일자: {d_str} ({shift})", sub_fmt)
        
        curr_row = 3
        for bu in BUILDING_ORDER:
            if bu in selected_buildings:
                b_df = df[df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if not b_df.empty:
                    worksheet.set_row(curr_row, 35)
                    worksheet.merge_range(curr_row, 0, curr_row, 5, f"  🏢 {bu} ({len(b_df)}건)", bu_fmt)
                    curr_row += 1
                    worksheet.write_row(curr_row, 0, ["장소", "시간", "행사명", "부서", "인원", "상태"], hdr_fmt)
                    curr_row += 1
                    for _, r in b_df.sort_values('시간').iterrows():
                        worksheet.set_row(curr_row, 35)
                        worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], cell_fmt)
                        curr_row += 1
                    curr_row += 1 # 표 사이 1줄 개행
        
        worksheet.set_column('A:A', 25); worksheet.set_column('B:B', 15); worksheet.set_column('C:C', 44)
        worksheet.set_column('D:D', 25); worksheet.set_column('E:E', 6); worksheet.set_column('F:F', 6)
        
    return output.getvalue()

# 5. UI 구성
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 설정")
    view_mode = st.radio("모드", ["세로 카드", "가로 표"])
    target_date = st.date_input("날짜", value=now_today)
    sel_bu = st.multiselect("건물", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(target_date)

if not df.empty:
    shift_val = get_shift(target_date)
    st.markdown(f'<div class="date-bar">📅 {target_date} | {shift_val}</div>', unsafe_allow_html=True)
    
    with st.sidebar:
        st.download_button("📥 엑셀 출력", data=create_excel(df, sel_bu, str(target_date), shift_val), 
                           file_name=f"대관현황_{target_date}.xlsx", use_container_width=True)

    for bu in sel_bu:
        b_df = df[df['건물명'].str.replace(" ", "") == bu.replace(" ", "")]
        if not b_df.empty:
            st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
            if view_mode == "가로 표":
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']], hide_index=True, use_container_width=True)
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="row-1">
                                <span class="loc-text">📍 {r["장소"]}</span>
                                <span class="time-text">🕒 {r["시간"]}</span>
                                <span class="status-badge {s_cls}">{r["상태"]}</span>
                            </div>
                            <div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                        </div>
                    ''', unsafe_allow_html=True)
else:
    st.info("내역이 없습니다.")
