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

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. 데이터 로드 로직 (검증된 로직 유지)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
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
        df = pd.DataFrame(rows)
        if not df.empty:
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 3. 사이드바 설정
st.sidebar.title("📅 대관 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

# 4. 줌이 가능한 독립된 HTML 생성
# viewport 설정을 통해 브라우저의 줌 기능을 강제로 깨웁니다.
html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <style>
        body { font-family: 'Malgun Gothic', sans-serif; padding: 10px; background-color: white; }
        .date-header { font-size: 18px; font-weight: bold; color: #1E3A5F; padding: 10px 0; margin-top: 25px; border-bottom: 2px solid #eee; }
        .building-header { font-size: 15px; font-weight: bold; margin-top: 15px; margin-bottom: 5px; border-left: 5px solid #2E5077; padding-left: 10px; }
        .table-wrapper { width: 100%; overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; min-width: 800px; table-layout: fixed; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 10px 5px; font-size: 13px; text-align: center; vertical-align: middle; word-break: break-all; }
        th { background-color: #f8f9fa; font-weight: bold; }
        /* 열 너비 고정: 시간 열을 좁게 */
        .w-place { width: 120px; } .w-time { width: 85px; } .w-event { width: auto; } 
        .w-count { width: 45px; } .w-dept { width: 110px; } .w-stat { width: 50px; }
        .text-left { text-align: left !important; padding-left: 8px !important; }
    </style>
</head>
<body>
    <h2 style="text-align:center;">🏫 성의교정 대관 현황</h2>
"""

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        html_template += f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>'
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                html_template += f'<div class="building-header">🏢 {bu}</div>'
                html_template += """
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th class="w-place">장소</th><th class="w-time">시간</th><th class="w-event">행사명</th>
                                <th class="w-count">인원</th><th class="w-dept">부서</th><th class="w-stat">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, r in bu_df.iterrows():
                    html_template += f"""
                        <tr>
                            <td>{r['장소']}</td><td>{r['시간']}</td><td class="text-left">{r['행사명']}</td>
                            <td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td>
                        </tr>
                    """
                html_template += "</tbody></table></div>"
else:
    html_template += "<p style='text-align:center;'>조회된 내역이 없습니다.</p>"

html_template += "</body></html>"

# 5. 컴포넌트를 통해 HTML 출력 (이것이 줌 해결의 핵심)
# height는 데이터 양에 따라 넉넉하게 잡거나 자동 조절되도록 합니다.
components.html(html_template, height=1500, scrolling=True)
