import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인 CSS
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 4rem !important; max-width: 1000px !important; margin: 0 auto !important; }
    .main-header { font-size: 26px; font-weight: bold; color: #1e3a5f; margin-bottom: 25px; display: flex; align-items: center; gap: 10px; border-bottom: 3px solid #1e3a5f; padding-bottom: 12px; }
    .date-shift-bar { background-color: #444; color: white; padding: 15px; border-radius: 8px; text-align: center; margin: 25px 0 15px 0; font-weight: bold; font-size: 19px !important; }
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:8px 0; margin-top:15px; }
    .count-text { font-size: 15px; font-weight: bold; color: #333; }
    
    /* 모바일 카드 스타일 */
    .mobile-card { padding: 15px 0; border-bottom: 1px solid #eee; width: 100%; }
    .card-first-line { display: flex; justify-content: space-between; align-items: flex-start; gap: 20px; }
    .place-name { font-weight: bold; color: #333; font-size: 16px; flex: 1; min-width: 0; overflow-wrap: break-word; line-height: 1.4; }
    .time-status-area { display: flex; align-items: center; flex-shrink: 0; white-space: nowrap; margin-top: 2px; }
    .time-text { font-size: 13px; color: #e74c3c; font-weight: bold; }
    .status-badge { padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; color: white; margin-left:8px; }
    .card-second-line { font-size: 13px; color: #666; margin-top: 8px; overflow-wrap: break-word; line-height: 1.4; }
    
    div.stDownloadButton > button { width: 100%; background-color: #1e3a5f !important; color: white !important; border: none !important; padding: 12px !important; border-radius: 8px !important; font-weight: bold !important; }
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
                    if not allowed_days or str(curr.isoweekday()) in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        worksheet.set_landscape()
        m = 0.39
        worksheet.set_margins(left=m, right=m, top=m, bottom=m)
        
        # 포맷 정의
        date_hdr_fmt = workbook.add_format({'bold': 1, 'font_size': 12, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': 1, 'font_size': 11, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'indent': 1})
        col_hdr_fmt = workbook.add_format({'bold': 1, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        empty_fmt = workbook.add_format({'font_size': 10, 'font_color': '#999999', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        
        common = {'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'shrink': True, 'font_size': 10}
        left_fmt = workbook.add_format({**common, 'align': 'left', 'indent': 1})
        center_fmt = workbook.add_format({**common, 'align': 'center'})

        curr_row = 1
        dates = sorted(df['full_date'].unique()) if not df.empty else [now_today.strftime('%Y-%m-%d')]
        for d_str in dates:
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 4, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))] if not df.empty else pd.DataFrame()
                    count = len(b_df)
                    
                    # 건물명 헤더
                    worksheet.set_row(curr_row, 35)
                    worksheet.merge_range(curr_row, 0, curr_row, 4, f"  📍 {bu} (총 {count}건)", bu_fmt)
                    curr_row += 1
                    
                    if not b_df.empty:
                        # 데이터가 있을 때만 셸 헤더 표시 (중앙 정렬)
                        worksheet.set_row(curr_row, 25)
                        headers = ['장소', '시간', '행사명', '부서', '상태']
                        for i, h in enumerate(headers):
                            worksheet.write(curr_row, i, h, col_hdr_fmt)
                        curr_row += 1
                        
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write(curr_row, 0, r['장소'], left_fmt)
                            worksheet.write(curr_row, 1, r['시간'], center_fmt) # 시간 중앙
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt)
                            worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['상태'], center_fmt) # 상태 중앙
                            curr_row += 1
                    else:
                        # 데이터 없을 때 문구 (중앙 정렬)
                        worksheet.set_row(curr_row, 30)
                        worksheet.merge_range(curr_row, 0, curr_row, 4, "대관 내역이 없습니다.", empty_fmt)
                        curr_row += 1
                    curr_row += 1

        worksheet.set_column('A:A', 25); worksheet.set_column('B:B', 14); worksheet.set_column('C:C', 35); worksheet.set_column('D:D', 20); worksheet.set_column('E:E', 8)
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
    st.download_button(label="📥 엑셀 결과 다운로드", data=create_formatted_excel(df_result, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

st.markdown('<div class="main-header">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_result.empty:
    # 웹 표 설정 (헤더 중앙 정렬 포함)
    col_config = {
        "장소": st.column_config.TextColumn("장소", width=180),
        "시간": st.column_config.TextColumn("시간", width=110, help="중앙 정렬"),
        "행사명": st.column_config.TextColumn("행사명", width=300),
        "부서": st.column_config.TextColumn("부서", width=144),
        "상태": st.column_config.TextColumn("상태", width=80, help="중앙 정렬")
    }
    
    for d_str in sorted(df_result['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df_result[(df_result['full_date'] == d_str) & (df_result['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            st.markdown(f'<div class="building-header"><div style="font-size:17px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
            if not b_df.empty:
                if view_mode == "가로 모드 (표)":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True, column_config=col_config)
                else:
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'<div class="mobile-card"><div class="card-first-line"><div class="place-name">📍 {r["장소"]}</div><div class="time-status-area"><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge" style="background-color:{bg};">{r["상태"]}</span></div></div><div class="card-second-line">📄 {r["행사명"]} | {r["부서"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="color:#999; padding:15px; font-size:14px; border:1px solid #eee; margin-top:5px; border-radius:5px; text-align:center;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회된 날짜에 대관 내역이 없습니다.")
