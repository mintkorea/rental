import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정 및 디자인 (절대 깨지지 않는 고정 레이아웃)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 1000px; margin: 0 auto; }
    .main-title { font-size: 22px; font-weight: bold; color: #1e3a5f; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px; }
    .date-bar { background-color: #444; color: white; padding: 10px; border-radius: 5px; text-align: center; margin: 15px 0; font-weight: bold; }
    .bu-header { background-color: #f8f9fa; border-bottom: 2px solid #1e3a5f; padding: 10px; margin-top: 20px; font-weight: bold; display: flex; justify-content: space-between; }
    
    /* 표 레이아웃 절대 고정 */
    table.fixed-table { width: 100%; table-layout: fixed; border-collapse: collapse; margin-top: 5px; background-color: white; }
    table.fixed-table th, table.fixed-table td { border: 1px solid #dee2e6; padding: 8px 4px; text-align: center; vertical-align: middle; height: 50px; }
    table.fixed-table th { background-color: #eee; font-size: 13px; color: #333; }
    
    /* 요청하신 너비 비율: 장소(20%), 시간(15%), 행사명(40%), 부서(18%), 상태(7%) */
    .w-place { width: 20%; } .w-time { width: 15%; } .w-event { width: 40%; } .w-dept { width: 18%; } .w-status { width: 7%; }
    
    /* 2줄 자동개행 및 말줄임표 */
    .cell-txt { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; line-height: 1.3; font-size: 12.5px; word-break: break-all; }
    .f-small { font-size: 11px !important; }
    .st-ok { color: #28a745; font-weight: bold; }
    .st-wait { color: #fd7e14; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# 2. 데이터 수집 (안전한 필드 매핑)
@st.cache_data(ttl=60)
def fetch_data(target_date):
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

# 3. 사이드바 및 근무조
def get_shift(d):
    return f"{['A', 'B', 'C'][(d - date(2026, 3, 13)).days % 3]}조"

st.markdown('<div class="main-title">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 검색")
    sel_date = st.date_input("날짜", value=date.today())
    bu_list = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]
    selected_bu = st.multiselect("건물 필터", bu_list, default=bu_list)

df = fetch_data(sel_date)
st.markdown(f'<div class="date-bar">📅 {sel_date} | {get_shift(sel_date)}</div>', unsafe_allow_html=True)

# 4. 결과 출력 (필터링 로직 유연화)
for bu in selected_bu:
    # 공백 무시 비교로 필터링 실패 방지
    if not df.empty:
        b_df = df[df['bu'].str.replace(" ","") == bu.replace(" ","")]
    else:
        b_df = pd.DataFrame()
        
    count = len(b_df)
    st.markdown(f'<div class="bu-header"><span>🏢 {bu}</span><span>총 {count}건</span></div>', unsafe_allow_html=True)
    
    if count > 0:
        rows_html = ""
        for _, r in b_df.iterrows():
            # 텍스트 길이에 따른 폰트 조절
            p_style = "f-small" if len(r['place']) > 14 else ""
            e_style = "f-small" if len(r['event']) > 25 else ""
            s_class = "st-ok" if r['status'] == '확정' else "st-wait"
            
            rows_html += f"""
            <tr>
                <td class="w-place"><div class="cell-txt {p_style}">{r['place']}</div></td>
                <td class="w-time"><div class="cell-txt">{r['time']}</div></td>
                <td class="w-event"><div class="cell-txt {e_style}">{r['event']}</div></td>
                <td class="w-dept"><div class="cell-txt">{r['dept']}</div></td>
                <td class="w-status"><span class="{s_class}">{r['status']}</span></td>
            </tr>
            """
        
        # HTML 표 출력 (가장 안정적인 형태)
        st.markdown(f"""
        <table class="fixed-table">
            <thead>
                <tr>
                    <th class="w-place">장소</th><th class="w-time">시간</th>
                    <th class="w-event">행사명</th><th class="w-dept">부서</th>
                    <th class="w-status">상태</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        """, unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#999; padding:10px;">└ 내역 없음</div>', unsafe_allow_html=True)
