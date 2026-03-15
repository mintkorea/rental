import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 현황 조회", layout="wide")

# 2. 고정 디자인 CSS
st.markdown("""
<style>
    .block-container { padding-top: 2rem; max-width: 1000px; margin: 0 auto; }
    .main-title { font-size: 22px; font-weight: bold; color: #1e3a5f; padding-bottom: 10px; border-bottom: 3px solid #1e3a5f; }
    .date-bar { background-color: #444; color: white; padding: 10px; border-radius: 5px; text-align: center; margin: 15px 0; font-weight: bold; }
    .bu-header { background-color: #f1f3f5; border-bottom: 2px solid #1e3a5f; padding: 8px 12px; margin-top: 20px; font-weight: bold; color: #1e3a5f; display: flex; justify-content: space-between; align-items: center; }
    
    /* 표 레이아웃 강제 고정 */
    .custom-table { width: 100%; table-layout: fixed; border-collapse: collapse; margin: 5px 0; background-color: white; border: 1px solid #dee2e6; }
    .custom-table th, .custom-table td { border: 1px solid #dee2e6; padding: 8px 4px; text-align: center; vertical-align: middle; height: 48px; word-break: break-all; }
    .custom-table th { background-color: #f8f9fa; font-size: 13px; color: #333; }
    
    /* 너비 비율 설정 */
    .w-place { width: 22%; } /* 장소명 기준 */
    .w-time { width: 15%; }
    .w-event { width: 40%; } /* 행사명 2배 */
    .w-dept { width: 16%; }
    .w-status { width: 7%; }
    
    /* 2줄 제한 및 폰트 조절 */
    .cell-txt { 
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; 
        overflow: hidden; text-overflow: ellipsis; line-height: 1.3; font-size: 12.5px; 
    }
    .f-small { font-size: 11px !important; }
    .status-ok { color: #28a745; font-weight: bold; }
    .status-wait { color: #fd7e14; font-weight: bold; }
    .no-data { color: #868e96; padding: 15px; font-size: 13px; font-style: italic; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 전처리 (KeyError 방지)
@st.cache_data(ttl=60)
def get_safe_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        raw_data = res.json().get('res', [])
        rows = []
        for item in raw_data:
            # 컬럼명이 'buNm'인지 확인하여 안전하게 매핑
            rows.append({
                'building': str(item.get('buNm', '')).strip(),
                'place': item.get('placeNm', '') or '-',
                'time': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                'event': item.get('eventNm', '') or '-',
                'dept': item.get('mgDeptNm', '') or '-',
                'status': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except:
        return pd.DataFrame(columns=['building', 'place', 'time', 'event', 'dept', 'status'])

# 4. 근무조 계산
def get_shift_name(d):
    base = date(2026, 3, 13)
    days = (d - base).days
    return f"{['A', 'B', 'C'][days % 3]}조"

# 5. 메인 로직
st.markdown('<div class="main-title">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 검색 설정")
    sel_date = st.date_input("날짜 선택", value=datetime.now(pytz.timezone('Asia/Seoul')).date())
    bu_list = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
    selected_bu = st.multiselect("건물 필터", bu_list, default=["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관"])

df = get_safe_data(sel_date)

# 상단 날짜바
st.markdown(f'<div class="date-bar">📅 {sel_date} | {get_shift_name(sel_date)}</div>', unsafe_allow_html=True)

# 건물별 표 출력
for bu in selected_bu:
    # 데이터 필터링 (KeyError 방지: 'building' 컬럼 사용)
    if not df.empty:
        filtered = df[df['building'].str.replace(" ", "") == bu.replace(" ", "")]
    else:
        filtered = pd.DataFrame()
        
    count = len(filtered)
    st.markdown(f'<div class="bu-header"><span>🏢 {bu}</span><span>총 {count}건</span></div>', unsafe_allow_html=True)
    
    if count > 0:
        # HTML 테이블 생성
        table_body = ""
        for _, r in filtered.iterrows():
            # 텍스트 길이에 따른 폰트 축소 적용
            p_style = "f-small" if len(r['place']) > 14 else ""
            e_style = "f-small" if len(r['event']) > 26 else ""
            s_class = "status-ok" if r['status'] == '확정' else "status-wait"
            
            table_body += f"""
            <tr>
                <td class="w-place"><div class="cell-txt {p_style}">{r['place']}</div></td>
                <td class="w-time"><div class="cell-txt">{r['time']}</div></td>
                <td class="w-event"><div class="cell-txt {e_style}">{r['event']}</div></td>
                <td class="w-dept"><div class="cell-txt">{r['dept']}</div></td>
                <td class="w-status"><span class="{s_class}">{r['status']}</span></td>
            </tr>
            """
        
        full_html = f"""
        <table class="custom-table">
            <thead>
                <tr>
                    <th class="w-place">장소</th><th class="w-time">시간</th>
                    <th class="w-event">행사명</th><th class="w-dept">부서</th>
                    <th class="w-status">상태</th>
                </tr>
            </thead>
            <tbody>
                {table_body}
            </tbody>
        </table>
        """
        # st.write 대신 st.markdown(..., unsafe_allow_html=True)를 확실히 사용
        st.markdown(full_html, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="no-data">└ {bu} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
