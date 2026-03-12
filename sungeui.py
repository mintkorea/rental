import streamlit as st
import streamlit.components.v1 as components
import requests
import pandas as pd
from datetime import datetime
import pytz

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 데이터 로드 함수 (기존 로직 유지)
@st.cache_data(ttl=60)
def get_data(target_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": target_date.isoformat(), "end": target_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            rows.append({
                '건물명': str(item.get('buNm', '')).strip(),
                '장소': item.get('placeNm', ''), 
                '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                '행사명': item.get('eventNm', ''), 
                '인원': item.get('peopleCount', ''),
                '부서': item.get('mgDeptNm', ''),
                '상태': '확정' if item.get('status') == 'Y' else '대기'
            })
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 메인 UI 및 출력
st.sidebar.title("📅 설정")
date_input = st.sidebar.date_input("조회 날짜", value=now_today)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관"]
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER[:2])

st.title("🏫 성의교정 대관 현황")

df = get_data(date_input)

if not df.empty:
    for bu in selected_bu:
        bu_df = df[df['건물명'] == bu]
        if not bu_df.empty:
            st.subheader(f"🏢 {bu}")
            
            # HTML 노출 방지의 핵심: Components 사용
            # 모든 표의 너비를 픽셀(px)로 고정하여 건물마다 크기가 달라지는 문제 해결
            table_content = ""
            for _, r in bu_df.iterrows():
                table_content += f"""
                <tr>
                    <td style="width:100px;">{r['장소']}</td>
                    <td style="width:120px;">{r['시간']}</td>
                    <td style="width:300px; text-align:left;">{r['행사명']}</td>
                    <td style="width:60px;">{r['인원']}</td>
                    <td style="width:130px;">{r['부서']}</td>
                    <td style="width:70px;">{r['상태']}</td>
                </tr>
                """

            full_html = f"""
            <div style="overflow-x:auto;">
                <style>
                    table {{ width: 780px; border-collapse: collapse; table-layout: fixed; font-family: sans-serif; border: 1px solid #ddd; }}
                    th, td {{ border: 1px solid #ddd; padding: 10px 5px; text-align: center; font-size: 13px; word-break: break-all; }}
                    th {{ background-color: #f2f2f2; font-weight: bold; }}
                </style>
                <table>
                    <thead>
                        <tr>
                            <th style="width:100px;">장소</th>
                            <th style="width:120px;">시간</th>
                            <th style="width:300px;">행사명</th>
                            <th style="width:60px;">인원</th>
                            <th style="width:130px;">부서</th>
                            <th style="width:70px;">상태</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_content}
                    </tbody>
                </table>
            </div>
            """
            
            # st.markdown 대신 components.html을 사용 (높이는 표 크기에 맞게 조절)
            # 이 방식은 HTML 태그가 텍스트로 보일 수 없는 독립 샌드박스 방식입니다.
            table_height = (len(bu_df) * 45) + 60 
            components.html(full_html, height=table_height, scrolling=False)
else:
    st.info("조회된 데이터가 없습니다.")
