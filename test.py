import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date
import pytz
import io

# 1. 페이지 설정 및 홈페이지 타이틀
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 웹 화면 CSS (세로 모드 2줄 구성 및 줌 최적화)
st.markdown("""
    <style>
    .block-container { padding: 1rem !important; }
    .main-title { font-size: 28px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 20px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 20px; }
    
    /* 세로 모드 카드: 2줄 압축 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 8px; padding: 12px; margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 14px; font-weight: 800; color: #1E3A5F; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    .row-2 { font-size: 12px; color: #555; border-top: 1px solid #f8f9fa; padding-top: 6px; }
    
    /* 가로 모드 표 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-top: 10px; }
    .custom-table th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; font-size: 13px; font-weight: 800; }
    .custom-table td { border: 1px solid #dee2e6; padding: 10px; text-align: center; font-size: 13px; vertical-align: middle; word-break: break-all; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (KeyError 방지)
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

# 4. 엑셀 출력 (인쇄 설정: 여백 10, 타이틀 18pt, 건물별 표 분리, 개행)
def create_excel(df, selected_buildings, d_str, shift):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 인쇄 설정: 좌우 여백 10 (약 0.39인치)
        worksheet.set_margins(left=0.39, right=0.39)
        
        # 서식 정의
        title_fmt = workbook.add_format({'bold':True, 'font_size':18, 'align':'center', 'valign':'vcenter'})
        sub_fmt = workbook.add_format({'bold':True, 'font_size':11, 'align':'right'})
        hdr_fmt = workbook.add_format({'bold':True, 'bg_color':'#333333', 'font_color':'white', 'align':'center', 'valign':'vcenter', 'border':1})
        bu_fmt = workbook.add_format({'bold':True, 'font_size':11, 'bg_color':'#EBF1F8', 'border':1, 'valign':'vcenter'})
        cell_fmt = workbook.add_format({'border':1, 'align':'center', 'valign':'vcenter', 'text_wrap':True, 'shrink':True})
        
        # 1. 메인 타이틀 (18pt)
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", title_fmt)
        worksheet.set_row(0, 30)
        
        # 2. 날짜 및 근무조 정보
        worksheet.merge_range('A2:F2', f"조회일자: {d_str} ({shift})", sub_fmt)
        
        curr_row = 3
        for bu in BUILDING_ORDER:
            if bu in selected_buildings:
                b_df = df[df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if not b_df.empty:
                    # 건물 헤더 및 행사 수
                    worksheet.set_row(curr_row, 35)
                    worksheet.merge_range(curr_row, 0, curr_row, 5, f"  🏢 {bu} (총 {len(b_df)}건)", bu_fmt)
                    curr_row += 1
                    
                    # 표 헤더
                    worksheet.write_row(curr_row, 0, ["장소", "시간", "행사명", "부서", "인원", "상태"], hdr_fmt)
                    curr_row += 1
                    
                    # 데이터 로우 (행 높이 35, 자동 줄바꿈 및 축소)
                    for _, r in b_df.sort_values('시간').iterrows():
                        worksheet.set_row(curr_row, 35)
                        worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], cell_fmt)
                        curr_row += 1
                    
                    # 표 사이 1줄 개행
                    curr_row += 1
        
        # 열 너비 설정 (장소25, 시간15, 행사명44, 부서25, 인원6, 상태6)
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:C', 44)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 6)
        worksheet.set_column('F:F', 6)
        
    return output.getvalue()

# 5. UI 메인
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 검색 필터")
    view_mode = st.radio("보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"])
    target_date = st.date_input("날짜 선택", value=now_today)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(target_date)

if not df.empty:
    with st.sidebar:
        shift_val = get_shift(target_date)
        st.download_button("📥 엑셀 출력 (인쇄용)", 
                           data=create_excel(df, sel_bu, target_date.strftime("%Y-%m-%d"), shift_val), 
                           file_name=f"대관현황_{target_date}.xlsx", use_container_width=True)

    st.markdown(f'<div class="date-bar">📅 {target_date.strftime("%Y-%m-%d")} | 근무조: {shift_val}</div>', unsafe_allow_html=True)
    
    for bu in sel_bu:
        b_df = df[df['건물명'].str.replace(" ", "") == bu.replace(" ", "")]
        if not b_df.empty:
            st.markdown(f'<div style="font-size:18px; font-weight:bold; color:#1E3A5F; margin:20px 0 10px 0; border-left:6px solid #1E3A5F; padding-left:12px;">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
            
            if view_mode == "가로 모드 (표)":
                html = '<table class="custom-table"><thead><tr><th style="width:20%">장소</th><th style="width:15%">시간</th><th style="width:34%">행사명</th><th style="width:19%">부서</th><th style="width:6%">인원</th><th style="width:6%">상태</th></tr></thead><tbody>'
                for _, r in b_df.sort_values('시간').iterrows():
                    html += f'<tr><td>{r["장소"]}</td><td>{r["시간"]}</td><td style="text-align:left;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["인원"]}</td><td>{r["상태"]}</td></tr>'
                st.markdown(html + '</tbody></table>', unsafe_allow_html=True)
            else:
                for _, r in b_df.sort_values('시간').iterrows():
                    s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                    st.markdown(f'''
                        <div class="mobile-card">
                            <div class="row-1">
                                <div>📍 {r["장소"]} <span style="color:#e74c3c; margin-left:8px;">🕒 {r["시간"]}</span></div>
                                <span class="status-badge {s_cls}">{r["상태"]}</span>
                            </div>
                            <div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                        </div>
                    ''', unsafe_allow_html=True)
else:
    st.info("조회된 대관 내역이 없습니다.")
