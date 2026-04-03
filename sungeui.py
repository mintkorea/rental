import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import csv

# 1. 페이지 설정 및 디자인 CSS (원본 스타일 유지)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .main .block-container { max-width: 1200px; margin: 0 auto; padding: 0.5rem 1rem !important; }
    .main-title { font-size: 22px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 10px; }
    .date-bar { background-color: #343a40; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; font-size: 15px; }
    .date-bar:first-of-type { margin-top: 0px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 12px 0 6px 0; border-left: 5px solid #1E3A5F; padding-left: 10px; background: #f1f4f9; padding: 5px 10px; }
    
    /* 세로 카드 스타일 */
    .mobile-card { background: white; border: 1px solid #eef0f2; border-radius: 6px; padding: 10px 14px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .row-1 { display: flex; align-items: center; white-space: nowrap; width: 100%; }
    .loc-text { font-size: 14px; font-weight: 800; color: #1E3A5F; flex: 1; overflow: hidden; text-overflow: ellipsis; }
    .time-text { font-size: 13px; font-weight: 700; color: #e74c3c; margin-left: auto; margin-right: 8px; }
    .status-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; color: white; font-weight: bold; background-color: #2ecc71; }
    .row-2 { font-size: 12px; color: #333; border-top: 1px solid #f8f9fa; padding-top: 6px; margin-top: 4px; }
    
    /* 기간 대관 강조용 (새로 추가) */
    .period-tag { font-size: 11px; color: #2E5077; background: #f0f4f8; padding: 4px 8px; border-radius: 4px; margin-top: 5px; display: inline-block; border: 1px solid #d1d9e6; }
    .section-label { font-size: 12px; font-weight: bold; color: #666; margin: 10px 0 5px 0; }
    </style>
""", unsafe_allow_html=True)

# --- 공통 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    anchor = date(2026, 3, 13)
    diff = (target_date - anchor).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# --- 엑셀/CSV 추출 로직 ---
def create_download_file(df, file_type="csv"):
    if file_type == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False, encoding='utf-8-sig')
        return output.getvalue().encode('utf-8-sig')
    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        return output.getvalue()

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            is_p = (item['startDt'] != item['endDt'])
            p_info = f"{item['startDt']}~{item['endDt']}"
            d_names = get_weekday_names(item.get('allowDay', ''))
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            '구분': '기간' if is_p else '당일',
                            '전체기간': p_info if is_p else '-',
                            '요일': d_names if is_p else '-'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# --- 메인 화면 ---
st.markdown('<div class="main-title">🏫 성의교정 시설 대관 현황</div>', unsafe_allow_html=True)

BUILDING_LIST = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]

with st.expander("🔍 검색 및 출력 설정", expanded=True):
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col1:
        s_date = st.date_input("조회 시작일", value=now_today)
        e_date = st.date_input("조회 종료일", value=s_date)
    with col2:
        sel_bu = st.multiselect("건물 선택", options=BUILDING_LIST, default=["성의회관", "의생명산업연구원", "옴니버스 파크"])
    with col3:
        # 1. 보기 유형 선택 (원본 기능 복구)
        view_mode = st.radio("보기 유형", ["세로 카드", "가로 표"], horizontal=True)
        
        # 2. 데이터 미리 가져오기
        df = get_data(s_date, e_date)
        
        # 3. 다운로드 버튼 (원본 위치 및 기능 반영)
        if not df.empty:
            st.download_button("📥 엑셀(CSV) 다운로드", data=create_download_file(df), file_name=f"대관현황_{s_date}.csv", use_container_width=True)

# 결과 출력 영역
if not df.empty:
    curr = s_date
    while curr <= e_date:
        d_str = curr.strftime('%Y-%m-%d')
        day_df = df[df['날짜'] == d_str]
        
        st.markdown(f'<div class="date-bar">📅 {d_str} ({["월","화","수","목","금","토","일"][curr.weekday()]}요일) | {get_shift(curr)}</div>', unsafe_allow_html=True)
        
        for bu in sel_bu:
            b_df = day_df[day_df['건물명'].str.replace(" ","") == bu.replace(" ","")]
            if not b_df.empty:
                st.markdown(f'<div class="bu-header">🏢 {bu} ({len(b_df)}건)</div>', unsafe_allow_html=True)
                
                if view_mode == "가로 표":
                    # 원본 리스트 뷰: 깔끔한 데이터프레임
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '인원', '상태', '구분']], hide_index=True, use_container_width=True)
                else:
                    # 원본 카드 뷰: 당일/기간 섹션 분리 적용
                    d_ev = b_df[b_df['구분'] == '당일'].sort_values('시간')
                    p_ev = b_df[b_df['구분'] == '기간'].sort_values('시간')
                    
                    if not d_ev.empty:
                        st.markdown('<div class="section-label">📌 당일 대관</div>', unsafe_allow_html=True)
                        for _, r in d_ev.iterrows():
                            st.markdown(f'''<div class="mobile-card"><div class="row-1"><span class="loc-text">📍 {r["장소"]}</span><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span></div><div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]}</div></div>''', unsafe_allow_html=True)
                    
                    if not p_ev.empty:
                        st.markdown('<div class="section-label">🗓️ 기간 대관</div>', unsafe_allow_html=True)
                        for _, r in p_ev.iterrows():
                            st.markdown(f'''<div class="mobile-card"><div class="row-1"><span class="loc-text">📍 {r["장소"]}</span><span class="time-text">🕒 {r["시간"]}</span><span class="status-badge">{"확정" if r["상태"]=="확정" else "대기"}</span></div><div class="row-2">🏷️ <b>{r["행사명"]}</b> / {r["부서"]}<br><span class="period-tag">🗓️ {r["전체기간"]} ({r["요일"]})</span></div></div>''', unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#999; font-size:12px; margin-left:10px; margin-bottom:20px;">내역 없음</div>', unsafe_allow_html=True)
        curr += timedelta(days=1)
else:
    st.info("조회된 데이터가 없습니다.")
