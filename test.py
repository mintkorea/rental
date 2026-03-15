import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 디자인 CSS
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    /* 상단 여백 및 메인 컨테이너 */
    .block-container { padding-top: 5rem !important; max-width: 1100px !important; margin: 0 auto !important; }
    
    .main-header { font-size: 24px; font-weight: bold; color: #1e3a5f; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; border-bottom: 3px solid #1e3a5f; padding-bottom: 10px; }
    
    .date-shift-bar {
        background-color: #444; color: white; padding: 12px; border-radius: 8px;
        text-align: center; margin: 15px 0 10px 0; font-weight: bold; font-size: 18px !important;
    }
    
    .building-header { display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #1e3a5f; padding:6px 0; margin-top:12px; }
    .count-text { font-size: 14px; font-weight: bold; color: #333; }

    /* [검증 필] HTML 표 고정 레이아웃 엔진 */
    .fixed-table {
        width: 100%;
        table-layout: fixed; /* 컬럼 너비를 아래 지정된 %로 강제 고정 */
        border-collapse: collapse;
        margin-top: 5px;
        background-color: white;
    }
    .fixed-table th, .fixed-table td {
        border: 1px solid #dee2e6;
        padding: 5px 2px;
        text-align: center;
        vertical-align: middle;
        height: 44px; /* 셀 높이 최소치 고정 */
    }
    .fixed-table th { background-color: #f8f9fa; font-size: 13px; font-weight: bold; color: #333; }
    .fixed-table td { font-size: 12.5px; color: #444; }

    /* 지정 비율: 장소(20) : 시간(15) : 행사(40) : 부서(18) : 상태(7) */
    .col-place { width: 20%; }  /* 의료원 소회의실(보직자회의실) 수용 가능 너비 */
    .col-time { width: 15%; }
    .col-event { width: 40%; }  /* 장소명의 정확히 2배 */
    .col-dept { width: 18%; }   /* 장소명과 유사한 수준 */
    .col-status { width: 7%; }

    /* 내용 제어: 2줄 자동개행 및 말줄임표 */
    .cell-wrapper {
        display: -webkit-box;
        -webkit-line-clamp: 2; /* 최대 2줄만 노출 */
        -webkit-box-orient: vertical;
        overflow: hidden;
        text-overflow: ellipsis;
        line-height: 1.25;
        word-break: break-all;
        max-height: 2.5em; 
    }

    /* 폰트 자동 축소 클래스 */
    .f-small { font-size: 11px !important; letter-spacing: -0.5px; }

    .empty-building-msg { color: #999; padding: 12px 5px; font-size: 13.5px; border-bottom: 1px solid #eee; }
    </style>
""", unsafe_allow_html=True)

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
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    curr_wd = str(curr.isoweekday())
                    if not allowed_days or curr_wd in allowed_days:
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

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)
    df_res = get_data(s_date, e_date)

st.markdown('<div class="main-header">📋 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if not df_res.empty:
    for d_str in sorted(df_res['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-shift-bar">📅 {d_str} | {get_shift(d_obj)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df_res[(df_res['full_date'] == d_str) & (df_res['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            count = len(b_df)
            
            # 건물 헤더 무조건 표출
            st.markdown(f'<div class="building-header"><div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div><div class="count-text">총 {count}건</div></div>', unsafe_allow_html=True)
            
            if count > 0:
                # HTML 표 렌더링 시작
                html_code = f"""
                <table class="fixed-table">
                    <thead>
                        <tr>
                            <th class="col-place">장소</th>
                            <th class="col-time">시간</th>
                            <th class="col-event">행사명</th>
                            <th class="col-dept">부서</th>
                            <th class="col-status">상태</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                for _, r in b_df.iterrows():
                    # 텍스트 길이에 따른 폰트 축소 클래스 계산
                    p_style = "f-small" if len(r['장소']) > 15 else ""
                    e_style = "f-small" if len(r['행사명']) > 30 else ""
                    d_style = "f-small" if len(r['부서']) > 15 else ""
                    
                    html_code += f"""
                        <tr>
                            <td class="{p_style}"><div class="cell-wrapper">{r['장소']}</div></td>
                            <td>{r['시간']}</td>
                            <td class="{e_style}"><div class="cell-wrapper">{r['행사명']}</div></td>
                            <td class="{d_style}"><div class="cell-wrapper">{r['부서']}</div></td>
                            <td style="color: {'#27ae60' if r['상태']=='확정' else '#e67e22'}; font-weight:bold;">{r['상태']}</td>
                        </tr>
                    """
                html_code += "</tbody></table>"
                st.markdown(html_code, unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="empty-building-msg">└ {bu} 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
