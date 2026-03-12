import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 건물 순서
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 로드 함수 (필터링 전 원본 데이터만 가져오기)
@st.cache_data(ttl=60)
def get_raw_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', ''), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', ''), 
                        '인원': item.get('peopleCount', ''),
                        '부서': item.get('mgDeptNm', ''),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 사이드바 UI
st.sidebar.title("📅 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("🏢 건물 선택 (필터)", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

# 4. 데이터 필터링 (고장난 부분 수정)
raw_df = get_raw_data(start_selected, end_selected)

if not raw_df.empty:
    # 선택한 건물만 필터링
    filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)].copy()
    filtered_df['건물명'] = pd.Categorical(filtered_df['건물명'], categories=BUILDING_ORDER, ordered=True)
    filtered_df = filtered_df.sort_values(by=['full_date', '건물명', '시간'])
else:
    filtered_df = pd.DataFrame()

# 5. HTML 생성 (줌 기능을 위해 iframe 내부로 삽입)
html_code = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <style>
        body { font-family: 'Malgun Gothic', sans-serif; padding: 10px; }
        .date-header { font-size: 18px; font-weight: bold; color: #1E3A5F; padding: 8px; background: #f0f2f6; border-left: 5px solid #2E5077; margin-top: 25px; }
        .bu-header { font-size: 15px; font-weight: bold; margin: 15px 0 5px 0; color: #333; }
        .table-wrapper { width: 100%; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; min-width: 800px; table-layout: fixed; }
        th, td { border: 1px solid #ccc; padding: 8px 4px; text-align: center; font-size: 13px; }
        th { background: #eee; font-weight: bold; }
        .w-place { width: 120px; } .w-time { width: 85px; } .w-event { width: auto; }
        .w-count { width: 45px; } .w-dept { width: 110px; } .w-stat { width: 50px; }
        .text-left { text-align: left !important; padding-left: 8px !important; }
    </style>
</head>
<body>
"""

if not filtered_df.empty:
    for date in sorted(filtered_df['full_date'].unique()):
        day_df = filtered_df[filtered_df['full_date'] == date]
        html_code += f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>'
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                html_code += f'<div class="bu-header">🏢 {bu}</div>'
                html_code += """<div class="table-wrapper"><table><thead><tr>
                                <th class="w-place">장소</th><th class="w-time">시간</th><th class="w-event">행사명</th>
                                <th class="w-count">인원</th><th class="w-dept">부서</th><th class="w-stat">상태</th>
                                </tr></thead><tbody>"""
                for _, r in bu_df.iterrows():
                    html_code += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='text-left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                html_code += "</tbody></table></div>"
else:
    html_code += "<p style='text-align:center; padding-top:20px;'>조회된 데이터가 없습니다.</p>"

html_code += "</body></html>"

# 6. 화면 출력 (무조건 줌 가능하게 컴포넌트 사용)
# 데이터 양에 따라 높이가 모자라지 않게 2000px로 넉넉히 잡았습니다.
components.html(html_code, height=2000, scrolling=True)
