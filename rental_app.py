import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
import streamlit.components.v1 as components

# 1. 페이지 설정 (최상단)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 데이터 로드 및 "강력한 정제" (HTML 파손 방지)
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
                    # 모든 텍스트 데이터에서 HTML을 깨뜨릴 수 있는 요소를 공백으로 치환
                    def clean(text):
                        if not text: return ""
                        return str(text).replace("'", " ").replace('"', " ").replace("<", " ").replace(">", " ").replace("\n", " ").strip()
                    
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

# 3. 사이드바 필터 (오타 수정됨)
st.sidebar.title("📅 대관 조회 필터")
s_day = st.sidebar.date_input("시작일", now_today)
e_day = st.sidebar.date_input("종료일", s_day)
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

raw_df = get_safe_data(s_day, e_day)

# 4. 물리적 줌(확대) 강제화를 위한 독립 HTML 생성
# viewport 설정을 maximum-scale=5.0으로 높여 줌을 강제합니다.
html_output = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        body {{ font-family: -apple-system, sans-serif; padding: 10px; background: white; }}
        .date-title {{ font-size: 19px; font-weight: bold; background: #f0f2f6; padding: 10px; border-left: 6px solid #2e5077; margin-top: 30px; }}
        .bu-title {{ font-size: 16px; font-weight: bold; margin: 15px 0 5px 0; color: #333; }}
        .table-wrap {{ width: 100%; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 900px; table-layout: fixed; }}
        th, td {{ border: 1px solid #ccc !important; padding: 12px 5px; text-align: center; font-size: 14px; word-break: break-all; }}
        th {{ background: #eee; font-weight: bold; }}
        /* 열 너비 고정: 시간 열을 좁게 유지 */
        .w-p {{ width: 130px; }} .w-t {{ width: 90px; }} .w-e {{ width: auto; }}
        .w-c {{ width: 50px; }} .w-d {{ width: 120px; }} .w-s {{ width: 60px; }}
        .left {{ text-align: left !important; padding-left: 10px !important; }}
    </style>
</head>
<body>
    <h2 style="text-align:center; color:#1e3a5f;">🏫 성의교정 대관 현황</h2>
"""

if not raw_df.empty:
    filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)]
    for d in sorted(filtered_df['full_date'].unique()):
        day_df = filtered_df[filtered_df['full_date'] == d]
        html_output += f'<div class="date-title">📅 {d} ({day_df.iloc[0]["요일"]})</div>'
        
        for bu in BUILDING_ORDER:
            if bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    html_output += f'<div class="bu-title">🏢 {bu}</div>'
                    html_output += """<div class="table-wrap"><table><thead><tr>
                        <th class="w-p">장소</th><th class="w-t">시간</th><th class="w-e">행사명</th>
                        <th class="w-c">인원</th><th class="w-d">부서</th><th class="w-s">상태</th>
                        </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        # 데이터 내부에 태그가 섞여 있어도 깨지지 않도록 한 번 더 안전하게 출력
                        html_output += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    html_output += "</tbody></table></div>"
else:
    html_output += "<p style='text-align:center; margin-top:50px;'>조회된 데이터가 없습니다.</p>"

html_output += "</body></html>"

# 5. 최종 출력
# height를 5000으로 매우 크게 설정하여 iframe 내부 스크롤을 방지하고 브라우저 전체 확대를 유도합니다.
components.html(html_output, height=5000, scrolling=False)
