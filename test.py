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
    .block-container { padding-top: 1rem !important; max-width: 900px !important; margin: 0 auto !important; }
    
    /* 상단 타이틀 디자인 */
    .main-header { font-size: 22px; font-weight: bold; color: #333; margin-bottom: 5px; display: flex; align-items: center; gap: 8px; }
    
    /* 엑셀 다운로드 버튼 스타일 */
    div.stDownloadButton > button {
        width: 100%; background-color: white !important; color: #333 !important;
        border: 1px solid #ddd !important; padding: 10px !important; border-radius: 8px !important; font-weight: bold !important;
        margin-bottom: 15px;
    }

    /* 보기 방식 선택 라디오 버튼 영역 */
    div[data-testid="stRadio"] > label { font-weight: bold !important; color: #1e3a5f !important; }

    /* 날짜/근무조 헤더 */
    .date-shift-bar {
        background-color: #555; color: white; padding: 8px; border-radius: 6px;
        text-align: center; margin: 20px 0 10px 0; font-weight: bold; font-size: 14px;
    }

    /* 건물 헤더 디자인 */
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:8px 0; margin-top:15px; }
    .count-text { font-size: 14px; font-weight: bold; color: #333; }

    /* 카드 디자인 (세로 모드용) */
    .mobile-card { padding: 15px 0; border-bottom: 1px solid #eee; width: 100%; }
    .card-first-line { display: flex; justify-content: space-between; align-items: center; }
    .place-name { font-weight: bold; color: #333; font-size: 15px; }
    .time-text { font-size: 12px; color: #e74c3c; font-weight: bold; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; margin-left:8px; }
    .card-second-line { font-size: 12px; color: #888; margin-top: 6px; }

    /* 화면 표 디자인: 높이 제한 해제 및 여백 */
    [data-testid="stDataFrame"] td { padding: 8px 10px !important; height: auto !important; }
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
                            '인원': str(item.get('peopleCount', '0')),
                            '부스': str(item.get('boothCount', '0')),
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
        # 엑셀 편집용지 여백 10mm (0.39인치) 설정
        m = 0.39
        worksheet.set_margins(left=m, right=m, top=m, bottom=m)

        date_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1, 'indent': 1})
        left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'shrink': True, 'indent': 1})
        center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'shrink': True})

        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write(curr_row, 0, r['장소'], left_fmt); worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt); worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['인원'], center_fmt); worksheet.write(curr_row, 5, r['부스'], center_fmt)
                            worksheet.write(curr_row, 6, r['상태'], center_fmt); curr_row += 1
                        curr_row += 1
        # 시간 열 너비 +2 (14) 반영
        worksheet.set_column('A:A', 20); worksheet.set_column('B:B', 14)
        worksheet.set_column('C:C', 35); worksheet.set_column('D:D', 18); worksheet.set_column('E:G', 8)
    return output.getvalue()

# 5. 메인 화면 구성
st.markdown('<div class="main-header">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

df = get_data(now_today, now_today + timedelta(days=7)) # 초기 데이터 로드 (범위 설정 가능)

# 화면 상단 엑셀 다운로드 및 보기 모드 선택 [집중 반영]
col1, col2 = st.columns([1, 1])
with col1:
    view_mode = st.radio("📱 보기 형식 선택", ["세로 모드 (카드)", "가로 모드 (표)"], horizontal=True)
with col2:
    if not df.empty:
        st.download_button(label="📊 엑셀 다운로드", data=create_formatted_excel(df, BUILDING_ORDER), file_name=f"현황.xlsx", use_container_width=True)

with st.sidebar:
    st.header("🔍 상세 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(s_date, e_date)

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            st.markdown(f'<div class="building-header"><div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {len(b_df)}건</div></div>', unsafe_allow_html=True)
            
            if not b_df.empty:
                if view_mode == "가로 모드 (표)":
                    # 가로 모드: 표 형식 (높이 제한 없음)
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True)
                else:
                    # 세로 모드: 카드 형식
                    for _, r in b_df.iterrows():
                        bg_color = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f"""
                            <div class="mobile-card">
                                <div class="card-first-line">
                                    <div class="place-name">📍 {r['장소']}</div>
                                    <div>
                                        <span class="time-text">🕒 {r['시간']}</span>
                                        <span class="status-badge" style="background-color:{bg_color};">{r['상태']}</span>
                                    </div>
                                </div>
                                <div class="card-second-line">📄 {r['행사명']} | {r['부서']}</div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown(f'<div style="color:#888; padding:15px; font-size:13px;">{bu} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
