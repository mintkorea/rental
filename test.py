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

# CSS (사용자님 원본 디자인 + 가독성만 보정)
st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 0.5rem 1rem !important; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; font-size: 15px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 8px 12px; margin-bottom: 6px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); border-left: 4px solid #1E3A5F; }
    .row-1 { display: flex; align-items: center; width: 100%; margin-bottom: 4px; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex: 1; }
    .time-text { font-size: 12px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; background-color: #2ecc71; }
    .row-2 { font-size: 12px; color: #555; line-height: 1.4; }
    </style>
""", unsafe_allow_html=True)

# 엑셀 생성 함수
def create_excel(df, sel_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('Sheet1')
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        c_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        for i, w in enumerate([25, 15, 40, 20, 10, 10]): worksheet.set_column(i, i, w)
        row = 0
        for d in sorted(df['full_date'].unique()):
            d_df = df[df['full_date'] == d]
            for bu in sel_bu:
                b_df = d_df[d_df['건물명'] == bu]
                if b_df.empty: continue
                worksheet.write(row, 0, f"📅 {d} | 🏢 {bu}", workbook.add_format({'bold': True})); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                for _, r in b_df.sort_values('시간').iterrows():
                    worksheet.set_row(row, 35)
                    worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt)
                    row += 1
                row += 1
    return output.getvalue()

# 데이터 로직 (가장 안정적인 방식)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

@st.cache_data(ttl=60)
def get_data(s_d, e_d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    try:
        res = requests.get(url, params={"mode": "getReservedData", "start": s_d.isoformat(), "end": e_d.isoformat()}, timeout=15)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s
            while curr <= e:
                if s_d <= curr <= e_d:
                    rows.append({
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# UI 메인
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
with st.expander("🔍 설정 (날짜/건물/다운로드)", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        s_date = st.date_input("시작일", now_today)
        e_date = st.date_input("종료일", s_date + timedelta(days=14)) # 넉넉하게 2주치 기본 설정
    with c2:
        sel_bu = st.multiselect("건물 선택", BUILDING_ORDER, default=BUILDING_ORDER)
        v_mode = st.radio("보기", ["세로 카드", "가로 표"], horizontal=True)
    
    df = get_data(s_date, e_date)
    if not df.empty:
        st.download_button("📥 최종 규격 엑셀 저장", data=create_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx")

# 결과 출력
if df.empty:
    st.error("데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")
else:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        d_df = df[df['full_date'] == d_str]
        st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일)</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = d_df[d_df['건물명'] == bu]
            st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
            if not b_df.empty:
                if v_mode == "가로 표":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']].sort_values('시간'), hide_index=True, use_container_width=True)
                else:
                    for _, r in b_df.sort_values('시간').iterrows():
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="row-1">
                                    <span class="loc-text">📍 {r["장소"]}</span>
                                    <span class="time-text">🕒 {r["시간"]}</span>
                                    <span class="status-badge">{r["상태"]}</span>
                                </div>
                                <div class="row-2">🏷️ <b>{r["행사명"]}</b><br>👥 {r["부서"]} | {r["인원"]}명</div>
                            </div>''', unsafe_allow_html=True)
            else:
                st.info("내역 없음")
        curr += timedelta(days=1)
        
