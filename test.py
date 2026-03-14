import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz

# 1. 초기 설정 및 스타일 (전달해주신 모바일 스타일 유지)
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
<style>
    .building-header { font-size: 19px !important; font-weight: bold; color: #2E5077; margin-top: 25px; border-bottom: 2px solid #2E5077; padding-bottom: 5px; margin-bottom: 15px; }
    .section-title { font-size: 16px; font-weight: bold; color: #555; margin: 15px 0 8px 0; padding-left: 8px; border-left: 4px solid #ccc; }
    .event-card { border: 1px solid #E0E0E0; border-left: 6px solid #2E5077; padding: 15px; border-radius: 8px; margin-bottom: 12px !important; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-badge { display: inline-block; padding: 3px 10px; font-size: 12px; border-radius: 12px; font-weight: bold; float: right; }
    .status-y { background-color: #FFF4E5; color: #B25E09; } .status-n { background-color: #E8F0FE; color: #1967D2; }
    .card-place { font-size: 18px; font-weight: bold; color: #1E3A5F; margin-bottom: 5px; }
    .card-time { color: #FF4B4B; font-weight: bold; font-size: 16px; margin: 5px 0; }
    .card-event { font-size: 15px; color: #333; font-weight: bold; margin-top: 5px; }
    .bottom-info { font-size: 13px; color: #666; margin-top: 10px; display: flex; justify-content: space-between; border-top: 1px solid #f0f0f0; padding-top: 8px; }
</style>
""", unsafe_allow_html=True)

# 2. 데이터 처리 로직
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
            
            # [수정] allowDay를 소스1처럼 리스트로 변환 (예: ['1', '3', '5'])
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [d.strip() for d in allow_day_raw.split(",") if d.strip().isdigit()]
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    # --- [핵심] 요일 엄격 필터링 ---
                    curr_wd = str(curr.isoweekday()) # 월=1, ..., 일=7
                    
                    # allowDay가 비어있지 않은 경우, 현재 요일이 포함될 때만 추가
                    if not allowed_days or curr_wd in allowed_days:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', '') or '-',
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '인원': str(item.get('peopleCount', '0')),
                            '상태': '확정' if item.get('status') == 'Y' else '대기',
                            'is_period': s_dt != e_dt,
                            'period_range': f"{item['startDt']} ~ {item['endDt']}",
                            'allow_day_names': ['','월','화','수','목','금','토','일'] # 요일 표시용
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# 3. 메인 화면 구성
with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    ALL_BU = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
    sel_bu = st.multiselect("건물 필터", options=ALL_BU, default=["성의회관", "의생명산업연구원"])

df = get_data(s_date, e_date)

if not df.empty:
    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        wd_name = ['','월','화','수','목','금','토','일'][d_obj.isoweekday()]
        
        st.markdown(f"""<div style="background-color:#F8FAFF; padding:15px; border-radius:10px; border:1px solid #D1D9E6; margin-top:35px;">
            <h3 style="margin:0; color:#1E3A5F;">📅 {d_str} ({wd_name})</h3>
        </div>""", unsafe_allow_html=True)
        
        for bu in sel_bu:
            # 소스1의 유연한 건물명 매칭 적용
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False))]
            st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
            
            if not b_df.empty:
                t_ev = b_df[b_df['is_period'] == False]
                p_ev = b_df[b_df['is_period'] == True]
                
                # 당일/기간 분리 노출
                for ev_df, title in [(t_ev, "📌 당일 대관"), (p_ev, "🗓️ 기간 대관")]:
                    if not ev_df.empty:
                        st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
                        for _, row in ev_df.iterrows():
                            s_cls, s_txt = ("status-y", "예약확정") if row['상태'] == '확정' else ("status-n", "신청대기")
                            info_txt = f"🗓️ {row['period_range']}" if row['is_period'] else f"🗓️ 당일 행사"
                            
                            st.markdown(f"""
                            <div class="event-card">
                                <span class="status-badge {s_cls}">{s_txt}</span>
                                <div class="card-place">📍 {row['장소']}</div>
                                <div class="card-time">⏰ {row['시간']}</div>
                                <div class="card-event">📄 {row['행사명']}</div>
                                <div class="bottom-info">
                                    <span>{info_txt}</span>
                                    <span style="font-weight:bold;">👤 {row['부서']} ({row['인원']}명)</span>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
            else:
                st.markdown('<div style="color:#999; text-align:center; padding:15px; font-size:13px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회된 내역이 없습니다.")
