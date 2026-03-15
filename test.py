import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 웹 화면 CSS (세로 2줄 / 가로 표 셸 너비 고정)
st.markdown("""
    <style>
    .block-container { padding: 1rem !important; max-width: 100% !important; }
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; border: 1px solid #dee2e6; }
    .custom-table th { background-color: #f8f9fa; color: #1E3A5F; padding: 10px; border: 1px solid #dee2e6; font-size: 13px; font-weight: 800; }
    .custom-table td { padding: 10px; border: 1px solid #dee2e6; text-align: center; font-size: 13px; vertical-align: middle; word-break: break-all; }
    
    /* 웹 가로 모드 비율 (요청하신 엑셀 비율 기반 최적화) */
    .col-1 { width: 20%; } .col-2 { width: 15%; } .col-3 { width: 35%; } .col-4 { width: 20%; } .col-5 { width: 5%; } .col-6 { width: 5%; }

    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 8px; padding: 12px; margin-bottom: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
    .row-1 { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .info-main { font-size: 14px; font-weight: 800; color: #1E3A5F; display: flex; gap: 8px; }
    .info-time { color: #e74c3c; font-weight: 700; }
    .status-badge { padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: bold; color: white; }
    .status-y { background-color: #2ecc71; } .status-n { background-color: #95a5a6; }
    .row-2 { font-size: 12px; color: #555; border-top: 1px solid #f8f9fa; padding-top: 6px; }
    </style>
""", unsafe_allow_html=True)

# 3. 데이터 로직 (생략)
def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(d):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": d.isoformat(), "end": d.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allowed_days = [str(x.strip()) for x in str(item.get('allowDay', '')).split(",") if x.strip().isdigit()]
            if s_dt <= d <= e_dt:
                if not allowed_days or str(d.isoweekday()) in allowed_days:
                    rows.append({
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 엑셀 출력 (요청하신 열 너비 및 자동 줄바꿈/축소 적용)
def create_excel(df, selected_buildings, d_str, shift):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        hdr_fmt = workbook.add_format({'bold':True,'font_size':12,'bg_color':'#333333','font_color':'white','align':'center','valign':'vcenter','border':1})
        bu_fmt = workbook.add_format({'bold':True,'font_size':11,'bg_color':'#EBF1F8','align':'left','valign':'vcenter','border':1})
        # [핵심] 텍스트가 넘치면 줄바꿈(text_wrap)하고, 그래도 넘치면 폰트 축소(shrink)
        cell_fmt = workbook.add_format({'border':1,'align':'center','valign':'vcenter','text_wrap':True,'shrink':True}) 
        
        curr_row = 0
        worksheet.set_row(curr_row, 35)
        worksheet.merge_range(curr_row, 0, curr_row, 5, f"📅 {d_str} | 근무조: {shift}", hdr_fmt)
        curr_row += 1
        
        for bu in BUILDING_ORDER:
            if bu in selected_buildings:
                b_df = df[df['건물명'].str.replace(" ","") == bu.replace(" ","")]
                if not b_df.empty:
                    worksheet.set_row(curr_row,
