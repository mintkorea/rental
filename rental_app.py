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

# 2. 데이터 로드 및 "강력한 정제" (HTML 깨짐 방지 핵심)
@st.cache_data(ttl=60)
def get_safe_data(s_date, e_date):
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
                    # 모든 텍스트에서 따옴표, 줄바꿈 등을 안전한 공백으로 대체
                    def safe_str(text):
                        if not text: return ""
                        return str(text).replace("'", " ").replace('"', " ").replace("\n", " ").replace("\r", " ")

                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': safe_str(item.get('buNm', '')).strip(),
                        '장소': safe_str(item.get('placeNm', '')),
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': safe_str(item.get('eventNm', '')),
                        '인원': safe_str(item.get('peopleCount', '')),
                        '부서': safe_str(item.get('mgDeptNm', '')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 필터 설정
st.sidebar.title("📅 대관 조회 필터")
s_day = st.sidebar.date_input("시작일", now_today)
e_day = st.sidebar.date_input("종료일", s_day)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_safe_data(s_day, e_day)

# 4. 독립된 뷰어를 위한 HTML 생성 (브라우저 직결)
# viewport 설정을 통해 모바일 줌(Pinch Zoom)을 강제 활성화합니다.
html_output = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        body {{ font-family: -apple-system, sans-serif; padding: 15px; background: white; color: #333; line-height: 1.4; }}
        .title {{ font-size: 20px; font-weight: bold; text-align: center; margin-bottom: 20px; color: #1e3a5f; }}
        .date-box {{ font-size: 17px; font-weight: bold; background: #f0f2f6; padding: 10px; border-left: 6px solid #2e5077; margin-top: 25px; }}
        .bu-tag {{ font-size: 15px; font-weight: bold; margin: 15px 0 6px 0; color: #444; }}
        .table-scroll {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 850px; table-layout: fixed; margin-bottom: 10px; }}
        th, td {{ border: 1px solid #ccc; padding: 10px 4px; text-align: center; font-size: 13px; word-break: break-all; }}
        th {{ background: #eee; font-weight: bold; }}
        .w-place {{ width: 120px; }} .w-time {{ width: 85px; }} .w-event {{ width: auto; }}
        .w-count {{ width: 45px; }} .w-dept {{ width: 110px; }} .w-stat {{ width: 50px; }}
        .left {{ text-align: left !important; padding-left: 8px !important; }}
    </style>
</head>
<body>
    <div class="title">🏫 성의교정 대관 현황</div>
"""

if not df.empty:
    filtered = df[df['건물명'].isin(selected_bu)]
    for date in sorted(filtered['full_date'].unique()):
        day_df = filtered[filtered_df['full_date'] == date]
        html_output += f'<div class="date-box">📅 {date} ({day_df.iloc[0]["요일"]})</div>'
        
        for bu in BUILDING_ORDER:
            if bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    html_output += f'<div class="bu-tag">🏢 {bu}</div>'
                    html_output += """<div class="table-scroll"><table><thead><tr>
                                    <th class="w-place">장소</th><th class="w-time">시간</th><th class="w-event">행사명</th>
                                    <th class="w-count">인원</th><th class="w-dept">부서</th><th class="w-stat">상태</th>
                                    </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        html_output += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    html_output += "</tbody></table></div>"
else:
    html_output += "<p style='text-align:center;'>데이터가 없습니다.</p>"

html_output += "</body></html>"

# 5. iframe 컴포넌트 출력 (높이를 매우 크게 잡아 스크롤 대신 줌을 유도)
# scrolling=False로 설정하여 외부 스크롤을 방지하고 내부 줌을 극대화합니다.
components.html(html_output, height=3000, scrolling=False)
