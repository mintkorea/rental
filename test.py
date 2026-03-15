import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정: 레이아웃 최적화 및 줌 기능 유지
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

# CSS: 페이지 좌우 여백 10 설정 및 타이틀 가독성
st.markdown("""
<style>
    /* 페이지 좌우 여백 10으로 설정 */
    .block-container { 
        padding-left: 10px !important; 
        padding-right: 10px !important; 
        padding-top: 2rem !important; 
    }
    /* PC 모드 표 내 줄바꿈 및 폰트 설정 (2행 노출 보장) */
    div[data-testid="stDataFrame"] td {
        white-space: normal !important;
        word-break: keep-all !important;
        line-height: 1.2 !important;
    }
</style>
""", unsafe_allow_html=True)

# 모바일 줌 기능 활성화 (수정 금지)
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">', unsafe_allow_html=True)

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
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 엑셀 생성: 시간 열 너비 확대 (12 -> 14) 및 행 높이 35 고정
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        date_hdr_fmt = workbook.add_format({'bold': True, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'bg_color': '#EBF1F8', 'align': 'left', 'valign': 'vcenter', 'border': 1})
        left_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'shrink': True})
        center_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'shrink': True})

        curr_row = 1
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    bu_clean = bu.replace(" ", "")
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu_clean)]
                    if not b_df.empty:
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            worksheet.set_row(curr_row, 35)
                            worksheet.write(curr_row, 0, r['장소'], left_fmt)
                            worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt)
                            worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['인원'], center_fmt)
                            worksheet.write(curr_row, 5, r['부스'], center_fmt)
                            worksheet.write(curr_row, 6, r['상태'], center_fmt)
                            curr_row += 1
                        curr_row += 1

        worksheet.set_column('A:A', 20)  # 장소
        worksheet.set_column('B:B', 14)  # 시간 (지시사항: 기존보다 너비 확대)
        worksheet.set_column('C:C', 35)  # 행사명
        worksheet.set_column('D:D', 18)  # 부서
        worksheet.set_column('E:G', 7)   
    return output.getvalue()

# 5. 메인 UI 및 화면 출력
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    # 모바일/PC 수동 전환 유지
    v_mode = st.radio("보기 모드", ["모바일", "PC"], horizontal=True)

df = get_data(s_date, e_date)

if not df.empty:
    with st.sidebar:
        excel_data = create_formatted_excel(df, sel_bu)
        st.download_button("📥 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    st.title("🏢 성의교정 실시간 대관 현황")

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div style="background-color:#343a40; color:white; padding:10px; border-radius:5px; margin-top:30px; text-align:center;">'
                    f'📅 {d_str} | 근무조: {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            bu_clean = bu.replace(" ", "")
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu_clean)]
            
            if not b_df.empty:
                st.markdown(f"#### 📍 {bu}")
                if v_mode == "PC":
                    # PC 모드: 줄바꿈 허용 및 장소/부서 너비 고정 (2행 노출)
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], 
                                 use_container_width=True, hide_index=True,
                                 column_config={
                                     "장소": st.column_config.TextColumn("장소", width="medium"),
                                     "시간": st.column_config.TextColumn("시간", width="medium"), # 시간 셸 확대 적용
                                     "부서": st.column_config.TextColumn("부서", width="medium")
                                 })
                else:
                    # 모바일 모드 디자인 유지 (로직 수정 없음)
                    for _, r in b_df.iterrows():
                        st.markdown(f"""
                        <div style="border-bottom:1px solid #eee; padding:10px 0;">
                            <div style="display:flex; justify-content:space-between; font-weight:700;">
                                <span style="color:#1e3a5f;">📍 {r['장소']}</span>
                                <span style="color:#e74c3c; font-size:12px;">🕒 {r['시간']}</span>
                                <span style="color:#27ae60; font-size:12px;">{r['상태']}</span>
                            </div>
                            <div style="font-size:12px; color:gray; margin-top:4px;">
                                {r['행사명']} ({r['부서']}, {r['인원']}명, 부스 {r['부스']}개)
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
else:
    st.info("조회된 날짜 범위 내에 대관 내역이 없습니다.")
