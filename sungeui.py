import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

# 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 1. 건물 리스트 순서 (홈페이지 노출 순서와 동일하게 고정)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "대학본관", "서울성모별관"]

# CSS 디자인 (기존 다크 그레이 스타일 복원)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 25px; }
    .building-header { font-size: 20px !important; font-weight: 700; color: #2E5077; margin-top: 35px; margin-bottom: 15px; border-left: 5px solid #2E5077; padding-left: 10px; }
    .custom-table { width: 100% !important; border-collapse: collapse; margin-bottom: 30px; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 14px; padding: 12px 5px; border: 1px solid #333; }
    .custom-table td { border: 1px solid #eee; padding: 10px 5px !important; font-size: 13px; vertical-align: middle; text-align: center; }
</style>
""", unsafe_allow_html=True)

# 데이터 수집 함수 (인원 필드: peopleCount 적용)
@st.cache_data(ttl=60)
def get_verified_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            
            # [수정] 인원 필드명을 peopleCount로 변경
            p_count = item.get('peopleCount', '-')
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (str(curr.weekday()+1) in allow_days):
                        rows.append({
                            'raw_date': curr, 'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%m-%d'), 
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': p_count,
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        if not df.empty:
            # 건물 순서 정렬 (BUILDING_ORDER 기준)
            df['건물명'] = pd.Categorical(df['건물명'], categories=BUILDING_ORDER, ordered=True)
            return df.sort_values(by=['raw_date', '건물명', 'raw_time'])
        return df
    except: return pd.DataFrame()

# 실행 및 렌더링 로직
all_df = get_verified_data(now_today, now_today) # 기본 오늘 날짜

# [홈페이지 노출] 날짜 포함 6열 양식
for bu in BUILDING_ORDER:
    bu_df = all_df[all_df['건물명'] == bu] if not all_df.empty else pd.DataFrame()
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    if not bu_df.empty:
        html = '<table class="custom-table"><thead><tr>'
        html += '<th>날짜</th><th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>상태</th>'
        html += '</tr></thead><tbody>'
        for _, r in bu_df.iterrows():
            html += f'<tr><td>{r["날짜"]}</td><td>{r["장소"]}</td><td>{r["시간"]}</td>'
            html += f'<td style="text-align:left; padding-left:10px;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#999; margin-left:15px; margin-bottom:30px;">대관 내역 없음</p>', unsafe_allow_html=True)

# [PDF 생성] 날짜 제외, 인원 추가, 시간 좁게, 부서 넓게 (이전 로직 유지)
# ... (PDF 생성 함수 및 버튼 로직 생략)
