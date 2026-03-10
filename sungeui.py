import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 기본 설정 및 시간
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 홈페이지 디자인 (이미지 d888bc 스타일 유지)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 25px; }
    .building-header { font-size: 20px !important; font-weight: 700; color: #2E5077; margin-top: 35px; margin-bottom: 12px; display: flex; align-items: center; }
    .building-icon { margin-right: 8px; font-size: 22px; }
    
    .custom-table { width: 100% !important; border-collapse: collapse; margin-bottom: 30px; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 14px; padding: 12px 5px; border: 1px solid #333; }
    .custom-table td { border: 1px solid #eee; padding: 10px 5px !important; font-size: 13px; vertical-align: middle; text-align: center; line-height: 1.5; }
    
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }
    @media (max-width: 768px) {
        .pc-time { display: none !important; }
        .mobile-time { display: block !important; font-size: 11px; font-weight: bold; color: #d32f2f; }
        .custom-table td { font-size: 11px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 및 필터
st.sidebar.header("🔍 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 타이틀 조건부 표출 (요청 사항 반영)
if start_selected == end_selected:
    display_title = f"성의교정 대관 현황 ({start_selected})"
else:
    display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)

# 5. 데이터 크롤링 및 처리
@st.cache_data(ttl=60)
def fetch_data(s_date, e_date):
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
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (str(curr.weekday()+1) in allow_days):
                        rows.append({
                            'raw_date': curr, 'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%m-%d'), '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        return df.sort_values(by=['raw_date', 'raw_time']) if not df.empty else df
    except: return pd.DataFrame()

all_df = fetch_data(start_selected, end_selected)

# 6. 화면 출력 및 데이터 수집
pdf_content_list = []
for bu in selected_bu:
    st.markdown(f'<div class="building-header"><span class="building-icon">🏢</span>{bu}</div>', unsafe_allow_html=True)
    bu_df = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)] if not all_df.empty else pd.DataFrame()
    
    if not bu_df.empty:
        pdf_content_list.append((bu, bu_df)) # PDF 생성용 데이터 보관
        html = '<table class="custom-table"><thead><tr><th style="width:10%">날짜</th><th style="width:15%">시간</th><th style="width:15%">장소</th><th style="width:35%">행사명</th><th style="width:15%">부서</th><th style="width:10%">상태</th></tr></thead><tbody>'
        for _, r in bu_df.iterrows():
            st_t, en_t = r['시간'].split('~')[0].strip(), r['시간'].split('~')[1].strip()
            time_td = f'<div class="pc-time">{r["시간"]}</div><div class="mobile-time">{st_t}<br>~ {en_t}</div>'
            html += f'<tr><td>{r["날짜"]}</td><td>{time_td}</td><td>{r["장소"]}</td><td style="text-align:left; padding-left:10px;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#999; font-size:13px; margin-left:10px;">내역 없음</p>', unsafe_allow_html=True)

# 7. PDF 생성 함수 (이미지 형태의 깔끔한 표 양식)
def create_styled_pdf(content_list, main_title):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf")
    pdf.add_page()
    
    # 메인 타이틀
    pdf.set_font("Nanum", size=18)
    pdf.cell(0, 15, main_title, ln=True, align='C')
    pdf.ln(5)

    for bu_name, df in content_list:
        # 건물별 헤더
        pdf.set_font("Nanum", size=12)
        pdf.set_text_color(46, 80, 119) # 건물명 강조 색상
        pdf.cell(0, 10, f"■ {bu_name}", ln=True)
        pdf.set_text_color(0, 0, 0)
        
        # 테이블 헤더
        pdf.set_font("Nanum", size=10)
        pdf.set_fill_color(240, 240, 240)
        cols = ["날짜", "장소", "시간", "행사명", "부서", "상태"]
        widths = [20, 40, 40, 100, 50, 25]
        for i, col in enumerate(cols):
            pdf.cell(widths[i], 10, col, border=1, align='C', fill=True)
        pdf.ln()
        
        # 데이터 행
        pdf.set_font("Nanum", size=9)
        for _, row in df.iterrows():
            pdf.cell(widths[0], 9, str(row['날짜']), border=1, align='C')
            pdf.cell(widths[1], 9, str(row['장소'])[:15], border=1, align='C')
            pdf.cell(widths[2], 9, str(row['시간']), border=1, align='C')
            pdf.cell(widths[3], 9, str(row['행사명'])[:45], border=1)
            pdf.cell(widths[4], 9, str(row['부서'])[:15], border=1, align='C')
            pdf.cell(widths[5], 9, str(row['상태']), border=1, align='C')
            pdf.ln()
        pdf.ln(10) # 건물 간 간격
        
    return pdf.output()

# 8. 저장 버튼
if pdf_content_list:
    st.sidebar.markdown("---")
    # 엑셀 저장
    final_excel_df = pd.concat([d for b, d in pdf_content_list]).drop(columns=['raw_date', 'raw_time'])
    out_ex = BytesIO()
    with pd.ExcelWriter(out_ex, engine='openpyxl') as writer:
        final_excel_df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀(Excel) 저장", out_ex.getvalue(), f"rental_{start_selected}.xlsx")
    
    # PDF 저장
    try:
        pdf_bytes = create_styled_pdf(pdf_content_list, display_title)
        st.sidebar.download_button("📄 PDF 리포트 저장", bytes(pdf_bytes), f"rental_{start_selected}.pdf", "application/pdf")
    except Exception as e:
        st.sidebar.error(f"PDF 생성 오류: {e}")import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 1. 기본 설정 및 시간
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. CSS 설정: 홈페이지 디자인 (이미지 d888bc 스타일 유지)
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 26px !important; font-weight: 800; color: #002D56; margin-bottom: 25px; }
    .building-header { font-size: 20px !important; font-weight: 700; color: #2E5077; margin-top: 35px; margin-bottom: 12px; display: flex; align-items: center; }
    .building-icon { margin-right: 8px; font-size: 22px; }
    
    .custom-table { width: 100% !important; border-collapse: collapse; margin-bottom: 30px; table-layout: fixed !important; }
    .custom-table th { background-color: #444 !important; color: white !important; font-size: 14px; padding: 12px 5px; border: 1px solid #333; }
    .custom-table td { border: 1px solid #eee; padding: 10px 5px !important; font-size: 13px; vertical-align: middle; text-align: center; line-height: 1.5; }
    
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }
    @media (max-width: 768px) {
        .pc-time { display: none !important; }
        .mobile-time { display: block !important; font-size: 11px; font-weight: bold; color: #d32f2f; }
        .custom-table td { font-size: 11px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 3. 사이드바 및 필터
st.sidebar.header("🔍 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 4. 타이틀 조건부 표출 (요청 사항 반영)
if start_selected == end_selected:
    display_title = f"성의교정 대관 현황 ({start_selected})"
else:
    display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)

# 5. 데이터 크롤링 및 처리
@st.cache_data(ttl=60)
def fetch_data(s_date, e_date):
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
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (str(curr.weekday()+1) in allow_days):
                        rows.append({
                            'raw_date': curr, 'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%m-%d'), '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        return df.sort_values(by=['raw_date', 'raw_time']) if not df.empty else df
    except: return pd.DataFrame()

all_df = fetch_data(start_selected, end_selected)

# 6. 화면 출력 및 데이터 수집
pdf_content_list = []
for bu in selected_bu:
    st.markdown(f'<div class="building-header"><span class="building-icon">🏢</span>{bu}</div>', unsafe_allow_html=True)
    bu_df = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)] if not all_df.empty else pd.DataFrame()
    
    if not bu_df.empty:
        pdf_content_list.append((bu, bu_df)) # PDF 생성용 데이터 보관
        html = '<table class="custom-table"><thead><tr><th style="width:10%">날짜</th><th style="width:15%">시간</th><th style="width:15%">장소</th><th style="width:35%">행사명</th><th style="width:15%">부서</th><th style="width:10%">상태</th></tr></thead><tbody>'
        for _, r in bu_df.iterrows():
            st_t, en_t = r['시간'].split('~')[0].strip(), r['시간'].split('~')[1].strip()
            time_td = f'<div class="pc-time">{r["시간"]}</div><div class="mobile-time">{st_t}<br>~ {en_t}</div>'
            html += f'<tr><td>{r["날짜"]}</td><td>{time_td}</td><td>{r["장소"]}</td><td style="text-align:left; padding-left:10px;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#999; font-size:13px; margin-left:10px;">내역 없음</p>', unsafe_allow_html=True)

# 7. PDF 생성 함수 (이미지 형태의 깔끔한 표 양식)
def create_styled_pdf(content_list, main_title):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf")
    pdf.add_page()
    
    # 메인 타이틀
    pdf.set_font("Nanum", size=18)
    pdf.cell(0, 15, main_title, ln=True, align='C')
    pdf.ln(5)

    for bu_name, df in content_list:
        # 건물별 헤더
        pdf.set_font("Nanum", size=12)
        pdf.set_text_color(46, 80, 119) # 건물명 강조 색상
        pdf.cell(0, 10, f"■ {bu_name}", ln=True)
        pdf.set_text_color(0, 0, 0)
        
        # 테이블 헤더
        pdf.set_font("Nanum", size=10)
        pdf.set_fill_color(240, 240, 240)
        cols = ["날짜", "장소", "시간", "행사명", "부서", "상태"]
        widths = [20, 40, 40, 100, 50, 25]
        for i, col in enumerate(cols):
            pdf.cell(widths[i], 10, col, border=1, align='C', fill=True)
        pdf.ln()
        
        # 데이터 행
        pdf.set_font("Nanum", size=9)
        for _, row in df.iterrows():
            pdf.cell(widths[0], 9, str(row['날짜']), border=1, align='C')
            pdf.cell(widths[1], 9, str(row['장소'])[:15], border=1, align='C')
            pdf.cell(widths[2], 9, str(row['시간']), border=1, align='C')
            pdf.cell(widths[3], 9, str(row['행사명'])[:45], border=1)
            pdf.cell(widths[4], 9, str(row['부서'])[:15], border=1, align='C')
            pdf.cell(widths[5], 9, str(row['상태']), border=1, align='C')
            pdf.ln()
        pdf.ln(10) # 건물 간 간격
        
    return pdf.output()

# 8. 저장 버튼
if pdf_content_list:
    st.sidebar.markdown("---")
    # 엑셀 저장
    final_excel_df = pd.concat([d for b, d in pdf_content_list]).drop(columns=['raw_date', 'raw_time'])
    out_ex = BytesIO()
    with pd.ExcelWriter(out_ex, engine='openpyxl') as writer:
        final_excel_df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 엑셀(Excel) 저장", out_ex.getvalue(), f"rental_{start_selected}.xlsx")
    
    # PDF 저장
    try:
        pdf_bytes = create_styled_pdf(pdf_content_list, display_title)
        st.sidebar.download_button("📄 PDF 리포트 저장", bytes(pdf_bytes), f"rental_{start_selected}.pdf", "application/pdf")
    except Exception as e:
        st.sidebar.error(f"PDF 생성 오류: {e}")
