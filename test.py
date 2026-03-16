import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# ==========================================
# 1. 페이지 설정 및 UI CSS (원형 디자인 복구)
# ==========================================
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 1rem 2rem !important; max-width: 1200px; margin: 0 auto; }
    
    /* 메인 타이틀 */
    .main-title { font-size: 24px; font-weight: 800; color: #1E3A5F; text-align: center; margin-bottom: 20px; }
    
    /* 설정창 박스 디자인 (사진 기준 복구) */
    .stExpander { border: 1px solid #dfe3e8 !important; border-radius: 12px !important; background-color: #f9fbfc !important; box-shadow: 0 2px 4px rgba(0,0,0,0.03) !important; }
    
    /* 멀티셀렉트/태그 빨간색 유지 (사진 기준) */
    span[data-baseweb="tag"] { background-color: #ff4b4b !important; color: white !important; font-weight: 600 !important; }
    
    /* 날짜바 및 건물 헤더 */
    .date-bar { background-color: #40464d; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 30px; margin-bottom: 10px; font-size: 16px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 15px 0 10px 0; border-left: 5px solid #1E3A5F; padding-left: 12px; }
    
    /* 세로 카드 디자인 (사진 image_0c8ae3.png 완벽 복구) */
    .mobile-card { background: white; border: 1px solid #e0e6ed; border-radius: 10px; padding: 14px 18px; margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .card-loc { font-size: 15px; font-weight: 700; color: #333; }
    .card-time { font-size: 14px; font-weight: 600; color: #d9534f; }
    .card-content { font-size: 14px; color: #555; border-top: 1px solid #f8f9fa; padding-top: 8px; margin-top: 4px; line-height: 1.4; }
    
    /* 버튼 스타일 */
    .stDownloadButton button { width: 100%; border: 1px solid #ccd1d9 !important; border-radius: 8px !important; font-weight: bold !important; height: 42px; background-color: white !important; }
    </style>
""", unsafe_allow_html=True)

# 2. 엑셀 생성 함수 (타이틀 16pt 반영)
def create_excel_report(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('대관현황')
        title_fmt = workbook.add_format({'bold': True, 'size': 16, 'align': 'center', 'valign': 'vcenter'})
        t_fmt = workbook.add_format({'bold': True, 'bg_color': '#343a40', 'font_color': 'white', 'align': 'center', 'border': 1})
        b_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'border': 1})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'border': 1})
        c_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 10})
        
        worksheet.set_column('A:F', 18)
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", title_fmt)
        row = 2
        for d_str in sorted(df['full_date'].unique()):
            worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", t_fmt); row += 1
            for bu in selected_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", b_fmt); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                if not b_df.empty:
                    for _, r in b_df.sort_values('시간').iterrows():
                        worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt); row += 1
                else:
                    worksheet.merge_range(row, 0, row, 5, "대관 내역 없음", c_fmt); row += 1
                row += 1
    return output.getvalue()

# 3. 데이터 로직 (중복 제거)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            s, e = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s
            while curr <= e:
                if s_date <= curr <= e_date:
                    rows.append({'full_date': curr.strftime('%Y-%m-%d'), '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}", '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'})
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        return df.drop_duplicates().reset_index(drop=True) if not df.empty else df
    except: return pd.DataFrame()

# 4. 설정 UI (사진 image_0d0ea3.png 기준 레이아웃 복구)
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.expander("🔍 설정 및 엑셀 다운로드", expanded=True):
    col_a, col_b = st.columns([1, 1.5])
    with col_a:
        st.write("**📅 기간 설정**")
        s_date = st.date_input("시작일", value=now_today, label_visibility="collapsed")
        e_date = st.date_input("종료일", value=s_date, label_visibility="collapsed")
    with col_b:
        st.write("**🏢 건물 및 보기 설정**")
        sel_bu = st.multiselect("건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"], default=["성의회관", "의생명산업연구원"], label_visibility="collapsed")
        view_mode = st.radio("모드 선택", ["세로 카드", "가로 표"], horizontal=True, label_visibility="collapsed")
    
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    df = get_data(s_date, e_date)
    if not df.empty:
        st.download_button("📥 최종 규격 엑셀 저장", data=create_excel_report(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx")

# 5. 리스트 출력
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]
def get_shift(t_date):
    diff = (t_date - date(2026, 3, 13)).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

curr = s_date
while curr <= e_date:
    d_str = curr.strftime('%Y-%m-%d')
    day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
    st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")] if not day_df.empty else pd.DataFrame()
        st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
        
        if not b_df.empty:
            if view_mode == "가로 표":
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']].sort_values('시간'), hide_index=True, use_container_width=True,
                    column_config={"장소": st.column_config.TextColumn("장소", width=140), "시간": st.column_config.TextColumn("시간", width=110), "행사명": st.column_config.TextColumn("행사명", width=250), "부서": st.column_config.TextColumn("부서", width=130), "인원": st.column_config.TextColumn("인원", width=50), "상태": st.column_config.TextColumn("상태", width=50)})
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="card-top">
                                <span class="card-loc">📍 {r["장소"]}</span>
                                <span class="card-time">🕒 {r["시간"]}</span>
                            </div>
                            <div class="card-content">
                                <b>{r["행사명"]}</b><br>
                                <span style="color:#777; font-size:13px;">{r["부서"]} | {r["인원"]}명 | {r["상태"]}</span>
                            </div>
                        </div>
                    ''', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center; color:#bbb; padding:15px; font-size:13px;">내역 없음</div>', unsafe_allow_html=True)
    curr += timedelta(days=1)
