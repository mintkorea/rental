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
    /* 상단 여백 및 기본 폰트 */
    .block-container { padding-top: 5rem !important; max-width: 1000px !important; margin: 0 auto !important; }
    
    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px; }
    
    .date-shift-bar {
        background-color: #444; color: white; padding: 12px; border-radius: 8px;
        text-align: center; margin: 15px 0 10px 0; font-weight: bold; font-size: 18px !important;
    }
    
    /* 건물 헤더 스타일 */
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:6px 0; margin-top:12px; }
    .count-text { font-size: 14px; font-weight: bold; color: #333; }
    
    /* 카드 및 줄 간격 축소 */
    .mobile-card { padding: 8px 0; border-bottom: 1px solid #eee; width: 100%; }
    .card-first-line { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 2px; }
    .place-name { font-weight: bold; color: #333; font-size: 15px; flex: 1; word-break: break-all; }
    .time-status-area { display: flex; align-items: center; flex-shrink: 0; }
    .time-text { font-size: 12.5px; color: #e74c3c; font-weight: bold; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; margin-left:6px; }
    
    /* 두번째 줄 간격 축소 */
    .card-second-line { font-size: 12.5px; color: #666; margin-top: 2px; line-height: 1.3; }

    /* 내역 없음 메시지 스타일 (소제목 아래 고정) */
    .empty-building-msg { color: #999; padding: 10px 5px; font-size: 13.5px; font-style: normal; }
    
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
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 엑셀 생성 (기존 포맷 유지)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        hdr_fmt = workbook.add_format({'bold': 1, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': 1, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'indent': 1})
        cell_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'text_wrap': True, 'align': 'left', 'indent': 1})
        center_fmt = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})

        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 4, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 4, f"  📍 {bu} (총 {len(b_df)}건)", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['상태']], cell_fmt)
                            curr_row += 1
                        curr_row += 1
        worksheet.set_column('A:A', 25); worksheet.set_column('B:E', 20)
    return output.getvalue()

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
            # 1. 건물 헤더 무조건 표출 (데이터 유무 상관없음)
            b_df = df_res[(df_res['full_date'] == d_str) & (df_res['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            count = len(b_df)
            st.markdown(f'<div class="building-header"><div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {count}건</div></div>', unsafe_allow_html=True)
            
            # 2. 데이터 유무에 따른 분기 처리
            if count > 0:
                if view_mode == "가로 모드 (표)":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
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
                            </div>
                        """, unsafe_allow_html=True)
            else:
                # 3. 내역 없는 건물 메시지 표출
                st.markdown(f'<div class="empty-building-msg">└ {bu} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.markdown('<div style="text-align:center; padding:50px; color:#666; background:#f9f9f9; border-radius:10px; margin-top:20px;">🔍 선택하신 기간 및 건물에 대한 대관 내역이 전혀 없습니다.</div>', unsafe_allow_html=True)
