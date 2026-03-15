import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# ==========================================
# 1. 페이지 설정 및 사용자 지정 UI CSS
# ==========================================
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 0.5rem 1rem !important; }
    
    /* 타이틀 */
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    
    /* 날짜 바: 간격 55px 규정 준수 */
    .date-bar { 
        background-color: #343a40; color: white; padding: 12px; border-radius: 6px; 
        text-align: center; font-weight: bold; margin-top: 55px; margin-bottom: 15px; font-size: 15px; 
    }
    .date-bar:first-of-type { margin-top: 0px; }

    /* 건물 헤더 */
    .bu-header { 
        font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 15px 0 10px 0; 
        border-left: 5px solid #1E3A5F; padding: 6px 12px; background: #f1f4f9; 
    }
    
    /* 카드 디자인: 시간 우측 정렬 규정 준수 */
    .mobile-card { 
        background: white; border: 1px solid #eef0f2; border-radius: 6px; 
        padding: 10px 12px; margin-bottom: 8px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); 
    }
    .row-1 { display: flex; align-items: center; white-space: nowrap; width: 100%; }
    .loc-text { font-size: 13px; font-weight: 800; color: #1E3A5F; flex: 1; overflow: hidden; text-overflow: ellipsis; }
    .time-text { font-size: 12px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; flex-shrink: 0; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; background-color: #2ecc71; flex-shrink: 0; }
    
    .row-2 { font-size: 11px; color: #555; border-top: 1px solid #f8f9fa; padding-top: 6px; margin-top: 6px; }
    .no-data { color: #7f8c8d; font-size: 12px; padding: 12px; background: #f8f9fa; border-radius: 6px; border: 1px dashed #ced4da; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 엑셀 생성 함수 (지정 정수 수치 및 높이 35 규정)
# ==========================================
def create_excel_report(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 스타일 정의
        t_fmt = workbook.add_format({'bold': True, 'bg_color': '#343a40', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        b_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        
        # 데이터 서식: 자동 개행 + 폰트 자동 축소(Shrink)
        c_fmt = workbook.add_format({
            'align': 'center', 'valign': 'vcenter', 'border': 1, 
            'text_wrap': True, 'shrink': True, 'font_size': 10
        })

        # [규정] 열 넓이 (정수값)
        worksheet.set_column('A:A', 25) # 장소
        worksheet.set_column('B:B', 15) # 시간
        worksheet.set_column('C:C', 50) # 행사명
        worksheet.set_column('D:D', 25) # 부서
        worksheet.set_column('E:F', 8)  # 인원, 상태

        row = 0
        for d_str in sorted(df['full_date'].unique()):
            # 날짜 바
            worksheet.set_row(row, 30)
            worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", t_fmt); row += 1
            
            for bu in selected_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                # 건물 바
                worksheet.set_row(row, 28)
                worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", b_fmt); row += 1
                
                # 헤더
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']):
                    worksheet.write(row, col, h, h_fmt)
                row += 1
                
                # 데이터 출력
                if not b_df.empty:
                    for _, r in b_df.sort_values('시간').iterrows():
                        # [규정] 행 높이 35 고정
                        worksheet.set_row(row, 35)
                        worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt)
                        row += 1
                else:
                    worksheet.set_row(row, 35)
                    worksheet.merge_range(row, 0, row, 5, "대관 내역 없음", c_fmt); row += 1
                row += 1
    return output.getvalue()

# ==========================================
# 3. 데이터 로직 (검색 알고리즘 완벽 복구)
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
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s
            while curr <= e:
                if s_date <= curr <= e_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
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

# ==========================================
# 4. 메인 화면 구성
# ==========================================
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.expander("🔍 설정 및 엑셀 다운로드", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        s_date = st.date_input("시작일", value=now_today)
        e_date = st.date_input("종료일", value=s_date)
    with c2:
        sel_bu = st.multiselect("건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"], default=["성의회관", "의생명산업연구원"])
        view_mode = st.radio("보기 모드", ["세로 카드", "가로 표"], horizontal=True)
    
    df = get_data(s_date, e_date)
    
    if not df.empty:
        st.download_button(
            label="📥 최종 규격 엑셀 저장",
            data=create_excel_report(df, sel_bu),
            file_name=f"대관현황_{s_date}.xlsx",
            use_container_width=True
        )

# ==========================================
# 5. 리스트 출력 (가로/세로 전환)
# ==========================================
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]
def get_shift(t_date):
    # 2026-03-13 기준 A조 순환 로직
    diff = (t_date - date(2026, 3, 13)).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

curr = s_date
while curr <= e_date:
    d_str = curr.strftime('%Y-%m-%d')
    day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
    
    # 날짜 바 (55px 마진 적용됨)
    st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr.isoweekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")] if not day_df.empty else pd.DataFrame()
        st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
        
        if not b_df.empty:
            if view_mode == "가로 표":
                # 가로 모드: 표 형식
                st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태']].sort_values('시간'), hide_index=True, use_container_width=True)
            else:
                # 세로 모드: 카드 형식
                for _, r in b_df.sort_values('시간').iterrows():
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="row-1">
                                <span class="loc-text">📍 {r["장소"]}</span>
                                <span class="time-text">🕒 {r["시간"]}</span>
                                <span class="status-badge">확정</span>
                            </div>
                            <div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                        </div>
                    ''', unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data">ℹ️ 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
    
    curr += timedelta(days=1)
