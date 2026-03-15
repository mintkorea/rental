import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 CSS (폰트 크기 대폭 강화)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    /* 타이틀 폰트 확대 (28px) */
    .main-title { font-size: 28px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    /* 날짜바 폰트 확대 (18px) */
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 12px; font-size: 18px; }
    /* 건물 헤더 폰트 확대 (20px) */
    .bu-header { font-size: 20px; font-weight: bold; color: #1E3A5F; margin: 15px 0 8px 0; border-left: 6px solid #1E3A5F; padding-left: 12px; background: #f1f4f9; padding-top: 5px; padding-bottom: 5px; }
    
    .no-data { color: #7f8c8d; font-size: 14px; padding: 12px; background: #f8f9fa; border-radius: 4px; border: 1px dashed #ced4da; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 15px; margin-bottom: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; }
    .loc-text { font-size: 15px; font-weight: 800; color: #1E3A5F; }
    .time-text { font-size: 14px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 15px; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; font-weight: bold; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    .row-2 { font-size: 13px; color: #333; border-top: 1px solid #f8f9fa; margin-top: 6px; padding-top: 6px; }
    
    /* 사이드바 열기 안내문 */
    .sidebar-hint { font-size: 12px; color: #666; margin-bottom: 10px; text-align: left; }
    </style>
""", unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 2. 엑셀 생성 (기존 포맷 유지)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('대관현황')
        hdr_fmt = workbook.add_format({'bold':True,'bg_color':'#333333','font_color':'white','align':'center','border':1})
        bu_fmt = workbook.add_format({'bold':True,'bg_color':'#EBF1F8','border':1})
        cell_fmt = workbook.add_format({'border':1,'align':'center','valign':'vcenter','text_wrap':True})
        curr_row = 0
        for d_str in sorted(df['full_date'].unique()):
            d_df = df[df['full_date'] == d_str]
            worksheet.merge_range(curr_row, 0, curr_row, 5, f"📅 {d_str}", hdr_fmt)
            curr_row += 1
            for bu in selected_buildings:
                b_df = d_df[d_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if not b_df.empty:
                    worksheet.merge_range(curr_row, 0, curr_row, 5, f"🏢 {bu}", bu_fmt)
                    curr_row += 1
                    for _, r in b_df.iterrows():
                        worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], cell_fmt)
                        curr_row += 1
            curr_row += 1
    return output.getvalue()

# 3. 데이터 로직 (엄격 필터링)
@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt, e_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({'full_date': curr.strftime('%Y-%m-%d'), '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}", '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'})
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. UI 출력
st.markdown('<div class="sidebar-hint">⬅️ 왼쪽 화살표(>)를 눌러 날짜와 건물을 설정하세요.</div>', unsafe_allow_html=True)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

if not df.empty:
    with st.sidebar:
        st.download_button("📥 엑셀 다운로드", data=create_formatted_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
        st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")] if not day_df.empty else pd.DataFrame()
            # 건물명 옆에 건수 표시 복구
            st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
            if not b_df.empty:
                for _, r in b_df.sort_values('시간').iterrows():
                    s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                    st.markdown(f'<div class="mobile-card"><div class="row-1"><span class="loc-text">📍 {r["장소"]}</span><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge {s_cls}">{r["상태"]}</span></div><div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div></div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="no-data">ℹ️ 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
        curr += timedelta(days=1)
