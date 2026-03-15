import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# ==========================================
# 1. 페이지 설정 및 강화된 UI CSS
# ==========================================
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 1rem 3rem !important; max-width: 1200px; margin: 0 auto; }
    
    /* 메인 타이틀 세련되게 */
    .main-title { 
        font-size: 26px; font-weight: 800; color: #1E3A5F; text-align: center; 
        margin-bottom: 25px; letter-spacing: -1px;
    }
    
    /* 멀티셀렉터 배지 색상 변경 */
    span[data-baseweb="tag"] { background-color: #1E3A5F !important; }
    
    /* 날짜 바: 55px 여백 */
    .date-bar { 
        background-color: #343a40; color: white; padding: 12px; border-radius: 8px; 
        text-align: center; font-weight: bold; margin-top: 55px; margin-bottom: 15px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .date-bar:first-of-type { margin-top: 0px; }

    /* 건물 헤더 */
    .bu-header { 
        font-size: 18px; font-weight: bold; color: #1E3A5F; margin: 20px 0 10px 0; 
        border-left: 6px solid #1E3A5F; padding: 8px 15px; background: #f8fafd; 
        border-radius: 0 4px 4px 0;
    }
    
    /* 카드 디자인 */
    .mobile-card { 
        background: white; border: 1px solid #eef2f6; border-radius: 8px; 
        padding: 15px; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .row-1 { display: flex; align-items: center; justify-content: space-between; width: 100%; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; }
    .time-text { font-size: 14px; font-weight: 700; color: #d9534f; }
    .status-badge { padding: 3px 8px; border-radius: 4px; font-size: 11px; color: white; font-weight: bold; background-color: #28a745; }
    
    .row-2 { font-size: 13px; color: #444; border-top: 1px solid #f1f3f5; padding-top: 10px; margin-top: 10px; line-height: 1.4; }
    .no-data { color: #868e96; font-size: 13px; padding: 20px; background: #fcfcfc; border-radius: 8px; border: 1px dashed #dee2e6; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 엑셀 생성 함수 (규정 수치 준수)
# ==========================================
def create_excel_report(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        t_fmt = workbook.add_format({'bold': True, 'bg_color': '#343a40', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        b_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        c_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'shrink': True, 'font_size': 10})

        worksheet.set_column('A:A', 25) 
        worksheet.set_column('B:B', 15) 
        worksheet.set_column('C:C', 50) 
        worksheet.set_column('D:D', 25) 
        worksheet.set_column('E:F', 8)  

        row = 0
        for d_str in sorted(df['full_date'].unique()):
            worksheet.set_row(row, 30)
            worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", t_fmt); row += 1
            for bu in selected_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                worksheet.set_row(row, 28)
                worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", b_fmt); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                if not b_df.empty:
                    for _, r in b_df.sort_values('시간').iterrows():
                        worksheet.set_row(row, 35)
                        worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt); row += 1
                else:
                    worksheet.set_row(row, 35); worksheet.merge_range(row, 0, row, 5, "대관 내역 없음", c_fmt); row += 1
                row += 1
    return output.getvalue()

# ==========================================
# 3. 데이터 로직
# ==========================================
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

# ==========================================
# 4. PC용 세련된 레이아웃 (3열 배치)
# ==========================================
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.container():
    # PC에서는 가로로 3분할, 모바일에서는 자동 세로 전환
    col1, col2, col3 = st.columns([1.5, 3, 1])
    
    with col1:
        s_date = st.date_input("📅 기간 (시작/종료)", value=now_today, label_visibility="visible")
        e_date = st.date_input("종료일 선택", value=s_date, label_visibility="collapsed")
        
    with col2:
        sel_bu = st.multiselect("🏢 건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"], default=["성의회관", "의생명산업연구원"])
        
    with col3:
        view_mode = st.radio("🖥️ 보기 모드", ["세로 카드", "가로 표"], horizontal=False)

    df = get_data(s_date, e_date)
    
    if not df.empty:
        st.download_button("📥 최종 규격 엑셀 저장", data=create_excel_report(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

st.markdown("---")

# ==========================================
# 5. 리스트 출력
# ==========================================
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
                st.dataframe(
                    b_df[['장소', '시간', '행사명', '부서', '인원', '상태']].sort_values('시간'),
                    hide_index=True, use_container_width=True,
                    column_config={
                        "장소": st.column_config.TextColumn("장소", width="medium"), 
                        "시간": st.column_config.TextColumn("시간", width="small"),
                        "행사명": st.column_config.TextColumn("행사명", width="large"), 
                        "부서": st.column_config.TextColumn("부서", width="medium"),
                        "인원": st.column_config.TextColumn("인원", width="small"),
                        "상태": st.column_config.TextColumn("상태", width="small"),
                    }
                )
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="row-1">
                                <span class="loc-text">📍 {r["장소"]}</span>
                                <span class="time-text">🕒 {r["시간"]}</span>
                                <span class="status-badge">확정</span>
                            </div>
                            <div class="row-2"><b>{r["행사명"]}</b><br><span style="color:#666;">{r["부서"]} | {r["인원"]}명</span></div>
                        </div>
                    ''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data">ℹ️ 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    curr += timedelta(days=1)
