import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정 및 디자인 CSS (절대 깨지지 않는 고정 레이아웃)
st.set_page_config(page_title="성의교정 대관 현황 조회", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; max-width: 1100px; margin: 0 auto; }
    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px; margin-bottom: 20px; }
    .date-shift-bar { background-color: #444; color: white; padding: 12px; border-radius: 8px; text-align: center; margin: 15px 0; font-weight: bold; font-size: 18px; }
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:8px 0; margin-top:20px; }
    
    /* 표 고정 레이아웃 - 행사명이 장소명의 2배 */
    .fixed-table { width: 100%; table-layout: fixed; border-collapse: collapse; margin-top: 5px; background-color: white; }
    .fixed-table th, .fixed-table td { border: 1px solid #dee2e6; padding: 8px 4px; text-align: center; vertical-align: middle; height: 48px; }
    .fixed-table th { background-color: #f8f9fa; font-weight: bold; color: #333; font-size: 13px; }
    
    /* 고정 너비 비율: 장소(21%), 시간(14%), 행사명(42%), 부서(16%), 상태(7%) */
    .col-place { width: 21%; }
    .col-time { width: 14%; }
    .col-event { width: 42%; }
    .col-dept { width: 16%; }
    .col-status { width: 7%; }

    /* 2줄 제한 및 말줄임표 처리 */
    .cell-content { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; line-height: 1.3; font-size: 12.5px; word-break: break-all; }
    .font-small { font-size: 11px !important; }
    .status-y { color: #27ae60; font-weight: bold; }
    .status-n { color: #e67e22; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 가져오기 (항목 추가 전 원형 데이터 구조)
@st.cache_data(ttl=60)
def get_rental_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json().get('res', [])
        rows = []
        for item in data:
            rows.append({
                'bu': str(item.get('buNm', '')).strip(),
                'place': item.get('placeNm', '') or '-',
                'time': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                'event': item.get('eventNm', '') or '-',
                'dept': item.get('mgDeptNm', '') or '-',
                'status': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame()

# 3. 근무조 계산
def get_shift_info(d):
    base = date(2026, 3, 13)
    diff = (d - base).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 4. 사이드바 및 검색 설정
st.markdown('<div class="main-header">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 검색 설정")
    sel_date = st.date_input("조회 날짜", value=date.today())
    bu_list = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
    selected_bu = st.multiselect("건물 필터", bu_list, default=["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관"])

df_res = get_rental_data(sel_date)
st.markdown(f'<div class="date-shift-bar">📅 {sel_date} | {get_shift_info(sel_date)}</div>', unsafe_allow_html=True)

# 5. 결과 출력 (필터링 로직 복구)
for bu in selected_bu:
    # 0건 방지를 위해 공백을 제거하고 유연하게 비교
    if not df_res.empty:
        b_df = df_res[df_res['bu'].str.replace(" ", "") == bu.replace(" ", "")]
    else:
        b_df = pd.DataFrame()
        
    count = len(b_df)
    st.markdown(f'<div class="building-header"><div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div style="font-size:14px;">총 {count}건</div></div>', unsafe_allow_html=True)
    
    if count > 0:
        table_html = f"""
        <table class="fixed-table">
            <thead>
                <tr>
                    <th class="col-place">장소</th><th class="col-time">시간</th>
                    <th class="col-event">행사명</th><th class="col-dept">부서</th>
                    <th class="col-status">상태</th>
                </tr>
            </thead>
            <tbody>
        """
        for _, r in b_df.iterrows():
            # 장소/행사명 길이에 따라 폰트 축소 적용
            p_cls = "font-small" if len(r['place']) > 14 else ""
            e_cls = "font-small" if len(r['event']) > 26 else ""
            s_cls = "status-y" if r['status'] == '확정' else "status-n"
            
            table_html += f"""
                <tr>
                    <td class="{p_cls}"><div class="cell-content">{r['place']}</div></td>
                    <td><div class="cell-content">{r['time']}</div></td>
                    <td class="{e_cls}"><div class="cell-content">{r['event']}</div></td>
                    <td><div class="cell-content">{r['dept']}</div></td>
                    <td class="{s_cls}">{r['status']}</td>
                </tr>
            """
        table_html += "</tbody></table>"
        st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#999; padding:10px; font-size:13px;">└ 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
