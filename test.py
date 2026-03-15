import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인 CSS
st.set_page_config(page_title="성희교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    /* 1. PC 와이드 화면 최적화 및 상단 여백 */
    .block-container { 
        padding-top: 5rem !important; 
        max-width: 95% !important; 
        margin: 0 auto !important; 
    }
    
    /* 2. 타이틀 상단 여백 및 잘림 방지 */
    .main-header { 
        font-size: 24px; font-weight: bold; color: #1e3a5f; 
        margin-bottom: 20px; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px;
        white-space: normal; overflow-wrap: break-word; line-height: 1.3;
    }

    /* 3. 표(DataFrame) 헤더 전체 중앙 정렬 */
    .stDataFrame th {
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
    }

    /* 4. 표 셸 내부 자동 줄바꿈(개행) 및 행 높이 조절 */
    .stDataFrame td {
        white-space: normal !important;
        word-break: keep-all !important;
        line-height: 1.5 !important;
        vertical-align: middle !important;
    }

    /* 날짜 및 근무조 바 */
    .date-shift-bar { background-color: #444; color: white; padding: 12px; border-radius: 8px; text-align: center; margin: 20px 0 10px 0; font-weight: bold; font-size: 17px !important; }
    
    /* 건물 헤더 */
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:5px 0; margin-top:10px; }
    .count-text { font-size: 14px; font-weight: bold; color: #333; }
    
    /* 세로 모드(카드) 스타일 */
    .mobile-card { padding: 8px 0; border-bottom: 1px solid #eee; width: 100%; }
    .card-first-line { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
    .place-name { font-weight: bold; color: #333; font-size: 15px; flex: 1; min-width: 0; }
    .time-status-area { display: flex; align-items: center; flex-shrink: 0; gap: 5px; }
    .time-text { font-size: 12px; color: #e74c3c; font-weight: bold; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; }
    .card-second-line { font-size: 12px; color: #666; margin-top: 2px; }
    
    div.stDownloadButton > button { width: 100%; background-color: #1e3a5f !important; color: white !important; border: none !important; padding: 10px !important; border-radius: 8px !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# [데이터 로직 생략 - 이전과 동일하게 유지]
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

# [엑셀 다운로드 로직 생략 - 이전과 동일]
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        worksheet.set_landscape()
        worksheet.center_horizontally()
        title_fmt = workbook.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter'})
        date_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 15, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'indent': 1})
        col_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#F2F2F2', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        common = {'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'shrink': True, 'font_size': 11}
        left_fmt = workbook.add_format({**common, 'align': 'left', 'indent': 1})
        center_fmt = workbook.add_format({**common, 'align': 'center'})
        worksheet.merge_range('A1:E1', "성희교정 대관 현황", title_fmt)
        worksheet.set_row(0, 40)
        curr_row = 2
        dates = sorted(df['full_date'].unique()) if not df.empty else [now_today.strftime('%Y-%m-%d')]
        for d_str in dates:
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 4, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))] if not df.empty else pd.DataFrame()
                    worksheet.set_row(curr_row, 30)
                    worksheet.merge_range(curr_row, 0, curr_row, 4, f"  📍 {bu} (총 {len(b_df)}건)", bu_fmt)
                    curr_row += 1
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 25)
                        for i, h in enumerate(['장소', '시간', '행사명', '부서명', '상태']): worksheet.write(curr_row, i, h, col_hdr_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write(curr_row, 0, r['장소'], left_fmt)
                            worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt)
                            worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['상태'], center_fmt)
                            curr_row += 1
                    else:
                        worksheet.set_row(curr_row, 30)
                        worksheet.merge_range(curr_row, 0, curr_row, 4, "대관 내역이 없습니다.", center_fmt)
                        curr_row += 1
                    curr_row += 1
        worksheet.set_column('A:A', 32); worksheet.set_column('B:B', 15); worksheet.set_column('C:C', 42); worksheet.set_column('D:D', 25); worksheet.set_column('E:E', 8)
    return output.getvalue()

# 5. UI 및 데이터 표출 로직
with st.sidebar:
    st.header("⚙️ 설정 및 도구")
    view_mode = st.radio("📱 보기 모드 설정", ["세로 모드 (카드)", "가로 모드 (표)"], index=0)
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    df_result = get_data(s_date, e_date)
    st.download_button(label="📥 엑셀 결과 다운로드", data=create_formatted_excel(df_result, sel_bu), file_name=f"성희교정 대관 현황({s_date}).xlsx", use_container_width=True)

st.markdown('<div class="main-header">📋 성희교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_result.empty:
    # [수정] 표의 열별 정렬 및 너비 구성
    col_config = {
        "장소": st.column_config.TextColumn("장소", width="medium"),
        "시간": st.column_config.TextColumn("시간", width="small"), # CSS를 통한 중앙 정렬 대상
        "행사명": st.column_config.TextColumn("행사명", width="large"),
        "부서": st.column_config.TextColumn("부서", width="medium"),
        "상태": st.column_config.TextColumn("상태", width="small")  # CSS를 통한 중앙 정렬 대상
    }
    
    for d_str in sorted(df_result['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df_result[(df_result['full_date'] == d_str) & (df_result['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            st.markdown(f'<div class="building-header"><div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
            if not b_df.empty:
                if view_mode == "가로 모드 (표)":
                    # 데이터프레임 스타일 적용 (중앙 정렬 포함)
                    styled_df = b_df[['장소', '시간', '행사명', '부서', '상태']].style.set_properties(
                        subset=['시간', '상태'], 
                        **{'text-align': 'center'}
                    )
                    st.dataframe(styled_df, use_container_width=True, hide_index=True, column_config=col_config)
                else:
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'<div class="mobile-card"><div class="card-first-line"><div class="place-name">📍 {r["장소"]}</div><div class="time-status-area"><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge" style="background-color:{bg};">{r["상태"]}</span></div></div><div class="card-second-line">📄 {r["행사명"]} | {r["부서"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="color:#999; padding:10px; font-size:13px; text-align:center; border:1px solid #eee; margin-top:5px; border-radius:5px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회된 날짜에 대관 내역이 없습니다.")
