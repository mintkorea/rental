import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, date, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 사이드바 및 날짜 설정
st.sidebar.header("🔍 설정")
start_selected = st.sidebar.date_input("시작일", value=date.today())
end_selected = st.sidebar.date_input("종료일", value=date.today())
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 타이틀 생성
title_date = start_selected.strftime('%Y-%m-%d') if start_selected == end_selected else f"{start_selected.strftime('%Y-%m-%d')} ~ {end_selected.strftime('%Y-%m-%d')}"
st.markdown(f"""
    <div style="padding-top: 10px; margin-bottom: 20px;">
        <h2 style="color: #1E3A5F; font-size: 26px; font-weight: bold;">🏫 성의교정 대관 현황 ({title_date})</h2>
    </div>
""", unsafe_allow_html=True)

# 3. 데이터 추출 로직
@st.cache_data(ttl=300)
def get_processed_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.strftime('%Y-%m-%d'), "end": e_date.strftime('%Y-%m-%d')}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        raw_list = res.json().get('res', [])
        expanded_rows = []
        for item in raw_list:
            item_start = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            item_end = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            curr_dt = item_start
            while curr_dt <= item_end:
                if s_date <= curr_dt <= e_date:
                    target_weekday = str(curr_dt.weekday() + 1)
                    if (item['startDt'] == item['endDt']) or (target_weekday in allow_days):
                        expanded_rows.append({
                            '날짜': curr_dt.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '강의실': item.get('placeNm', ''),
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''),
                            '관리부서': item.get('mgDeptNm', ''),
                            '상태': '예약확정' if item.get('status') == 'Y' else '신청대기',
                            'sort_time': item.get('startTime', '')
                        })
                curr_dt += timedelta(days=1)
        return pd.DataFrame(expanded_rows)
    except: return pd.DataFrame()

df_all = get_processed_data(start_selected, end_selected)

# 4. 결과 렌더링 함수 (HTML Table 직접 생성)
def render_building_table(bu_name, data):
    if data.empty:
        return f"<p style='color:#888; font-style:italic;'>대관 내역이 없습니다.</p>"
    
    # 헤더 중앙 정렬 및 디자인 CSS 포함
    html_code = f"""
    <style>
        .custom-table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; font-family: sans-serif; }}
        .custom-table th {{ background-color: #333; color: white; text-align: center; padding: 12px 5px; font-size: 14px; border: 1px solid #444; }}
        .custom-table td {{ border: 1px solid #dee2e6; padding: 10px 8px; font-size: 13.5px; vertical-align: middle; }}
        @media (max-width: 600px) {{
            .custom-table th, .custom-table td {{ font-size: 11px; padding: 6px 3px; }}
        }}
    </style>
    <table class="custom-table">
        <thead>
            <tr>
                <th style="width:90px;">날짜</th>
                <th style="width:18%;">강의실</th>
                <th style="width:110px;">시간</th>
                <th>행사명</th>
                <th style="width:18%;">관리부서</th>
                <th style="width:70px;">상태</th>
            </tr>
        </thead>
        <tbody>
    """
    for _, row in data.iterrows():
        html_code += f"""
            <tr>
                <td style="text-align:center;">{row['날짜']}</td>
                <td>{row['강의실']}</td>
                <td style="text-align:center;">{row['시간']}</td>
                <td>{row['행사명']}</td>
                <td>{row['관리부서']}</td>
                <td style="text-align:center;">{row['상태']}</td>
            </tr>
        """
    html_code += "</tbody></table>"
    return html_code

# 5. 화면 표시
export_list = []
for bu in selected_bu:
    st.markdown(f"#### 🏢 {bu}")
    target_bu_clean = bu.replace(" ", "")
    
    if not df_all.empty:
        bu_df = df_all[df_all['건물명'].str.replace(" ", "").str.contains(target_bu_clean, na=False)].copy()
        if not bu_df.empty:
            bu_df = bu_df.sort_values(by=['날짜', 'sort_time'])
            # 핵심: components.html을 사용하여 강제 렌더링
            table_html = render_building_table(bu, bu_df)
            components.html(table_html, height=len(bu_df) * 45 + 60, scrolling=False)
            export_list.append(bu_df)
        else:
            st.write("대관 내역이 없습니다.")
    else:
        st.write("대관 내역이 없습니다.")

# 6. 엑셀 다운로드
if export_list:
    df_export = pd.concat(export_list)
    df_export['건물명'] = pd.Categorical(df_export['건물명'], categories=BUILDING_ORDER, ordered=True)
    df_export = df_export.sort_values(by=['건물명', '날짜', 'sort_time'])
    
    st.sidebar.markdown("---")
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export[['날짜', '건물명', '강의실', '시간', '행사명', '관리부서', '상태']].to_excel(writer, index=False)
    st.sidebar.download_button("📥 검색 결과 엑셀 저장", output.getvalue(), f"대관현황_{date.today()}.xlsx")
