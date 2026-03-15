import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# ==========================================
# 1. 페이지 설정 및 UI CSS
# ==========================================
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    /* 본문 폭 제한: PC에서 너무 퍼지지 않게 함 */
    .block-container { padding: 1.5rem 2rem !important; max-width: 1100px; margin: 0 auto; }
    
    .main-title { font-size: 26px; font-weight: 800; color: #1E3A5F; text-align: center; margin-bottom: 25px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; margin-top: 50px; margin-bottom: 10px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 15px 0 8px 0; border-left: 5px solid #1E3A5F; padding: 5px 12px; background: #f8fafd; }
    
    /* 버튼 컴팩트하게 */
    .stDownloadButton button { border: 1px solid #1E3A5F !important; color: #1E3A5F !important; font-weight: bold !important; width: auto !important; padding: 0.25rem 2rem !important; }
    </style>
""", unsafe_allow_html=True)

# (2. 엑셀 생성 및 3. 데이터 로직은 기존과 동일하므로 생략 가능하나 전체 코드를 위해 유지)
def create_excel_report(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook, worksheet = writer.book, writer.book.add_worksheet('대관현황')
        t_fmt = workbook.add_format({'bold': True, 'bg_color': '#343a40', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        b_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        c_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'shrink': True, 'font_size': 10})
        worksheet.set_column('A:A', 25); worksheet.set_column('B:B', 15); worksheet.set_column('C:C', 50); worksheet.set_column('D:D', 25); worksheet.set_column('E:F', 8)  
        row = 0
        for d_str in sorted(df['full_date'].unique()):
            worksheet.set_row(row, 30); worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", t_fmt); row += 1
            for bu in selected_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                worksheet.set_row(row, 28); worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", b_fmt); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                if not b_df.empty:
                    for _, r in b_df.sort_values('시간').iterrows():
                        worksheet.set_row(row, 35); worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt); row += 1
                else:
                    worksheet.set_row(row, 35); worksheet.merge_range(row, 0, row, 5, "대관 내역 없음", c_fmt); row += 1
                row += 1
    return output.getvalue()

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
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 상단 레이아웃
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1.5, 3, 1])
with col1:
    s_date = st.date_input("📅 기간 설정", value=now_today)
    e_date = st.date_input("종료일", value=s_date, label_visibility="collapsed")
with col2:
    sel_bu = st.multiselect("🏢 건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"], default=["성의회관", "의생명산업연구원"])
    df = get_data(s_date, e_date)
    if not df.empty:
        st.download_button("📥 최종 규격 엑셀 저장", data=create_excel_report(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx")
with col3:
    view_mode = st.radio("🖥️ 보기 모드", ["세로 카드", "가로 표"], horizontal=False)

# 5. 리스트 출력 (너비 수동 조절로 '퍼짐' 방지)
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
                # width를 숫자로 지정하여 전체 표가 너무 늘어나는 것을 방지
                st.dataframe(
                    b_df[['장소', '시간', '행사명', '부서', '인원', '상태']].sort_values('시간'),
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        "장소": st.column_config.TextColumn("장소", width=150), 
                        "시간": st.column_config.TextColumn("시간", width=120), # 중앙 정렬 느낌을 위해 폭 조절
                        "행사명": st.column_config.TextColumn("행사명", width=300), 
                        "부서": st.column_config.TextColumn("부서", width=150),
                        "인원": st.column_config.TextColumn("인원", width=60),
                        "상태": st.column_config.TextColumn("상태", width=60),
                    }
                )
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'<div style="background:white; border:1px solid #eee; padding:10px; border-radius:8px; margin-bottom:8px;"><b>📍 {r["장소"]}</b> <span style="color:red; float:right;">{r["시간"]}</span><br><small>{r["행사명"]} ({r["부서"]})</small></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="text-align:center; color:grey; font-size:12px;">내역 없음</div>', unsafe_allow_html=True)
    curr += timedelta(days=1)
