import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 데이터 처리 로직 (인원 데이터 추출 추가)
@st.cache_data(ttl=60)
def get_clean_data(s_date, e_date):
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
            allow_days = [d.strip() for d in str(item.get('allowDay', '')).split(',') if d.strip()]
            
            # 홈페이지 데이터에서 'entryCnt' 또는 관련 인원 필드 확인 (가칭: item.get('entryCnt', ''))
            # 실제 API 필드명에 맞춰 수정 가능합니다.
            entry_cnt = item.get('entryCnt', '') 

            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (str(curr.weekday() + 1) in allow_days):
                        rows.append({
                            'raw_date': curr,
                            'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''),
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''),
                            '인원': entry_cnt, # 홈페이지 데이터 필드 반영
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        return df.sort_values(by=['raw_date', '건물명', 'raw_time']) if not df.empty else df
    except: return pd.DataFrame()

# 데이터 로드
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
all_df = get_clean_data(start_selected, end_selected)

# 타이틀 설정
if start_selected == end_selected:
    display_title = f"성의교정 대관 현황 ({start_selected})"
else:
    display_title = f"성의교정 대관 현황 ({start_selected.strftime('%Y.%m.%d')} ~ {end_selected.strftime('%m.%d')})"

st.markdown(f'<h2 style="text-align:center;">{display_title}</h2>', unsafe_allow_html=True)

# 3. PDF 생성 함수 (이미지 양식 001.jpg 완벽 재현)
def create_final_pdf(df, main_title):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    font_path = "NanumGothic.ttf"
    pdf.add_font("Nanum", "", font_path)
    pdf.add_font("Nanum", "B", font_path)
    
    pdf.add_page()
    pdf.set_font("Nanum", size=18)
    pdf.cell(0, 20, main_title, ln=True, align='C')
    pdf.ln(5)

    # 날짜별 그룹화
    dates = df['날짜'].unique()
    for d in dates:
        d_df = df[df['날짜'] == d]
        buildings = d_df['건물명'].unique()
        
        for b in buildings:
            b_df = d_df[d_df['건물명'] == b]
            
            # 소제목: 건물명(날짜)
            pdf.set_font("Nanum", "B", 12)
            pdf.cell(0, 10, f"{b}({d})", ln=True, align='L')
            
            # 테이블 헤더 설정
            pdf.set_font("Nanum", size=10)
            pdf.set_fill_color(200, 200, 200) # 이미지와 유사한 회색 배경
            widths = [45, 45, 95, 20, 45, 20]
            headers = ["장소", "시간", "행사명", "인원", "부서", "상태"]
            
            for i, h in enumerate(headers):
                pdf.cell(widths[i], 10, h, border=1, align='C', fill=True)
            pdf.ln()
            
            # 데이터 행 출력
            pdf.set_font("Nanum", size=9)
            for _, row in b_df.iterrows():
                pdf.cell(widths[0], 9, str(row['장소']), border=1, align='C')
                pdf.cell(widths[1], 9, str(row['시간']), border=1, align='C')
                # 행사명 자동 줄바꿈 대신 길이 조절
                ev_name = str(row['행사명'])[:45] + ".." if len(str(row['행사명'])) > 47 else str(row['행사명'])
                pdf.cell(widths[2], 9, ev_name, border=1, align='L')
                pdf.cell(widths[3], 9, str(row['인원']), border=1, align='C') # 실제 인원 데이터 매핑
                pdf.cell(widths[4], 9, str(row['부서'])[:15], border=1, align='C')
                pdf.cell(widths[5], 9, str(row['상태']), border=1, align='C')
                pdf.ln()
            pdf.ln(6) # 섹션 간 간격

    return pdf.output()

# 4. 저장 기능
if not all_df.empty:
    try:
        pdf_bytes = create_final_pdf(all_df, display_title)
        st.sidebar.download_button(
            "📄 PDF 리포트 저장 (이미지 양식)", 
            bytes(pdf_bytes), 
            f"Rental_Report_{start_selected}.pdf", 
            "application/pdf"
        )
    except Exception as e:
        st.sidebar.error(f"PDF 생성 중 오류 발생: {e}")
