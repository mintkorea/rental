import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 사이드바 상시 확장 (가이드라인 준수)
st.set_page_config(
    page_title="성의교정 실시간 대관 현황", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일: 폰트 밸런스 조정 및 1줄 나열 강제 (가이드라인 준수)
# SyntaxError 방지를 위해 format용 {{ }} 사용
style_html = """
<style>
    .main-title {{ font-size: 2.3rem !important; font-weight: 800; color: #1e3a5f; text-align: center; margin: 15px 0; }}
    .bu-header {{ font-size: 1.4rem !important; font-weight: 700; color: #1e3a5f; margin: 0; }}
    .event-shell {{ border-bottom: 1px solid #eee; padding: 10px 0; background: white; }}
    .row-main {{ display: flex; align-items: center; justify-content: space-between; gap: 4px; width: 100%; }}
    .col-place {{ 
        flex: 5.5; font-weight: 700; color: #1e3a5f; 
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: block;
    }}
    .col-time {{ flex: 3.2; font-size: 12px; color: #d9534f; font-weight: 600; text-align: center; white-space: nowrap; }}
    .col-status {{ flex: 1.3; font-size: 12px; font-weight: 800; text-align: right; white-space: nowrap; }}
    .row-sub {{ font-size: 12px; color: #666; margin-top: 5px; line-height: 1.3; }}
</style>
"""
st.markdown(style_html, unsafe_allow_html=True)

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return ['A', 'B', 'C'][diff % 3] + "조"

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
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    # [가이드라인] 요일 필터링 적용
                    if not allow_days or str(curr.isoweekday()) in allow_days:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': "{0}~{1}".format(item.get('startTime', ''), item.get('endTime', '')),
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 4. 사이드바 구성: 자동 세팅 및 엑셀 다운로드 (가이드라인 준수)
with st.sidebar:
    st.header("🔍 설정")
    view_mode = st.radio("📺 보기 모드", ["PC 모드", "모바일(세로)"], index=1)
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

    # [가이드라인] 디자인과 무관한 독립형 엑셀 다운로드 기능
    df = get_data(s_date, e_date)
    if not df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='대관현황')
        st.download_button(
            label="📊 엑셀 결과 다운로드",
            data=output.getvalue(),
            file_name="rental_data_{0}.xlsx".format(s_date.strftime('%Y%m%d')),
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

st.markdown('<div class="main-title">🏢 성의교정 실시간 대관 현황</div>', unsafe_allow_html=True)

if not df.empty:
    for d_str in sorted(df['날짜'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        st.markdown('<div style="background:#444; color:white; padding:8px 12px; border-radius:5px; margin-top:15px; font-weight:bold;">🗓️ {0} | 근무조: {1}</div>'.format(d_str, get_shift(d_obj)), unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = df[(df['날짜'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
            if not b_df.empty:
                st.markdown('<div style="display:flex; align-items:center; justify-content:space-between; border-bottom:2px solid #1e3a5f; margin:15px 0 5px 0;"><span class="bu-header">🏢 {0}</span><span style="font-size:12px; background:#e1e8f0; padding:2px 8px; border-radius:10px;">총 {1}건</span></div>'.format(bu, len(b_df)), unsafe_allow_html=True)
                
                if view_mode == "모바일(세로)":
                    for _, row in b_df.iterrows():
                        color = "#28a745" if row['상태'] == "확정" else "#d9534f"
                        # [가이드라인] 가변 폰트 및 장소명 1줄 제어
                        p_name = row['장소']
                        p_font = "14px"
                        if len(p_name) > 10: p_font = "12px"
                        if len(p_name) > 14: p_font = "11px"

                        # [가이드라인] .format() 사용하여 구문 에러 방지
                        html_item = """
                        <div class="event-shell">
                            <div class="row-main">
                                <div class="col-place" style="font-size:{0};">📍 {1}</div>
                                <div class="col-time">🕒 {2}</div>
                                <div class="col-status" style="color:{3};">{4}</div>
                            </div>
                            <div class="row-sub">📄 {5} ({6}, {7}명)</div>
                        </div>
                        """.format(p_font, p_name, row['시간'], color, row['상태'], row['행사명'], row['부서'], row['인원'])
                        st.markdown(html_item, unsafe_allow_html=True)
                else:
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
else:
    st.info("조회된 내역이 없습니다.")
