import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정 및 줌/모바일 반응형 강제 해제
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 브라우저에게 줌을 허용하고 가로 폭을 고정하도록 명령
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes">
    </head>
    <style>
        /* 1. 전체 줌 및 터치 조작 허용 */
        html, body { 
            zoom: 100%; 
            touch-action: auto !important; 
            overflow-x: auto !important;
        }

        /* 2. 제목 및 헤더 스타일 */
        .main-title { font-size: 22px !important; font-weight: 800; text-align: center; margin-bottom: 10px; }
        .date-header { font-size: 18px !important; font-weight: 800; padding: 10px; margin-top: 25px; border-bottom: 2px solid #ddd; }
        .date-sat { color: #007BFF !important; } /* 토요일 청색 */
        .date-sun { color: #FF0000 !important; } /* 일요일 적색 */
        .building-header { font-size: 16px !important; font-weight: 700; margin: 15px 0 5px 0; padding-left: 10px; border-left: 5px solid #2E5077; }

        /* 3. 표 레이아웃 완전 고정 (최소 800px 유지) */
        .table-wrapper { width: 100%; overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
        table { 
            width: 100% !important; 
            min-width: 800px !important; /* 모바일에서 찌그러짐 방지 */
            border-collapse: collapse; 
            table-layout: fixed !important; 
            margin-bottom: 20px;
            background-color: white;
        }
        th, td { border: 1px solid #ccc; padding: 8px 4px; text-align: center; vertical-align: middle; font-size: 13px; }
        th { background-color: #f8f9fa; font-weight: 700; }

        /* 4. 열 너비 비율 강제 지정 (시간 필드 최소화) */
        .col-place { width: 15%; }    /* 장소 */
        .col-time  { width: 90px; }   /* 시간 (장소보다 작게 고정) */
        .col-event { width: 40%; }    /* 행사명 (가장 넓게) */
        .col-count { width: 45px; }   /* 인원 */
        .col-dept  { width: 20%; }    /* 부서 */
        .col-stat  { width: 50px; }   /* 상태 */

        /* 행사명 등 긴 텍스트 2줄 제한 및 폰트 최적화 */
        .text-truncate {
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            word-break: break-all;
            line-height: 1.3;
            font-size: 12px;
        }
    </style>
""", unsafe_allow_html=True)

# 2. 데이터 로직 (스크린샷에서 확인된 성공 로직 그대로 유지)
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
                        'w_num': curr.weekday(),
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

# 3. UI 구성
st.sidebar.header("🗓️ 조회 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected + timedelta(days=7))
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

all_df = get_data(start_selected, end_selected)

st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)

if not all_df.empty:
    for date in sorted(all_df['full_date'].unique()):
        day_df = all_df[all_df['full_date'] == date]
        w_num = day_df.iloc[0]['w_num']
        color_class = "date-sat" if w_num == 5 else ("date-sun" if w_num == 6 else "")
        
        st.markdown(f'<div class="date-header {color_class}">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
        
        for bu in selected_bu:
            bu_df = day_df[day_df['건물명'] == bu]
            if not bu_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                
                # 표 생성 (HTML 구조 최적화)
                table_html = f"""
                <div class="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th class="col-place">장소</th>
                                <th class="col-time">시간</th>
                                <th class="col-event">행사명</th>
                                <th class="col-count">인원</th>
                                <th class="col-dept">부서</th>
                                <th class="col-stat">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                for _, r in bu_df.iterrows():
                    table_html += f"""
                        <tr>
                            <td><div class="text-truncate">{r['장소']}</div></td>
                            <td>{r['시간']}</td>
                            <td style="text-align:left;"><div class="text-truncate">{r['행사명']}</div></td>
                            <td>{r['인원']}</td>
                            <td><div class="text-truncate">{r['부서']}</div></td>
                            <td>{r['상태']}</td>
                        </tr>
                    """
                table_html += "</tbody></table></div>"
                st.markdown(table_html, unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
