import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os
import streamlit.components.v1 as components

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
DEFAULT_BUILDINGS = ["성의회관", "의생명산업연구원"]

# 2. 데이터 로드 및 "강력 정제" (HTML 파손 방지 핵심)
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
            
            # HTML 깨짐 방지를 위한 텍스트 정제 함수
            def clean_t(t):
                if not t: return ""
                return str(t).replace("'", " ").replace('"', " ").replace("<", " ").replace(">", " ").replace("\n", " ").strip()

            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    rows.append({
                        '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': clean_t(item.get('buNm', '')),
                        '장소': clean_t(item.get('placeNm', '')), 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': clean_t(item.get('eventNm', '')), 
                        '인원': clean_t(item.get('peopleCount', '')),
                        '부서': clean_t(item.get('mgDeptNm', '')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# (기존 PDF 생성 함수 생략 - 소스 유지됨)
def create_split_pdf(df, selected_buildings):
    # ... 사용자님이 제공하신 기존 PDF 코드 그대로 사용 ...
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    # (이하 생략 - 사용자 원본 소스 적용)
    return bytes(pdf.output())

# 3. 사이드바 UI
st.sidebar.title("📅 대관 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

all_df = get_data(start_selected, end_selected)

# 4. 화면 출력용 HTML 생성 (줌/확대 강제 설정)
# viewport 메타 태그를 삽입하여 모바일 줌을 활성화합니다.
html_body = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    <style>
        body {{ font-family: sans-serif; padding: 10px; background: white; }}
        .date-h {{ font-size: 18px; font-weight: 800; background: #f0f2f6; padding: 10px; border-left: 6px solid #2e5077; margin-top: 25px; }}
        .bu-h {{ font-size: 15px; font-weight: 700; margin: 15px 0 5px 0; border-left: 5px solid #2E5077; padding-left: 10px; }}
        .t-wrap {{ width: 100%; overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; min-width: 850px; table-layout: fixed; }}
        th, td {{ border: 1px solid #ccc; padding: 10px 5px; text-align: center; font-size: 13px; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .w-p {{ width: 130px; }} .w-t {{ width: 90px; }} .w-e {{ width: auto; }}
        .w-c {{ width: 45px; }} .w-d {{ width: 110px; }} .w-s {{ width: 55px; }}
        .left {{ text-align: left !important; padding-left: 8px !important; }}
    </style>
</head>
<body>
    <h2 style="text-align:center;">🏫 성의교정 대관 현황</h2>
"""

if not all_df.empty:
    filtered_df = all_df[all_df['건물명'].isin(selected_bu)]
    for d in sorted(filtered_df['full_date'].unique()):
        day_df = filtered_df[filtered_df['full_date'] == d]
        html_body += f'<div class="date-h">📅 {d} ({day_df.iloc[0]["요일"]}요일)</div>'
        for bu in BUILDING_ORDER:
            if bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    html_body += f'<div class="bu-h">🏢 {bu}</div>'
                    html_output = """<div class="t-wrap"><table><thead><tr>
                        <th class="w-p">장소</th><th class="w-t">시간</th><th class="w-e">행사명</th>
                        <th class="w-c">인원</th><th class="w-d">부서</th><th class="w-s">상태</th>
                        </tr></thead><tbody>"""
                    for _, r in bu_df.iterrows():
                        html_output += f"<tr><td>{r['장소']}</td><td>{r['시간']}</td><td class='left'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>"
                    html_body += html_output + "</tbody></table></div>"
    html_body += "</body></html>"
    # 높이를 넉넉히 잡아 줌 시 잘림을 방지합니다.
    components.html(html_body, height=4000, scrolling=False)
else:
    st.info("조회된 내역이 없습니다.")
