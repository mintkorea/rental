import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 (사용자 확대 허용)
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")
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
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('현황')
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#333333', 'font_color': 'white', 'border': 1, 'align': 'center'})
        bu_fmt = workbook.add_format({'bold': True, 'bg_color': '#f1f3f5', 'border': 1})
        # [장소 길이 대응] text_wrap이 적용된 셀 포맷
        cell_fmt = workbook.add_format({'border': 1, 'text_wrap': True, 'valign': 'vcenter'})
        
        curr_row = 0
        for d_str in sorted(df['full_date'].unique()):
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str}", header_fmt)
            curr_row += 1
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
                    if not b_df.empty:
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"📍 {bu} ({len(b_df)}건)", bu_fmt)
                        curr_row += 1
                        for _, r in b_df.iterrows():
                            # 장소(0번 컬럼) 등 긴 텍스트 입력
                            worksheet.write_row(curr_row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], '-', '-', r['상태']], cell_fmt)
                            curr_row += 1
                        curr_row += 1
        # 컬럼 너비 기본 설정
        worksheet.set_column('A:A', 25) # 장소 컬럼을 조금 넓게 설정
    return output.getvalue()

# --- 화면 출력 ---
with st.sidebar:
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    v_mode = st.radio("모드", ["모바일", "PC"], horizontal=True)

df = get_data(s_date, e_date)

if not df.empty:
    st.download_button("📥 엑셀 다운로드", data=create_formatted_excel(df, sel_bu), file_name=f"현황_{s_date}.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        st.markdown(f"### 📅 {d_str} | {get_shift(datetime.strptime(d_str, '%Y-%m-%d').date())}")
        for bu in sel_bu:
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                st.markdown(f"#### 📍 {bu} ({len(b_df)}건)")
                for _, r in b_df.iterrows():
                    if v_mode == "모바일":
                        # [장소 길이 대응] 모바일에서 장소명을 굵고 크게 표시
                        st.markdown(f"""
                        <div style="border-bottom:1px solid #eee; padding:5px 0;">
                            <div style="font-size:16px; font-weight:bold; color:#2c3e50;">{r['장소']}</div>
                            <div style="font-size:13px; color:#e74c3c;">{r['시간']} | {r['상태']}</div>
                            <div style="font-size:12px; color:#666;">{r['행사명']} ({r['부서']})</div>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.write(f"- **{r['장소']}** | {r['시간']} | {r['행사명']}")
else:
    st.info("내역 없음")
