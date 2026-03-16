import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 홈페이지 UI 가이드라인 반영 (2행 제한 및 폰트 축소)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 1.5rem 2rem !important; max-width: 1200px; margin: 0 auto; }
    .main-title { font-size: 26px; font-weight: 800; color: #1E3A5F; text-align: center; margin-bottom: 25px; }
    
    .date-bar { background-color: #3d444b; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 20px 0 10px 0; border-left: 5px solid #1E3A5F; padding-left: 12px; }
    
    /* 웹페이지 카드: 최대 2행 개행 허용 및 폰트 제어 */
    .mobile-card { background: white; border: 1px solid #eef2f6; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    .card-row-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .card-loc { font-size: 15px; font-weight: 800; color: #1E3A5F; }
    .card-time { font-size: 14px; font-weight: 700; color: #ff4b4b; }
    
    .card-event { 
        font-size: 14px; font-weight: 700; color: #333; margin-top: 5px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
        overflow: hidden; line-height: 1.3; word-break: break-all;
    }
    .card-info { font-size: 13px; color: #777; margin-top: 3px; }
    </style>
""", unsafe_allow_html=True)

# 2. 엑셀 가이드라인 (행 높이 35, 열 너비 커스텀)
def create_excel_report(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 서식 설정
        title_fmt = workbook.add_format({'bold': True, 'size': 16, 'align': 'center', 'valign': 'vcenter'})
        date_fmt = workbook.add_format({'bold': True, 'bg_color': '#3d444b', 'font_color': 'white', 'align': 'center', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'border': 1})
        head_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'border': 1})
        cell_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 10})
        
        # [약속] 열 너비 적용
        worksheet.set_column('A:A', 25) # 장소
        worksheet.set_column('B:B', 15) # 시간
        worksheet.set_column('C:C', 40) # 행사명
        worksheet.set_column('D:D', 20) # 부서
        worksheet.set_column('E:F', 10) # 인원/상태
        
        # 1행 타이틀 (16pt)
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", title_fmt)
        
        row = 2
        for d_str in sorted(df['full_date'].unique()):
            worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", date_fmt); row += 1
            for bu in selected_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", bu_fmt); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']):
                    worksheet.write(row, col, h, head_fmt)
                row += 1
                if not b_df.empty:
                    for _, r in b_df.sort_values('시간').iterrows():
                        # [약속] 행 높이 35 고정
                        worksheet.set_row(row, 35)
                        worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], cell_fmt)
                        row += 1
                else:
                    worksheet.set_row(row, 35)
                    worksheet.merge_range(row, 0, row, 5, "내역 없음", cell_fmt); row += 1
                row += 1
    return output.getvalue()

# 3. 데이터 로직 (검색 0건 문제 해결 버전)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        raw_res = res.json().get('res', [])
        rows = []
        for item in raw_res:
            if not item.get('startDt'): continue
            s, e = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s
            while curr <= e:
                if s_date <= curr <= e_date:
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
        df = pd.DataFrame(rows)
        # 3/16 성의회관 2건 조회를 위한 정확한 중복 제거
        return df.drop_duplicates().reset_index(drop=True) if not df.empty else df
    except Exception as e:
        return pd.DataFrame()

# 4. 상단 설정 UI (원본 유지)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
with st.expander("🔍 설정 및 엑셀 다운로드", expanded=True):
    col1, col2, col3, col4 = st.columns([1, 1, 2.5, 1])
    with col1: s_d = st.date_input("시작일", value=now_today)
    with col2: e_d = st.date_input("종료일", value=s_d)
    with col3: bu_s = st.multiselect("건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"], default=["성의회관", "의생명산업연구원"])
    with col4: v_m = st.radio("보기 모드", ["세로 카드", "가로 표"])
    
    df = get_data(s_d, e_d)
    if not df.empty:
        st.download_button("📥 최종 규격 엑셀 저장", data=create_excel_report(df, bu_s), file_name=f"대관현황_{s_d}.xlsx")

# 5. 리스트 출력 (가이드라인 반영)
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]
def get_shift(t_date):
    diff = (t_date - date(2026, 3, 13)).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

curr = s_d
while curr <= e_d:
    d_str = curr.strftime('%Y-%m-%d')
    day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
    st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
    for bu in bu_s:
        b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")] if not day_df.empty else pd.DataFrame()
        st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
        if not b_df.empty:
            if v_m == "가로 표":
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']].sort_values('시간'), hide_index=True, use_container_width=True)
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="card-row-top"><span class="card-loc">📍 {r["장소"]}</span><span class="card-time">🕒 {r["시간"]}</span></div>
                            <div class="card-event">{r["행사명"]}</div>
                            <div class="card-info">{r["부서"]} | {r["인원"]}명 | {r["상태"]}</div>
                        </div>''', unsafe_allow_html=True)
    curr += timedelta(days=1)
