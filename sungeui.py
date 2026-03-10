import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
import pytz
import os
from fpdf import FPDF

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 한국 시간대 기준 오늘 날짜
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 폰트 자동 다운로드 (한글 PDF용)
@st.cache_data
def load_font():
    font_url = "https://github.com/google/fonts/raw/main/ofl/nanumgothic/NanumGothic-Regular.ttf"
    font_path = "NanumGothic.ttf"
    if not os.path.exists(font_path):
        try:
            res = requests.get(font_url)
            with open(font_path, "wb") as f:
                f.write(res.content)
        except:
            return None
    return font_path

# 3. CSS 설정: 이미지에서 발생한 시간 중복 노출 및 깨짐 현상 해결
st.markdown("""
<style>
    .stApp { background-color: white; }
    .main-title { font-size: 24px !important; font-weight: 800; color: #002D56; margin-bottom: 20px; }
    .building-header { font-size: 18px !important; font-weight: 700; color: #2E5077; margin-top: 30px; display: flex; align-items: center; }
    
    /* 테이블 레이아웃 복구 */
    .custom-table { width: 100% !important; border-collapse: collapse; table-layout: fixed !important; margin-bottom: 20px; border-top: 2px solid #444; }
    .custom-table th { background-color: #f8f9fa !important; color: #333 !important; font-size: 13px; padding: 10px 2px; border: 1px solid #dee2e6; }
    .custom-table td { border: 1px solid #dee2e6; padding: 8px 4px !important; font-size: 13px; vertical-align: middle; line-height: 1.4; text-align: center; }
    
    /* 시간 중복 노출 방지 클래스 */
    .pc-time { display: block !important; }
    .mobile-time { display: none !important; }

    @media (max-width: 768px) {
        .pc-time { display: none !important; }
        .mobile-time { display: block !important; font-size: 11px; font-weight: bold; }
        .custom-table td { font-size: 11px !important; }
    }
</style>
""", unsafe_allow_html=True)

# 4. 사이드바 필터
st.sidebar.header("🔍 대관 조회 필터")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=now_today)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
selected_bu = st.sidebar.multiselect("조회 건물", options=BUILDING_ORDER, default=BUILDING_ORDER)

# 5. 데이터 처리 (요일 필터링 및 정렬)
@st.cache_data(ttl=60)
def get_processed_data(s_date, e_date):
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
                    current_weekday = str(curr.weekday() + 1)
                    # 요일 필터: 당일 대관 혹은 지정된 요일에만 데이터 생성
                    if (item['startDt'] == item['endDt']) or (not allow_days) or (current_weekday in allow_days):
                        rows.append({
                            'raw_date': curr,
                            'raw_time': item.get('startTime', '00:00'),
                            '날짜': curr.strftime('%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''),
                            '시간': f"{item.get('startTime', '')} ~ {item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''),
                            '부서': item.get('mgDeptNm', ''),
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        df = pd.DataFrame(rows)
        # 날짜 -> 시간 -> 건물명 순으로 정렬
        return df.sort_values(by=['raw_date', 'raw_time', '건물명']) if not df.empty else df
    except: return pd.DataFrame()

all_df = get_processed_data(start_selected, end_selected)

# 6. 화면 출력 및 데이터 수집
date_range = f"{start_selected}" if start_selected == end_selected else f"{start_selected} ~ {end_selected}"
st.markdown(f'<div class="main-title">🏫 성의교정 대관 현황 ({date_range})</div>', unsafe_allow_html=True)

excel_data_list = []
for bu in selected_bu:
    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
    bu_df = all_df[all_df['건물명'].str.replace(" ","").str.contains(bu.replace(" ",""), na=False)] if not all_df.empty else pd.DataFrame()
    
    if not bu_df.empty:
        excel_data_list.append(bu_df)
        html = '<table class="custom-table"><thead><tr><th style="width:10%">날짜</th><th style="width:15%">시간</th><th style="width:15%">장소</th><th style="width:35%">행사명</th><th style="width:15%">부서</th><th style="width:10%">상태</th></tr></thead><tbody>'
        for _, r in bu_df.iterrows():
            st_t, en_t = r['시간'].split('~')[0].strip(), r['시간'].split('~')[1].strip()
            time_td = f'<div class="pc-time">{r["시간"]}</div><div class="mobile-time">{st_t}<br>~ {en_t}</div>'
            html += f'<tr><td>{r["날짜"]}</td><td>{time_td}</td><td>{r["장소"]}</td><td style="text-align:left; padding-left:8px;">{r["행사명"]}</td><td>{r["부서"]}</td><td>{r["상태"]}</td></tr>'
        html += '</tbody></table>'
        st.markdown(html, unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#999; font-size:12px; margin-left:10px;">내역 없음</p>', unsafe_allow_html=True)

# 7. PDF 및 엑셀 저장 버튼 (안전장치 강화)
if excel_data_list:
    final_df = pd.concat(excel_data_list).drop(columns=['raw_date', 'raw_time'])
    st.sidebar.markdown("---")
    
    # 엑셀 저장 (화면 순서와 일치)
    out_ex = BytesIO()
    with pd.ExcelWriter(out_ex, engine='openpyxl') as writer:
        final_df.to_excel(writer, index=False)
    st.sidebar.download_button("📥 검색 결과 엑셀 저장", out_ex.getvalue(), f"rental_{start_selected}.xlsx")
    
    # PDF 저장 (한글 폰트 적용)
    font_p = load_font()
    if font_p:
        try:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            pdf.add_font("Nanum", "", font_p)
            pdf.set_font("Nanum", size=10)
            pdf.add_page()
            pdf.cell(0, 10, f"성의교정 대관 현황 ({date_range})", ln=True, align='C')
            pdf.ln(5)
            # PDF 테이블 생성 로직...
            pdf_bytes = pdf.output()
            st.sidebar.download_button("📄 검색 결과 PDF 저장", bytes(pdf_bytes), f"rental_{start_selected}.pdf", "application/pdf")
        except Exception as e:
            st.sidebar.error("PDF 생성 중 오류가 발생했습니다. (엑셀 저장을 권장합니다)")
    else:
        st.sidebar.warning("서버 폰트 로드 중... 잠시 후 시도하거나 엑셀을 이용해 주세요.")
