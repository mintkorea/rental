import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정
st.set_page_config(page_title="성희교정 대관 현황 조회", page_icon="📋", layout="wide")

# 2. 통합 CSS (너비 고정 및 레이아웃 최적화)
st.markdown("""
    <style>
    .block-container { padding-top: 5rem !important; max-width: 95% !important; margin: 0 auto !important; }
    
    /* 가로 모드 표 스타일: 너비 고정 및 정렬 */
    .custom-table { width: 100%; border-collapse: collapse; table-layout: fixed; margin-bottom: 20px; }
    .custom-table th, .custom-table td { 
        border: 1px solid #ddd; padding: 10px; font-size: 14px; 
        overflow: hidden; text-overflow: ellipsis; word-break: break-all;
    }
    .custom-table th { background-color: #f0f2f6; font-weight: bold; text-align: center; }
    
    /* 열별 너비 및 정렬 설정 */
    .col-no { width: 40px; text-align: center; }
    .col-place { width: 15%; text-align: left; }
    .col-time { width: 120px; text-align: center; }
    .col-event { width: 35%; text-align: left; }
    .col-dept { width: 20%; text-align: left; }
    .col-status { width: 60px; text-align: center; }

    /* 세로 모드 카드 스타일 */
    .mobile-card { 
        padding: 15px; border: 1px solid #eee; border-radius: 8px; 
        margin-bottom: 10px; background-color: white; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .card-place { font-size: 16px; font-weight: bold; color: #1e3a5f; margin-bottom: 5px; }
    .card-time-status { display: flex; align-items: center; gap: 10px; margin-bottom: 5px; }
    .card-info { font-size: 13px; color: #666; line-height: 1.4; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; color: white; }

    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px; }
    .date-shift-bar { background-color: #444; color: white; padding: 12px; border-radius: 8px; text-align: center; margin: 20px 0 10px 0; font-weight: bold; }
    .building-header { padding:10px 0; margin-top:15px; font-weight: bold; color: #1e3a5f; font-size: 18px; display: flex; align-items: center; gap: 8px; }
    </style>
""", unsafe_allow_html=True)

# [데이터 로직 및 엑셀 생성 생략 - 기존과 동일]
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
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
                if start_date <= curr <= end_date:
                    rows.append({
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 사이드바 및 본문 구성
with st.sidebar:
    st.header("⚙️ 설정")
    view_mode = st.radio("📱 보기 모드", ["세로 모드 (카드)", "가로 모드 (표)"], index=1)
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    df_result = get_data(s_date, e_date)
    if not df_result.empty:
        # 간단 엑셀 다운로드 (생략 가능)
        output = io.BytesIO()
        df_result.to_excel(output, index=False)
        st.download_button("📥 엑셀 다운로드", output.getvalue(), f"대관현황_{s_date}.xlsx", use_container_width=True)

st.markdown('<div class="main-header">📋 성희교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_result.empty:
    for d_str in sorted(df_result['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        for bu in sel_bu:
            b_df = df_result[(df_result['full_date'] == d_str) & (df_result['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            if not b_df.empty:
                st.markdown(f'<div class="building-header">🏢 {bu} <span style="font-size:14px; color:#666; margin-left:10px;">(총 {len(b_df)}건)</span></div>', unsafe_allow_html=True)
                
                if view_mode == "가로 모드 (표)":
                    # HTML 테이블 직접 생성 (너비 및 정렬 완벽 제어)
                    table_html = f"""
                    <table class="custom-table">
                        <thead>
                            <tr>
                                <th class="col-no">No</th><th class="col-place">장소</th><th class="col-time">시간</th>
                                <th class="col-event">행사명</th><th class="col-dept">부서</th><th class="col-status">상태</th>
                            </tr>
                        </thead>
                        <tbody>
                    """
                    for idx, (_, r) in enumerate(b_df.iterrows(), 1):
                        table_html += f"""
                            <tr>
                                <td class="col-no">{idx}</td><td class="col-place">{r['장소']}</td><td class="col-time">{r['시간']}</td>
                                <td class="col-event">{r['행사명']}</td><td class="col-dept">{r['부서']}</td><td class="col-status">{r['상태']}</td>
                            </tr>
                        """
                    table_html += "</tbody></table>"
                    st.markdown(table_html, unsafe_allow_html=True)
                
                else: # 세로 모드 (카드)
                    for _, r in b_df.iterrows():
                        bg = '#27ae60' if r['상태'] == '확정' else '#95a5a6'
                        st.markdown(f'''
                            <div class="mobile-card">
                                <div class="card-place">📍 {r["장소"]}</div>
                                <div class="card-time-status">
                                    <span style="color:#e74c3c; font-weight:bold; font-size:14px;">🕒 {r["시간"]}</span>
                                    <span class="status-badge" style="background-color:{bg};">{r["상태"]}</span>
                                </div>
                                <div class="card-info">📄 {r["행사명"]} | {r["부서"]}</div>
                            </div>
                        ''', unsafe_allow_html=True)
else:
    st.info("조회된 날짜에 대관 내역이 없습니다.")
