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
    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; border-bottom: 3px solid #1e3a5f; padding-bottom: 12px; }
    .date-shift-bar {
        background-color: #444; color: white; padding: 12px; border-radius: 8px;
        text-align: center; margin: 20px 0 10px 0; font-weight: bold; font-size: 17px !important;
    }
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:8px 0; margin-top:10px; }
    .count-text { font-size: 14px; font-weight: bold; color: #333; }
    .mobile-card { padding: 12px 0; border-bottom: 1px solid #eee; width: 100%; }
    .card-first-line { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
    .place-name { font-weight: bold; color: #333; font-size: 15px; flex: 1; word-break: break-all; }
    .time-status-area { text-align: right; flex-shrink: 0; }
    .time-text { font-size: 13px; color: #e74c3c; font-weight: bold; display: block; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; display: inline-block; margin-top: 4px; }
    .card-second-line { font-size: 13px; color: #555; margin-top: 6px; font-weight: 500; }
    .card-third-line { font-size: 12px; color: #0066cc; margin-top: 4px; display: flex; flex-wrap: wrap; gap: 5px; }
    div.stDownloadButton > button {
        width: 100%; background-color: #1e3a5f !important; color: white !important;
        border: none !important; padding: 10px !important; border-radius: 6px !important; font-weight: bold !important;
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
            
            # 요일 필터링 로직
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
                        # [검증 및 보정] 데이터 필드 재매핑
                        req_name = item.get('reqNm') or item.get('reqUserNm') or '-'
                        phone_num = item.get('phone') or item.get('reqPhone') or '-'
                        # 인원수는 숫자가 0이거나 없을 경우를 명확히 구분
                        u_cnt = item.get('userCnt')
                        user_count = f"{int(u_cnt)}명" if u_cnt and str(u_cnt).isdigit() and int(u_cnt) > 0 else "-"

                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            '신청자': req_name,
                            '연락처': phone_num,
                            '인원': user_count
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        hdr_fmt = workbook.add_format({'bold': 1, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': 1, 'bg_color': '#EBF1F8', 'border': 1, 'valign': 'vcenter', 'indent': 1})
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'align': 'left', 'indent': 1})
        center_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})

        curr_row = 0
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 7, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", hdr_fmt)
            curr_row += 1
            
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 7, f"📍 {bu} (총 {len(b_df)}건)", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['신청자'], r['연락처'], r['인원'], r['상태']], cell_fmt)
                            curr_row += 1
                        curr_row += 1
        worksheet.set_column('A:H', 18)
    return output.getvalue()

# --- UI ---
with st.sidebar:
    st.header("⚙️ 설정")
    view_mode = st.radio("📱 보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"])
    st.divider()
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    df_res = get_data(s_date, e_date)
    if not df_res.empty:
        fname = f"성의교정 대관 현황 조회 보고({s_date}).xlsx"
        st.download_button("📥 엑셀 결과 다운로드", data=create_formatted_excel(df_res, sel_bu), file_name=fname, use_container_width=True)

st.markdown('<div class="main-header">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_res.empty:
    for d_str in sorted(df_res['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df_res[(df_res['full_date'] == d_str) & (df_res['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                st.markdown(f'<div class="building-header"><div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
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
                                <div class="card-second-line">📄 {r['행사명']}</div>
                                <div class="card-third-line">
                                    <span>🏢 {r['부서']}</span> | 
                                    <span>👤 {r['신청자']}</span> | 
                                    <span>📞 {r['연락처']}</span> | 
                                    <span>👥 {r['인원']}</span>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
