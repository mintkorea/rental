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

# 건물 리스트 순서 고정 (요청하신 옴니버스파크 의대/간호대 포함)
BUILDING_ORDER = [
    "성의회관", "의생명산업연구원", "옴니버스 파크", 
    "옴니버스파크 의과대학", "옴니버스파크 간호대학", 
    "대학본관", "서울성모별관"
]

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
</style>
""", unsafe_allow_html=True)

# 3. 데이터 로드 및 요일 필터링 (조회 누락 방지 로직 보강)
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
            # 요일 필터 데이터 처리
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_weekdays = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip()]
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # 기간 내 모든 날짜 순회
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    curr_weekday = curr.weekday() + 1 # 1:월 ~ 7:일
                    if not allowed_weekdays or curr_weekday in allowed_weekdays:
                        rows.append({
                            '날짜': curr.strftime('%m-%d'),
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
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
            return df.sort_values(by=['full_date', '건물명', '시간'])
        return df
    except Exception:
        return pd.DataFrame()

# 4. PDF 생성: 건물별 -> 날짜별 표 분리 (요청 사항 반영)
def create_split_pdf(df, title_text, selected_buildings):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_font("Nanum", "", "NanumGothic.ttf", uni=True)
    pdf.add_page()
    
    # 상단 타이틀
    pdf.set_font("Nanum", size=16)
    pdf.cell(0, 15, title_text, ln=True, align='C')
    pdf.ln(5)

    for bu in selected_buildings:
        bu_df = df[df['건물명'] == bu]
        
        # 건물 섹션 (■ 건물명)
        pdf.set_font("Nanum", size=13)
        pdf.set_text_color(46, 80, 119)
        pdf.cell(0, 10, f"■ {bu}", ln=True, align='L')
        pdf.set_text_color(0, 0, 0)
        
        if not bu_df.empty:
            # 날짜별로 그룹화하여 별도의 표 생성
            for date_val in sorted(bu_df['full_date'].unique()):
                day_df = bu_df[bu_df['full_date'] == date_val]
                weekday_str = day_df.iloc[0]['요일']
                
                # 부제목: 날짜(요일) 대관 현황
                pdf.set_font("Nanum", size=10)
                pdf.cell(0, 8, f"   ▶ {date_val}({weekday_str}) 대관 현황", ln=True, align='L')
                
                # 표 헤더
                cols = [("장소", 40), ("시간", 35), ("행사명", 115), ("인원", 12), ("부서", 50), ("상태", 15)]
                pdf.set_fill_color(240, 240, 240)
                for txt, width in cols:
                    pdf.cell(width, 8, txt, border=1, align='C', fill=True)
                pdf.ln()

                # 표 내용
                pdf.set_font("Nanum", size=9)
                for _, row in day_df.iterrows():
                    pdf.cell(40, 8, str(row['장소']), border=1, align='C')
                    pdf.cell(35, 8, str(row['시간']), border=1, align='C')
                    pdf.cell(115, 8, " " + str(row['행사명']), border=1, align='L')
                    pdf.cell(12, 8, str(row['인원']), border=1, align='C')
                    pdf.cell(50, 8, str(row['부서']), border=1, align='C')
                    pdf.cell(15, 8, str(row['상태']), border=1, align='C')
                    pdf.ln()
                pdf.ln(5) # 날짜 표 간격
        else:
            pdf.set_font("Nanum", size=9)
            pdf.cell(267, 8, "   해당 기간 대관 내역이 없습니다.", border=1, align='L')
            pdf.ln()
        pdf.ln(5) # 건물 간격
        
    # AttributeError 방지를 위한 바이트 변환
    return pdf.output(dest='S').encode('latin-1', 'replace')

# 5. 메인 UI
st.sidebar.title("📅 대관 조회 설정")
start_selected = st.sidebar.date_input("조회 시작일", value=now_today)
end_selected = st.sidebar.date_input("조회 종료일", value=now_today)

# 건물 필터 및 디폴트 설정 (성의회관, 의생명산업연구원)
selected_bu = st.sidebar.multiselect(
    "건물 필터", 
    options=BUILDING_ORDER, 
    default=["성의회관", "의생명산업연구원"]
)

all_df = get_data(start_selected, end_selected)
display_title = f"성의교정 대관 현황 ({start_selected} ~ {end_selected})" if start_selected != end_selected else f"성의교정 대관 현황 ({start_selected})"

# PDF 생성 및 다운로드
if not all_df.empty:
    try:
        pdf_bytes = create_split_pdf(all_df, display_title, selected_bu)
        st.sidebar.download_button(
            label="📥 PDF 생성 및 저장", 
            data=pdf_bytes, 
            file_name=f"rental_{start_selected}.pdf", 
            mime="application/pdf"
        )
    except Exception as e:
        st.sidebar.error(f"PDF 생성 오류: {e}")
else:
    st.sidebar.info("조회된 내역이 없습니다.")

st.markdown(f'<div class="main-title">🏫 {display_title}</div>', unsafe_allow_html=True)
if not all_df.empty:
    for bu in selected_bu:
        bu_df = all_df[all_df['건물명'] == bu]
        st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
        if not bu_df.empty:
            rows_html = "".join([f"<tr><td>{r['날짜']}({r['요일']})</td><td>{r['장소']}</td><td>{r['시간']}</td><td style='text-align:left;'>{r['행사명']}</td><td>{r['인원']}</td><td>{r['부서']}</td><td>{r['상태']}</td></tr>" for _, r in bu_df.iterrows()])
            st.markdown(f'<div class="table-container"><table><thead><tr><th>날짜</th><th>장소</th><th>시간</th><th>행사명</th><th>인원</th><th>부서</th><th>상태</th></tr></thead><tbody>{rows_html}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.info("해당 건물에 조회된 내역이 없습니다.")
else:
    st.info("선택한 기간 및 건물에 대한 조회 내역이 없습니다.")
