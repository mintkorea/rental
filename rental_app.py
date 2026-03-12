import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import streamlit.components.v1 as components

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 로드 및 "완전 정제" (HTML 깨짐 방지 핵심)
@st.cache_data(ttl=60)
def get_clean_data(s_date, e_date):
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
                    # 모든 텍스트에서 줄바꿈, 따옴표 등을 제거하여 HTML 파괴 방지
                    def clean(text):
                        if not text: return ""
                        return str(text).replace("\n", " ").replace("\r", "").replace("'", " ").replace('"', " ")

                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': clean(item.get('buNm', '')),
                        '장소': clean(item.get('placeNm', '')),
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': clean(item.get('eventNm', '')),
                        '인원': clean(item.get('peopleCount', '')),
                        '부서': clean(item.get('mgDeptNm', '')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 필터 설정
st.sidebar.title("📅 대관 조회 필터")
s_selected = st.sidebar.date_input("시작일", now_today)
e_selected = st.sidebar.date_input("종료일", s_selected)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

df = get_clean_data(s_selected, e_selected)

# 4. HTML 표준 문서 생성 (브라우저 직결 방식)
# viewport 설정을 통해 모바일 줌을 물리적으로 강제합니다.
html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes">
    <style>
        body {{ font-family: sans-serif; padding: 10px; background: #fff; }}
        .date-section {{ font-size: 18px; font-weight: bold; background: #f0f2f6; padding: 8px; border-left: 5px solid #2e5077; margin-top: 25px; }}
        .bu-title {{ font-size: 15px; font-weight: bold; margin: 15px 0 5px 0; color: #333; }}
        .table-wrap {{ width: 100%; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 800px; table-layout: fixed; }}
        th, td {{ border: 1px solid #ccc; padding: 8px 4px; text-align: center; font-size: 13px; word-break: break-all; }}
        th {{ background: #eee; }}
        .w-place {{ width: 120px; }} .w-time {{ width: 85px; }} .w-event {{ width: auto; }}
        .w-count {{ width: 45px; }} .w-dept {{ width: 110px; }} .w-stat {{ width: 50px; }}
        .left {{ text-align: left !important; padding-left: 8px !important; }}
    </style>
</head>
<body>
    <h2 style="text-align:center;">🏫 성의교정 대관 현황</h2>
"""

if not df.empty:
    filtered = df[df['건물명'].isin(selected_bu)]
    for date in sorted(filtered['full_date'].unique()):
        day_df = filtered[filtered['full_date'] == date]
        html_body += f'<div class="date-section">📅 {date} ({day_df.iloc[0]["요일"]})</div>'
        
        for bu in BUILDING_ORDER:
            if bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    html_body += f'<div class="bu-title">🏢 {bu}</div>'
                    html_body += """<div class="table-wrap"><table><thead><tr>
                                    <th class="w-place">장소</th><th class="w-time">시간</th><th class="w-event">행사명</th>
                                    <th class="w-count">인원</th><th class="w-dept">부서</th><th class="w-stat">상태</th>
                                    </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        html_body += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    html_body += "</tbody></table></div>"
else:
    html_body += "<p style='text-align:center;'>내역이 없습니다.</p>"

html_body += "</body></html>"

# 5. 컴포넌트 출력 (높이를 넉넉히 잡아 잘림 방지)
components.html(html_body, height=2000, scrolling=True)
