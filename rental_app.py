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

# 2. 데이터 로드 및 정제
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
                    def safe_t(t):
                        return str(t).replace("'", " ").replace('"', " ").replace("\n", " ").strip() if t else ""
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': safe_t(item.get('buNm', '')),
                        '장소': safe_t(item.get('placeNm', '')),
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': safe_t(item.get('eventNm', '')),
                        '인원': safe_t(item.get('peopleCount', '')),
                        '부서': safe_t(item.get('mgDeptNm', '')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 사이드바 필터
st.sidebar.title("📅 대관 조회 필터")
s_day = st.sidebar.date_input("시작일", now_today)
e_day = st.sidebar.date_input("종료일", s_day)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

raw_df = get_clean_data(s_day, e_day)

# 4. HTML 생성 (줌 기능을 위해 viewport 설정을 가장 강력하게 적용)
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        body {{ font-family: sans-serif; padding: 10px; background: white; -webkit-text-size-adjust: none; }}
        .date-title {{ font-size: 18px; font-weight: bold; background: #f0f2f6; padding: 10px; border-left: 6px solid #2e5077; margin-top: 25px; }}
        .bu-title {{ font-size: 15px; font-weight: bold; margin: 15px 0 5px 0; color: #333; }}
        .table-wrap {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 900px; table-layout: fixed; }}
        th, td {{ border: 1px solid #ccc; padding: 10px 5px; text-align: center; font-size: 14px; word-break: break-all; }}
        th {{ background: #eee; font-weight: bold; }}
        .col-p {{ width: 130px; }} .col-t {{ width: 90px; }} .col-e {{ width: auto; }}
        .col-c {{ width: 45px; }} .col-d {{ width: 110px; }} .col-s {{ width: 55px; }}
        .left {{ text-align: left !important; padding-left: 8px !important; }}
    </style>
</head>
<body>
    <h2 style="text-align:center; color:#1e3a5f;">🏫 성의교정 대관 현황</h2>
"""

if not raw_df.empty:
    filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)]
    # 날짜 정렬 후 출력
    for d in sorted(filtered_df['full_date'].unique()):
        day_df = filtered_df[filtered_df['full_date'] == d]
        html_code += f'<div class="date-title">📅 {d} ({day_df.iloc[0]["요일"]})</div>'
        for bu in BUILDING_ORDER:
            if bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    html_code += f'<div class="bu-title">🏢 {bu}</div>'
                    html_code += """<div class="table-wrap"><table><thead><tr>
                        <th class="col-p">장소</th><th class="col-t">시간</th><th class="col-e">행사명</th>
                        <th class="col-c">인원</th><th class="col-d">부서</th><th class="col-s">상태</th>
                        </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        html_code += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    html_code += "</tbody></table></div>"
else:
    html_code += "<p style='text-align:center; padding-top:20px;'>조회된 데이터가 없습니다.</p>"

html_code += "</body></html>"

# 5. 출력 (iframe 높이를 데이터 양에 맞춰 유연하게 조절하거나 아주 크게 설정)
components.html(html_code, height=4000, scrolling=True)
