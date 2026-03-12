import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import streamlit.components.v1 as components

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 2. 데이터 로직 (검증된 로직 유지)
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

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
st.sidebar.title("조회 설정")
s_date = st.sidebar.date_input("시작일", now_today)
e_date = st.sidebar.date_input("종료일", s_date + timedelta(days=7))
target_bu = st.sidebar.multiselect("건물 필터", BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(s_date, e_date)

# 4. HTML 생성 (줌이 가능한 독립된 구조)
html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <style>
        body { font-family: sans-serif; padding: 10px; }
        .date-section { background: #f0f2f6; padding: 10px; font-weight: bold; border-left: 5px solid #2e5077; margin-top: 20px; font-size: 1.2rem; }
        .bu-title { margin-top: 15px; font-weight: bold; color: #333; }
        table { width: 100%; min-width: 800px; border-collapse: collapse; margin-bottom: 10px; table-layout: fixed; }
        th, td { border: 1px solid #ccc; padding: 8px 4px; text-align: center; font-size: 14px; }
        th { background: #eee; }
        .col-place { width: 120px; } .col-time { width: 90px; } .col-event { width: auto; } .col-dept { width: 110px; } .col-stat { width: 50px; }
        .text-left { text-align: left; }
    </style>
</head>
<body>
    <h2 style="text-align:center;">🏫 성의교정 대관 현황</h2>
"""

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        html_content += f'<div class="date-section">📅 {date} ({day_df.iloc[0]["요일"]})</div>'
        
        for bu in target_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                html_content += f'<div class="bu-title">🏢 {bu}</div>'
                html_content += '<table><thead><tr><th class="col-place">장소</th><th class="col-time">시간</th><th class="col-event">행사명</th><th class="col-dept">부서</th><th class="col-stat">상태</th></tr></thead><tbody>'
                for _, r in bu_df.iterrows():
                    html_content += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='text-left'>{r['행사명']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                html_content += "</tbody></table>"
else:
    html_content += "<p>조회된 데이터가 없습니다.</p>"

html_content += "</body></html>"

# 5. 컴포넌트로 HTML 출력 (이 부분이 줌 해결의 핵심입니다)
# height를 충분히 주어 스크롤이 내부에서 발생하게 합니다.
components.html(html_content, height=2000, scrolling=True)
