import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 초기 설정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 근무조 로직 및 요일 변환
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

# 3. 데이터 수집 로직 (소스 1의 엄격한 필터링 이식)
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
            
            # allowDay 파싱 (소스 1 방식)
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    # [핵심] 요일 엄격 검사 (allowDay가 있으면 해당 요일만, 없으면 매일)
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '요일': ['','월','화','수','목','금','토','일'][curr.isoweekday()],
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '부스': str(item.get('boothCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt, # 당일/기간 구분용
                            'allowDay': allow_day_raw
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 엑셀 생성 (기존 서식 유지)
def create_formatted_excel(df, start_date, end_date, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        worksheet.set_landscape()
        worksheet.fit_to_pages(1, 0)
        
        # 서식 생략 (기존과 동일)
        date_hdr_fmt = workbook.add_format({'bold': True, 'font_size': 13, 'bg_color': '#333333', 'font_color': 'white', 'align': 'center', 'valign': 'vcenter', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#EBF1F8', 'border': 1})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 11})
        cnt_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 11})

        curr_row = 1
        dates = sorted(df['full_date'].unique()) if not df.empty else []
        for i, d_str in enumerate(dates):
            if i > 0: worksheet.set_h_pagebreaks([curr_row])
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    # 건물명 검색 시 공백 제거 매칭 (소스 1 방식)
                    b_df = df[(df['full_date'] == d_str) & 
                              (df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False))]
                    worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                    curr_row += 1
                    if not b_df.empty:
                        for _, r in b_df.iterrows():
                            worksheet.write(curr_row, 0, r['장소'], cell_fmt)
                            worksheet.write(curr_row, 1, r['시간'], cnt_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], cell_fmt)
                            worksheet.write(curr_row, 3, r['부서'], cell_fmt)
                            worksheet.write(curr_row, 4, r['인원'], cnt_fmt)
                            worksheet.write(curr_row, 5, r['부스'], cnt_fmt)
                            worksheet.write(curr_row, 6, r['상태'], cnt_fmt)
                            curr_row += 1
                    curr_row += 1
        worksheet.set_column('A:A', 20); worksheet.set_column('C:C', 40); worksheet.set_column('D:D', 20)
    return output.getvalue()

# 5. 메인 UI
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

if not df.empty:
    with st.sidebar:
        excel_data = create_formatted_excel(df, s_date, e_date, sel_bu)
        st.download_button("📥 엑셀 다운로드", data=excel_data, file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div style="background-color:#f1f3f5; padding:10px; border-radius:5px; margin-top:30px;">'
                    f'<h3>📅 {d_str} | 근무조: {get_shift(d_obj)}</h3></div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            # 소스 1 스타일의 유연한 건물명 매칭
            b_df = df[(df['full_date'] == d_str) & 
                      (df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False))]
            st.markdown(f"#### 📍 {bu}")
            
            if not b_df.empty:
                # 당일 대관과 기간 대관 분리 노출
                t_df = b_df[b_df['is_period'] == False]
                p_df = b_df[b_df['is_period'] == True]
                
                if not t_df.empty:
                    st.write("**📌 당일 대관**")
                    st.dataframe(t_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True)
                
                if not p_df.empty:
                    st.write("**🗓️ 기간 대관**")
                    st.dataframe(p_df[['장소', '시간', '행사명', '부서', '인원', '부스', '상태']], use_container_width=True, hide_index=True)
            else:
                st.info("대관 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
