import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 고정 디자인 CSS (헤드 영역)
st.markdown("""
<style>
    .block-container { padding-top: 3rem; max-width: 1000px; margin: 0 auto; }
    .main-title { font-size: 24px; font-weight: bold; color: #1e3a5f; padding-bottom: 10px; border-bottom: 3px solid #1e3a5f; }
    .date-bar { background-color: #444; color: white; padding: 10px; border-radius: 5px; text-align: center; margin: 15px 0; font-weight: bold; }
    .bu-header { background-color: white; border-bottom: 2px solid #1e3a5f; padding: 5px 0; margin-top: 15px; font-weight: bold; color: #1e3a5f; display: flex; justify-content: space-between; }
    
    /* 표 고정 레이아웃 */
    table.custom-table { width: 100%; table-layout: fixed; border-collapse: collapse; margin: 5px 0 15px 0; background-color: white; }
    table.custom-table th, table.custom-table td { border: 1px solid #ddd; padding: 6px 3px; text-align: center; vertical-align: middle; height: 45px; overflow: hidden; }
    table.custom-table th { background-color: #f8f9fa; font-size: 13px; }
    
    /* 너비 고정 (장소:20%, 시간:15%, 행사:40%, 부서:18%, 상태:7%) */
    .w-place { width: 20%; } .w-time { width: 15%; } .w-event { width: 40%; } .w-dept { width: 18%; } .w-status { width: 7%; }
    
    /* 2줄 제한 및 자동 폰트 축소 */
    .cell-txt { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; text-overflow: ellipsis; line-height: 1.2; word-break: break-all; font-size: 12.5px; }
    .small-txt { font-size: 11px !important; }
    .status-ok { color: #27ae60; font-weight: bold; }
    .status-wait { color: #e67e22; font-weight: bold; }
    .no-data { color: #999; padding: 10px; font-size: 13px; border-bottom: 1px solid #eee; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 조회 함수
@st.cache_data(ttl=60)
def fetch_rental_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json().get('res', [])
        result = []
        for item in data:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    result.append({
                        'date': curr.strftime('%Y-%m-%d'),
                        'bu': str(item.get('buNm', '')).strip(),
                        'place': item.get('placeNm', '') or '-',
                        'time': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        'event': item.get('eventNm', '') or '-',
                        'dept': item.get('mgDeptNm', '') or '-',
                        'status': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(result)
    except: return pd.DataFrame()

# 4. 근무조 계산
def get_shift(d):
    diff = (d - date(2026, 3, 13)).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# 5. 메인 화면 구성
st.markdown('<div class="main-title">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ 설정")
    target_date = st.date_input("조회 날짜", value=datetime.now(pytz.timezone('Asia/Seoul')).date())
    sel_bu = st.multiselect("건물 선택", ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"], default=["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"])

df = fetch_rental_data(target_date, target_date)

# 6. HTML 렌더링 루프 (철저 검증 구역)
if not df.empty or target_date:
    # 근무조 정보 표시
    st.markdown(f'<div class="date-bar">📅 {target_date} | {get_shift(target_date)}</div>', unsafe_allow_html=True)
    
    for bu_name in sel_bu:
        # 건물 헤더 출력
        filtered = df[df['bu'].str.replace(" ", "") == bu_name.replace(" ", "")]
        count = len(filtered)
        st.markdown(f'<div class="bu-header"><span>🏢 {bu_name}</span><span>총 {count}건</span></div>', unsafe_allow_html=True)
        
        if count > 0:
            # HTML 표 작성 (문자열 결합 방식 최적화)
            rows_html = ""
            for _, r in filtered.iterrows():
                # 텍스트 길이에 따른 클래스 부여
                p_cls = "small-txt" if len(r['place']) > 14 else ""
                e_cls = "small-txt" if len(r['event']) > 25 else ""
                s_cls = "status-ok" if r['status'] == '확정' else "status-wait"
                
                rows_html += f"""
                <tr>
                    <td class="w-place"><div class="cell-txt {p_cls}">{r['place']}</div></td>
                    <td class="w-time"><div class="cell-txt">{r['time']}</div></td>
                    <td class="w-event"><div class="cell-txt {e_cls}">{r['event']}</div></td>
                    <td class="w-dept"><div class="cell-txt">{r['dept']}</div></td>
                    <td class="w-status"><span class="{s_cls}">{r['status']}</span></td>
                </tr>
                """
            
            # 최종 표 결합 출력
            full_table = f"""
            <table class="custom-table">
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
            """
            st.markdown(full_table, unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="no-data">└ {bu_name} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
