import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인 CSS
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    
    /* 화면 가로 폭 제한 및 중앙 정렬 */
    .main .block-container {
        max-width: 1200px;  /* 가로 폭 1200px 제한 */
        margin: 0 auto;
        padding: 0.5rem 1rem !important;
    }
    
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; font-size: 15px; }
    .date-bar:first-of-type { margin-top: 0px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .row-1 { display: flex; align-items: center; white-space: nowrap; width: 100%; }
    .loc-text { font-size: 13px; font-weight: 800; color: #1E3A5F; flex: 1; overflow: hidden; text-overflow: ellipsis; }
    .time-text { font-size: 12px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; flex-shrink: 0; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; background-color: #2ecc71; flex-shrink: 0; }
    
    .row-2 { 
        font-size: 11px; color: #555; border-top: 1px solid #f8f9fa; padding-top: 5px; margin-top: 5px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
        overflow: hidden; line-height: 1.4; max-height: 2.8em; word-break: break-all;
    }
    .no-data { color: #7f8c8d; font-size: 12px; padding: 12px; background: #f8f9fa; border-radius: 6px; border: 1px dashed #ced4da; text-align: center; }
    </style>
""", unsafe_allow_html=True)

def create_excel(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        t_fmt = workbook.add_format({'bold': True, 'size': 16, 'align': 'center', 'valign': 'vcenter'})
        d_fmt = workbook.add_format({'bold': True, 'bg_color': '#3d444b', 'font_color': 'white', 'align': 'center', 'border': 1})
        b_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'border': 1})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'border': 1})
        c_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})

        widths = [25, 15, 40, 20, 10, 10]
        for i, w in enumerate(widths): worksheet.set_column(i, i, w)
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", t_fmt)
        
        row = 2
        for d_str in sorted(df['full_date'].unique()):
            worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", d_fmt); row += 1
            current_day_bu = [b for b in BUILDING_ORDER if b in selected_bu]
            for bu in current_day_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", b_fmt); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                for _, r in b_df.sort_values('시간').iterrows():
                    worksheet.set_row(row, 35)
                    worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt)
                    row += 1
                row += 1
    return output.getvalue()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

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
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({'full_date': curr.strftime('%Y-%m-%d'), '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}", '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'})
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
with st.expander("🔍 설정 (날짜/건물/다운로드)", expanded=True):
    # 상단 메뉴 3열 배치
    c1, c2, c3 = st.columns([1.5, 2, 1])
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with c2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])
    with c3:
        view_mode = st.radio("보기", ["세로 카드", "가로 표"], horizontal=True)
        df = get_data(s_date, e_date)
        if not df.empty:
            st.download_button("📥 최종 규격 엑셀 저장", data=create_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str]
        st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
            st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
            if not b_df.empty:
                if view_mode == "가로 표":
                    st.dataframe(
                        b_df[['장소', '시간', '행사명', '부서', '인원', '상태']].sort_values('시간'),
                        hide_index=True,
                        use_container_width=True,
                        column_config={
                            "장소": st.column_config.TextColumn(width="medium"),
                            "시간": st.column_config.TextColumn(width="small"),
                            "행사명": st.column_config.TextColumn(width="large"),
                            "부서": st.column_config.TextColumn(width="medium"),
                            "인원": st.column_config.TextColumn(width="small"),
                            "상태": st.column_config.TextColumn(width="small"),
                        }
                    )
                else:
                    for _, r in b_df.sort_values('시간').iterrows():
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="row-1">
                                    <span class="loc-text">📍 {r["장소"]}</span>
                                    <span class="time-text">🕒 {r["시간"]}</span>
                                    <span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span>
                                </div>
                                <div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                            </div>''', unsafe_allow_html=True)
            else:
                st.markdown('<div class="no-data">ℹ️ 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("선택한 날짜에 대관 데이터가 없거나 불러오는 중입니다.")
