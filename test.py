import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인 CSS (기존 디자인 유지)
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; max-width: 1000px !important; margin: 0 auto !important; }
    .main-header { font-size: 26px; font-weight: bold; color: #1e3a5f; margin-bottom: 25px; display: flex; align-items: center; gap: 10px; border-bottom: 3px solid #1e3a5f; padding-bottom: 12px; }
    .date-shift-bar {
        background-color: #444; color: white; padding: 15px; border-radius: 8px;
        text-align: center; margin: 25px 0 15px 0; font-weight: bold; font-size: 19px !important;
    }
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:8px 0; margin-top:15px; }
    .count-text { font-size: 15px; font-weight: bold; color: #333; }
    .mobile-card { padding: 15px 0; border-bottom: 1px solid #eee; width: 100%; }
    .card-first-line { display: flex; justify-content: space-between; align-items: center; gap: 15px; }
    .place-name { font-weight: bold; color: #333; font-size: 16px; flex: 1; min-width: 0; word-break: break-all; }
    .time-status-area { display: flex; align-items: center; flex-shrink: 0; text-align: right; }
    .time-text { font-size: 13px; color: #e74c3c; font-weight: bold; white-space: nowrap; }
    .status-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; margin-left:8px; white-space: nowrap; }
    .card-second-line { font-size: 13px; color: #666; margin-top: 8px; }
    .card-third-line { font-size: 12px; color: #007bff; margin-top: 5px; font-weight: 500; }
    div.stDownloadButton > button {
        width: 100%; background-color: #1e3a5f !important; color: white !important;
        border: none !important; padding: 12px !important; border-radius: 8px !important; font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

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
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            '신청자': item.get('reqNm') or '미기재',
                            '연락처': item.get('phone') or '미기재',
                            '인원': f"{item.get('userCnt')}명" if item.get('userCnt') else "인원미정"
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 엑셀 생성 함수 (지시사항 반영)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 포맷 설정
        hdr_fmt = workbook.add_format({'bold': 1, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': 1, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'indent': 1})
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'align': 'left', 'indent': 1})
        center_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})

        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            # 날짜 헤더
            worksheet.set_row(curr_row, 35) # 높이 35 고정
            worksheet.merge_range(curr_row, 0, curr_row, 7, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", hdr_fmt)
            curr_row += 1
            
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        # 건물 헤더 (수량 포함)
                        worksheet.set_row(curr_row, 35) # 높이 35 고정
                        worksheet.merge_range(curr_row, 0, curr_row, 7, f"  📍 {bu} (총 {len(b_df)}건)", bu_fmt)
                        curr_row += 1
                        
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35) # 높이 35 고정
                            worksheet.write(curr_row, 0, r['장소'], cell_fmt)
                            worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], cell_fmt)
                            worksheet.write(curr_row, 3, r['부서'], cell_fmt)
                            worksheet.write(curr_row, 4, r['신청자'], cell_fmt)
                            worksheet.write(curr_row, 5, r['연락처'], cell_fmt)
                            worksheet.write(curr_row, 6, r['인원'], center_fmt)
                            worksheet.write(curr_row, 7, r['상태'], center_fmt)
                            curr_row += 1
                        curr_row += 1 # 건물간 간격

        # 컬럼 너비 설정
        worksheet.set_column('A:A', 22); worksheet.set_column('B:B', 15); worksheet.set_column('C:C', 35)
        worksheet.set_column('D:G', 18); worksheet.set_column('H:H', 10)
        
    return output.getvalue()

# UI 구성
with st.sidebar:
    st.header("⚙️ 설정 및 도구")
    view_mode = st.radio("📱 보기 모드 설정", ["세로 모드 (카드)", "가로 모드 (표)"], index=0)
    st.divider()
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    df_result = get_data(s_date, e_date)
    
    if not df_result.empty:
        # 파일명 형식 반영: 성의교정 대관 현황 조회 보고(날짜).xlsx
        report_filename = f"성의교정 대관 현황 조회 보고({s_date}).xlsx"
        st.download_button(label="📥 엑셀 결과 다운로드", data=create_formatted_excel(df_result, sel_bu), file_name=report_filename, use_container_width=True)

st.markdown('<div class="main-header">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

# 메인 화면 로직 (기존 카드/표 표출 유지)
if not df_result.empty:
    for d_str in sorted(df_result['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df_result[(df_result['full_date'] == d_str) & (df_result['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            st.markdown(f'<div class="building-header"><div style="font-size:17px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
            if not b_df.empty:
                if view_mode == "가로 모드 (표)":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '신청자', '연락처', '인원', '상태']], use_container_width=True, hide_index=True)
                else:
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f"""
                            <div class="mobile-card">
                                <div class="card-first-line">
                                    <div class="place-name">📍 {r['장소']}</div>
                                    <div class="time-status-area">
                                        <span class="time-text">🕒 {r['시간']}</span>
                                        <span class="status-badge" style="background-color:{bg};">{r['상태']}</span>
                                    </div>
                                </div>
                                <div class="card-second-line">📄 {r['행사명']} | {r['부서']}</div>
                                <div class="card-third-line">👤 {r['신청자']} ({r['연락처']}) | 👥 {r['인원']}</div>
                            </div>
                        """, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
