import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

# 1. 페이지 및 기본 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스 파크 의과대학", "옴니버스 파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 설정
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 20px !important; font-weight: 800; text-align: center; margin-bottom: 15px; }
    .building-header { font-size: 16px !important; font-weight: 700; margin-top: 25px; border-left: 5px solid #2E5077; padding-left: 10px; margin-bottom: 10px; }
    .table-container { width: 100%; overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 600px; }
    th { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 6px; font-size: 11px; font-weight: bold; }
    td { border: 1px solid #eee; padding: 8px 6px; font-size: 12px; text-align: center; }
    .no-data { color: #666; font-size: 11px; padding: 10px; border: 1px solid #eee; text-align: center; }
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 함수 (요일 필터링 로직 반영)
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
            
            # [수정] 요일 필터링을 위한 allowDay 리스트화
            allowed_days = str(item.get('allowDay', '')).split(',')
            allowed_days = [d.strip() for d in allowed_days if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    # [수정] 현재 날짜의 요일(월=1...일=7)이 allowDay에 포함되는지 확인
                    curr_weekday = str(curr.isoweekday())
                    is_allowed = True
                    if s_dt != e_dt and allowed_days: # 기간 대관일 때만 요일 체크
                        if curr_weekday not in allowed_days:
                            is_allowed = False
                    
                    if is_allowed:
                        rows.append({
                            '날짜': curr.strftime('%m-%d'),
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
            return df.sort_values(by=['날짜', '건물명', '시간'])
        return df
    except: return pd.DataFrame()

# 4. PDF 생성 함수 (기존 소스 유지)
def create_building_split_pdf(df, title_text, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
    pdf.add_page()
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    for bu in selected_buildings:
        bu_df = df[df['건물명'] == bu]
        pdf.set_font("Nanum", size=12)
        pdf.set_text_color(46, 80, 119)
        pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
        pdf.set_text_color(0, 0, 0)
        
        cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 50), ("상태", 15)]
        pdf.set_fill_color(240, 240, 240)
        pdf.set_font("Nanum", size=10)
        for txt, width in cols:
            pdf.cell(width, 9, txt, border=1, align='C', fill=True)
        pdf.ln()

        pdf.set_font("Nanum", size=9)
        if not bu_df.empty:
            for _, row in bu_df.iterrows():
                pdf.cell(40, 9, str(row['장소']), border=1, align='C')
                pdf.cell(35, 9, str(row['시간']), border=1, align='C')
                pdf.cell(115, 9, " " + str(row['행사명']), border=1, align='L')
                pdf.cell(12, 9, str(row['인원']), border=1, align='C')
                pdf.cell(50, 9, str(row['부서']), border=1, align='C')
                pdf.cell(15, 9, str(row['상태']), border=1, align='C')
                pdf.ln()
        else:
            pdf.cell(267, 9, "대관 내역이 없습니다.", border=1, align='C')
            pdf.ln()
        pdf.ln(12)
    return bytes(pdf.output())

# 5. 메인 UI 및 다운로드 버튼 로직
st.sidebar.title("📅 조회 설정")
start_selected = st.sidebar.date_input("조회 시작일", value=now_today)
end_selected = st.sidebar.date_input("조회 종료일", value=now_today)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=BUILDING_ORDER)

all_df = get_data(start_selected, end_selected)
display_title = f"성의교정 대관 현황 ({start_selected})" if start_selected == end_selected else f"성의교정 대관 현황 ({start_selected} ~ {end_selected})"

if not all_df.empty:
    try:
        pdf_bytes = create_building_split_pdf(all_df, display_title, selected_bu)
        st.sidebar.download_button(
            label="📥 PDF 즉시 저장",
            data=pdf_bytes,
            file_name=f"rental_{start_selected}.pdf",
            mime="application/pdf"
        )
    except Exception as e:
        st.sidebar.error(f"PDF 처리 중 오류: {str(e)}")
else:
    st.sidebar.info("조회된 내역이 없습니다.")

# 6. 웹 화면 출력
st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)

if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            rows_html = "".join([f"<tr><td>{r['날짜']}</td><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in bu_df.iterrows()])
            st.markdown(f'<div class="table-container"><table><thead><tr><th>날짜</th><th>장소</th><th>시간</th><th>행사명</th><th>인원</th><th>부서</th><th>상태</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="no-data">해당 건물에 조회된 대관 내역이 없습니다.</div>', unsafe_allow_html=True)
else:
    st.info("조회된 기간에 전체 대관 내역이 없습니다.")
