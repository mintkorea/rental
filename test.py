import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황", layout="wide")

# 2. 디자인 CSS (HTML 렌더링 안정화)
st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 1000px; margin: 0 auto; }
    .main-title { font-size: 22px; font-weight: bold; color: #1e3a5f; padding-bottom: 10px; border-bottom: 3px solid #1e3a5f; }
    .date-bar { background-color: #444; color: white; padding: 10px; border-radius: 5px; text-align: center; margin: 15px 0; font-weight: bold; }
    .bu-header { background-color: #f1f3f5; border-bottom: 2px solid #1e3a5f; padding: 8px 12px; margin-top: 20px; font-weight: bold; color: #1e3a5f; display: flex; justify-content: space-between; }
    
    /* 표 레이아웃 강제 고정 */
    table.fixed-table { width: 100%; table-layout: fixed; border-collapse: collapse; margin-top: 5px; background-color: white; }
    table.fixed-table th, table.fixed-table td { border: 1px solid #dee2e6; padding: 8px 4px; text-align: center; vertical-align: middle; height: 48px; }
    table.fixed-table th { background-color: #f8f9fa; font-size: 13px; color: #333; }
    
    /* 너비 비율: 장소(22), 시간(15), 행사(40), 부서(16), 상태(7) */
    .w-place { width: 22%; } .w-time { width: 15%; } .w-event { width: 40%; } .w-dept { width: 16%; } .w-status { width: 7%; }
    
    /* 내용 제어: 2줄 자동개행 */
    .cell-txt { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; line-height: 1.3; font-size: 12.5px; word-break: break-all; }
    .f-small { font-size: 11px !important; }
    .status-ok { color: #28a745; font-weight: bold; }
    .status-wait { color: #fd7e14; font-weight: bold; }
    .no-data { color: #868e96; padding: 15px; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 (필드명 매핑 철저 검증)
@st.cache_data(ttl=60)
def load_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        data_list = res.json().get('res', [])
        rows = []
        for item in data_list:
            # API에서 내려오는 실제 키값을 building_name으로 통일
            rows.append({
                'building_name': str(item.get('buNm', '')).strip(),
                'place_name': item.get('placeNm', '') or '-',
                'time_info': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                'event_name': item.get('eventNm', '') or '-',
                'dept_name': item.get('mgDeptNm', '') or '-',
                'status_txt': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except Exception as e:
        return pd.DataFrame()

# 4. 근무조 계산
def get_shift_name(d):
    diff = (d - date(2026, 3, 13)).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 5. UI 및 로직 실행
st.markdown('<div class="main-title">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 검색")
    sel_date = st.date_input("날짜", value=datetime.now(pytz.timezone('Asia/Seoul')).date())
    bu_options = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
    selected_bu = st.multiselect("건물 필터", bu_options, default=["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관"])

# 데이터 가져오기
df = load_data(sel_date)

# 상단 정보바
st.markdown(f'<div class="date-bar">📅 {sel_date} | {get_shift_name(sel_date)}</div>', unsafe_allow_html=True)

# 건물별 결과 출력
for bu in selected_bu:
    # 필터링 로직 강화: 포함 여부로 체크 (공백 등 이슈 해결)
    if not df.empty:
        # 건물명이 포함되어 있는지 확인
        b_df = df[df['building_name'].apply(lambda x: bu.replace(" ","") in x.replace(" ",""))]
    else:
        b_df = pd.DataFrame()
        
    count = len(b_df)
    st.markdown(f'<div class="bu-header"><span>🏢 {bu}</span><span>총 {count}건</span></div>', unsafe_allow_html=True)
    
    if count > 0:
        # 테이블 바디 구성
        rows_html = ""
        for _, r in b_df.iterrows():
            p_cls = "f-small" if len(r['place_name']) > 14 else ""
            e_cls = "f-small" if len(r['event_name']) > 26 else ""
            s_cls = "status-ok" if r['status_txt'] == '확정' else "status-wait"
            
            rows_html += f"""
            <tr>
                <td class="w-place"><div class="cell-txt {p_cls}">{r['place_name']}</div></td>
                <td class="w-time"><div class="cell-txt">{r['time_info']}</div></td>
                <td class="w-event"><div class="cell-txt {e_cls}">{r['event_name']}</div></td>
                <td class="w-dept"><div class="cell-txt">{r['dept_name']}</div></td>
                <td class="w-status"><span class="{s_cls}">{r['status_txt']}</span></td>
            </tr>
            """
        
        # 최종 HTML 출력
        st.markdown(f"""
        <table class="fixed-table">
            <thead>
                <tr>
                    <th class="w-place">장소</th><th class="w-time">시간</th>
                    <th class="w-event">행사명</th><th class="w-dept">부서</th>
                    <th class="w-status">상태</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="no-data">└ {bu} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
