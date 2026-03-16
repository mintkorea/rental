import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 0.5rem 1rem !important; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; font-size: 15px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 15px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 5px solid #1E3A5F; }
    .row-1 { display: flex; align-items: center; justify-content: space-between; margin-bottom: 5px; }
    .loc-text { font-size: 15px; font-weight: 800; color: #1E3A5F; }
    .time-status { display: flex; align-items: center; gap: 10px; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; font-weight: bold; background-color: #2ecc71; }
    .row-2 { font-size: 13px; color: #333; line-height: 1.5; border-top: 1px solid #f0f0f0; padding-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# 엑셀 생성 함수 (행높이 35 규격 적용)
def create_excel(df, sel_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('Sheet1')
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center'})
        c_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'text_wrap': True})
        # 열 너비 설정: [장소, 시간, 행사명, 부서, 인원, 상태]
        for i, w in enumerate([25, 15, 40, 20, 10, 10]): worksheet.set_column(i, i, w)
        
        row = 0
        for d in sorted(df['full_date'].unique()):
            d_df = df[df['full_date'] == d]
            for bu in sel_bu:
                b_df = d_df[d_df['건물명'] == bu]
                if b_df.empty: continue
                worksheet.merge_range(row, 0, row, 5, f"📅 {d} | 🏢 {bu}", workbook.add_format({'bold': True, 'bg_color': '#D9E1F2'})); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                for _, r in b_df.sort_values('시간').iterrows():
                    worksheet.set_row(row, 35) # 행 높이 35 고정
                    worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt)
                    row += 1
                row += 2
    return output.getvalue()

# 데이터 수집 (사용자 원본 로직으로 완전 복구)
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

# UI 구성
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
with st.expander("🔍 설정 및 엑셀 다운로드", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        s_date = st.date_input("시작일", now_today)
        e_date = st.date_input("종료일", s_date + timedelta(days=7))
    with c2:
        sel_bu = st.multiselect("건물 선택", BUILDING_ORDER, default=["성의회관", "의생명산업연구원", "옴니버스 파크"])
        v_mode = st.radio("보기 모드", ["세로 카드", "가로 표"], horizontal=True)
    
    df = get_data(s_date, e_date)
    if not df.empty:
        st.download_button("📥 최종 규격 엑셀 저장", data=create_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx")

# 리스트 출력
if df.empty:
    st.warning("조회된 대관 데이터가 없습니다. 날짜와 건물 선택을 확인해 주세요.")
else:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        d_df = df[df['full_date'] == d_str]
        # 근무조 계산 로직 (3/13 A조 기준)
        diff = (curr - date(2026, 3, 13)).days
        shift = f"{['A', 'B', 'C'][diff % 3]}조"
        
        st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {shift}</div>', unsafe_allow_html=True)
        
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
                                    <div class="time-status">
                                        <span class="time-text">🕒 {r["시간"]}</span>
                                        <span class="status-badge">{r["상태"]}</span>
                                    </div>
                                </div>
                                <div class="row-2">🏷️ <b>{r["행사명"]}</b><br>👥 {r["부서"]} | {r["인원"]}명</div>
                            </div>''', unsafe_allow_html=True)
            else:
                st.info(f"{bu}에 예정된 대관이 없습니다.")
        curr += timedelta(days=1)
