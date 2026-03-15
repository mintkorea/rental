import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 여백 최소화 CSS
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    .block-container { padding: 0.5rem 1rem !important; }
    header {visibility: hidden;}
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin: 0; padding: 5px 0; }
    .date-bar { background-color: #343a40; color: white; padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; margin-bottom: 8px; font-size: 14px; }
    .bu-header { font-size: 16px; font-weight: bold; color: #1E3A5F; margin: 12px 0 5px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; }
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 8px 12px; margin-bottom: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 12px; }
    .status-badge { padding: 1px 6px; border-radius: 4px; font-size: 10px; color: white; font-weight: bold; min-width: 38px; text-align: center; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    .row-2 { font-size: 12px; color: #555; border-top: 1px solid #f8f9fa; margin-top: 4px; padding-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    </style>
""", unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
WEEKDAYS = ["", "월", "화", "수", "목", "금", "토", "일"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 2. 엑셀 출력 함수 (사용자 제시 인쇄 규격 반영)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 스타일 설정
        hdr_fmt = workbook.add_format({'bold':True,'bg_color':'#333333','font_color':'white','align':'center','border':1})
        bu_fmt = workbook.add_format({'bold':True,'bg_color':'#EBF1F8','border':1})
        cell_fmt = workbook.add_format({'border':1,'align':'center','valign':'vcenter','text_wrap':True,'shrink':True})
        
        curr_row = 0
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.set_row(curr_row, 35)
            worksheet.merge_range(curr_row, 0, curr_row, 5, f"📅 {d_str} | {get_shift(d_obj)}", hdr_fmt)
            curr_row += 1
            
            for bu in selected_buildings:
                bu_clean = bu.replace(" ", "")
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu_clean)]
                if not b_df.empty:
                    worksheet.set_row(curr_row, 35)
                    worksheet.merge_range(curr_row, 0, curr_row, 5, f"  📍 {bu}", bu_fmt)
                    curr_row += 1
                    for _, r in b_df.iterrows():
                        worksheet.set_row(curr_row, 35)
                        worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], cell_fmt)
                        curr_row += 1
            curr_row += 1
    return output.getvalue()

# 3. 데이터 수집 및 엄격 필터링
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
            allowed_days = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            
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
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

# 필터링 결과 출력 로직 개선
if not df.empty:
    with st.sidebar:
        st.download_button("📥 엑셀 다운로드", data=create_formatted_excel(df, sel_bu), file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    # 날짜별 루프
    date_list = sorted(df['full_date'].unique()) if not df.empty else []
    
    # 만약 선택한 기간의 날짜가 데이터에 하나도 없다면 안내문 출력
    found_any_in_range = False
    
    curr_date = s_date
    while curr_date <= e_date:
        d_str = curr_date.strftime('%Y-%m-%d')
        day_df = df[df['full_date'] == d_str] if not df.empty else pd.DataFrame()
        
        # 해당 날짜에 선택한 건물의 데이터가 있는지 확인
        filtered_day_df = day_df[day_df['건물명'].str.replace(" ", "").isin([b.replace(" ", "") for b in sel_bu])] if not day_df.empty else pd.DataFrame()

        if not filtered_day_df.empty:
            found_any_in_range = True
            st.markdown(f'<div class="date-bar">📅 {d_str} ({WEEKDAYS[curr_date.isoweekday()]}요일) | {get_shift(curr_date)}</div>', unsafe_allow_html=True)
            
            for bu in sel_bu:
                bu_clean = bu.replace(" ", "")
                b_df = filtered_day_df[filtered_day_df['건물명'].str.replace(" ", "") == bu_clean]
                
                if not b_df.empty:
                    st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                    for _, r in b_df.sort_values('시간').iterrows():
                        s_cls = "status-y" if r['상태'] == '확정' else "status-n"
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="row-1">
                                    <span class="loc-text">📍 {r["장소"]}</span>
                                    <span class="time-text">🕒 {r["시간"]}</span>
                                    <span class="status-badge {s_cls}">{r["상태"]}</span>
                                </div>
                                <div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]} ({r["인원"]}명)</div>
                            </div>
                        ''', unsafe_allow_html=True)
                else:
                    # 건물별 결과 없음 안내 (선택사항: 너무 지저분하면 제거 가능)
                    st.info(f"ℹ️ {d_str} {bu} 대관 내역이 없습니다.")
        curr_date += timedelta(days=1)

    if not found_any_in_range:
        st.warning(f"⚠️ {s_date} ~ {e_date} 기간 내 선택하신 건물에 대한 검색 결과가 없습니다.")
else:
    st.warning(f"⚠️ {s_date} ~ {e_date} 기간에 조회된 대관 내역이 전혀 없습니다.")
