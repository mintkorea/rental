import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import io

# 1. 초기 설정 및 CSS (다크모드 완벽 방어)
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

st.markdown("""
<style>
    .stApp { background-color: white !important; color: black !important; }
    .main-title { font-size: 24px !important; font-weight: 800; text-align: center; color: #1E3A5F !important; margin-bottom: 20px; }
    .date-header { 
        background-color: #2E5077 !important; color: white !important; padding: 10px 15px; 
        border-radius: 5px; margin-top: 30px; display: flex; 
        justify-content: space-between; align-items: center;
    }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 20px; border-left: 5px solid #2E5077; padding-left: 10px; color: #333 !important; }
    table { width: 100%; border-collapse: collapse; table-layout: fixed; background-color: white !important; border: 1px solid #ddd !important; }
    th { background-color: #f8f9fa !important; color: #333 !important; border: 1px solid #ccc !important; text-align: center !important; padding: 10px 2px; font-size: 13px; }
    td { border: 1px solid #eee !important; color: #333 !important; padding: 10px 5px; font-size: 13px; vertical-align: middle; background-color: white !important; text-align: center; }
    .no-building-data { color: #d9534f !important; font-size: 14px; font-weight: bold; padding: 15px; border: 1px dashed #d9534f !important; border-radius: 5px; margin-top: 10px; text-align: center; background-color: #fffafa !important; }
</style>
""", unsafe_allow_html=True)

# 2. PDF 함수 (에러 방지용)
def create_pdf(df, selected_buildings):
    pdf = FPDF()
    pdf.add_page()
    try:
        pdf.add_font('Nanum', '', 'NanumGothic.ttf')
        pdf.set_font('Nanum', size=14)
    except:
        pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt="Rental Status Report", ln=True, align='C')
    return pdf.output()

# 3. 사이드바 설정 (사용자 요청 위치)
with st.sidebar:
    st.header("📅 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 필터", options=BUILDING_ORDER, default=["성의회관", "의생명산업연구원"])

# 4. 메인 데이터 로직 및 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

if sel_bu:
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    
    try:
        res = requests.get(url, params=params, timeout=10)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()] if allow_day_raw and allow_day_raw.lower() != 'none' else []
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
    except:
        df = pd.DataFrame()

    # 데이터가 비어있어도 날짜 루프는 돌려서 건물별 '내역 없음'을 표시함
    date_range = pd.date_range(s_date, e_date).strftime('%Y-%m-%d').tolist()
    
    for date_str in date_range:
        current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        w_idx = current_date.weekday()
        yoil = ['월','화','수','목','금','토','일'][w_idx]
        
        st.markdown(f'<div class="date-header"><span>📅 {date_str}</span><span>({yoil}요일)</span></div>', unsafe_allow_html=True)
        
        for b in sel_bu:
            st.markdown(f'<div class="building-header">🏢 {b}</div>', unsafe_allow_html=True)
            # 해당 날짜, 해당 건물의 데이터 필터링
            if not df.empty:
                b_df = df[(df['full_date'] == date_str) & (df['건물명'] == b)]
            else:
                b_df = pd.DataFrame()

            if not b_df.empty:
                table_html = "<table><thead><tr><th style='width:18%'>장소</th><th style='width:15%'>시간</th><th>행사명</th><th style='width:8%'>인원</th><th style='width:20%'>부서</th><th style='width:8%'>상태</th></tr></thead><tbody>"
                for _, r in b_df.sort_values('시간').iterrows():
                    table_html += f"<tr><td style='text-align:left'>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left'>{r['행사명']}</td><td>{r['인원']}</td><td style='text-align:left'>{r['부서']}</td><td>{r['상태']}</td></tr>"
                st.markdown(table_html + "</tbody></table>", unsafe_allow_html=True)
            else:
                # [개선] 데이터가 없어도 '내역 없음' 박스를 노출하여 사이드바 선택에 반응함을 보여줌
                st.markdown(f'<div class="no-building-data">"{b}"에 대한 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("왼쪽 사이드바에서 건물을 선택해 주세요.")
