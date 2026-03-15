import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 정밀 CSS 보정 (요청하신 레이아웃 반영)
st.markdown("""
    <style>
    .block-container { padding: 1.5rem 2rem !important; }
    
    /* 가로 모드 표: 열 너비 강제 고정 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; border: 1px solid #dee2e6; }
    .custom-table th { background-color: #f8f9fa; color: #1E3A5F; padding: 12px 5px; border: 1px solid #dee2e6; font-weight: 800; font-size: 14px; }
    .custom-table td { padding: 12px 8px; border: 1px solid #dee2e6; text-align: center; font-size: 14px; vertical-align: middle; word-break: break-all; }
    .col-1 { width: 20%; } .col-2 { width: 18%; } .col-3 { width: 35%; } .col-4 { width: 15%; } .col-5 { width: 12%; }

    /* 세로 모드 카드: 장소/시간/상태 1줄 + 행사/부서/인원 1줄 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 12px; padding: 18px; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }
    
    /* 첫 번째 줄: 장소, 시간, 상태 */
    .card-top-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px; }
    .card-place-time { display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 800; color: #1E3A5F; }
    .card-time-sub { color: #e74c3c; font-size: 15px; font-weight: 700; }
    .status-badge { padding: 3px 10px; border-radius: 5px; font-size: 11px; font-weight: bold; color: white; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }

    /* 두 번째 줄: 행사명 / 부서 (인원) */
    .card-bottom-row { font-size: 14px; color: #444; border-top: 1px solid #f4f5f7; padding-top: 10px; line-height: 1.5; }
    .event-name { font-weight: 700; color: #2c3e50; }
    .dept-info { color: #666; }

    /* 헤더 스타일 */
    .date-bar { background-color: #343a40; color: white; padding: 12px; border-radius: 8px; text-align: center; font-weight: bold; margin: 20px 0; font-size: 18px; }
    .bu-header { font-size: 19px; font-weight: bold; color: #1E3A5F; margin: 30px 0 10px 0; border-left: 6px solid #1E3A5F; padding-left: 12px; }
    </style>
""", unsafe_allow_html=True)

# 3. 로직 및 데이터 처리
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
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed_days = [str(x.strip()) for x in str(item.get('allowDay', '')).split(",") if x.strip().isdigit()]
            if s_dt <= d <= e_dt:
                if not allowed_days or str(d.isoweekday()) in allowed_days:
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
    except: return pd.DataFrame()

# 4. 엑셀 생성 (초기 PC 버전 행 높이 35 및 서식 복구)
def create_excel(df, selected_buildings, d_str, shift):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        hdr_fmt = workbook.add_format({'bold':True,'font_size':12,'bg_color':'#333333','font_color':'white','align':'center','valign':'vcenter','border':1})
        bu_fmt = workbook.add_format({'bold':True,'font_size':11,'bg_color':'#EBF1F8','align':'left','valign':'vcenter','border':1})
        cell_fmt = workbook.add_format({'border':1,'align':'center','valign':'vcenter','text_wrap':True,'shrink':True})
        
        curr_row = 0
        worksheet.set_row(curr_row, 35)
        worksheet.merge_range(curr_row, 0, curr_row, 5, f"📅 {d_str} | 근무조: {shift}", hdr_fmt)
        curr_row += 1
        
        for bu in BUILDING_ORDER:
            if bu in selected_buildings:
                b_df = df[df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if not b_df.empty:
                    worksheet.set_row(curr_row, 35)
                    worksheet.merge_range(curr_row, 0, curr_row, 5, f"  📍 {bu}", bu_fmt)
                    curr_row += 1
                    for _, r in b_df.iterrows():
                        worksheet.set_row(curr_row, 35) # 행 높이 35 고정
                        worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], cell_fmt)
                        curr_row += 1
        worksheet.set_column('A:D', 20); worksheet.set_column('E:F', 8)
    return output.getvalue()

# 5. UI 메인 레이아웃
with st.sidebar:
    st.header("🔍 설정")
    view_mode = st.radio("보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"])
    target_date = st.date_input("날짜", value=now_today)
    sel_bu = st.multiselect("건물", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(target_date)

if not df.empty:
    with st.sidebar:
        shift_val = get_shift(target_date)
        st.download_button("📥 엑셀 다운로드", 
                           data=create_excel(df, sel_bu, target_date.strftime("%Y-%m-%d"), shift_val),
                           file_name=f"대관현황_{target_date}.xlsx", use_container_width=True)

    st.markdown(f'<div class="date-bar">📅 {target_date.strftime("%Y-%m-%d")} | 근무조: {shift_val}</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        b_df = df[df['건물명'].str.replace(" ", "") == bu.replace(" ", "")]
        if not b_df.empty:
            st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
            if view_mode == "가로 모드 (표)":
                html = '<table class="custom-table"><thead><tr><th class="col-1">장소</th><th class="col-2">시간</th><th class="col-3">행사명</th><th class="col-4">부서</th><th class="col-5">인원/상태</th></tr></thead><tbody>'
                for _, r in b_df.sort_values('시간').iterrows():
                    html += f'<tr><td>{r["장소"]}</td><td>{r["시간"]}</td><td style="text-align:left;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["인원"]}명 / {r["상태"]}</td></tr>'
                st.markdown(html + '</tbody></table>', unsafe_allow_html=True)
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="card-top-row">
                                <div class="card-place-time">
                                    <span>📍 {r["장소"]}</span>
                                    <span class="card-time-sub">🕒 {r["시간"]}</span>
                                </div>
                                <span class="status-badge {s_cls}">{r["상태"]}</span>
                            </div>
                            <div class="card-bottom-row">
                                <span class="event-name">🏷️ {r["행사명"]}</span><br>
                                <span class="dept-info">🏢 {r["부서"]} ({r["인원"]}명)</span>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
else:
    st.info("조회된 대관 내역이 없습니다.")
