import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io
import csv

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 대관 현황 추출", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# --- CSS 스타일 (UI 개선) ---
st.markdown("""
    <style>
    .main-title { font-size: 24px; font-weight: bold; color: #1E3A5F; text-align: center; margin-bottom: 20px; }
    .stDownloadButton { width: 100%; }
    .info-text { font-size: 13px; color: #666; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 공통 함수: 조(Shift) 계산 ---
def get_shift(target_date):
    base_date = date(2026, 3, 13) # C조 기준일
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

# --- 1. 편집된 엑셀(XLSX) 생성 함수 ---
def create_styled_excel(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('성의교정대관현황')
        
        # 서식 설정
        t_fmt = workbook.add_format({'bold': True, 'size': 16, 'align': 'center', 'valign': 'vcenter'})
        d_fmt = workbook.add_format({'bold': True, 'bg_color': '#343a40', 'font_color': 'white', 'align': 'center', 'border': 1})
        b_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'border': 1})
        h_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'border': 1})
        c_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True})

        widths = [25, 15, 40, 20, 10, 10]
        for i, w in enumerate(widths): worksheet.set_column(i, i, w)
        
        worksheet.merge_range('A1:F1', "성의교정 대관 현황 (보고용)", t_fmt)
        
        row = 2
        for d_str in sorted(df['full_date'].unique()):
            target_dt = datetime.strptime(d_str, '%Y-%m-%d').date()
            worksheet.merge_range(row, 0, row, 5, f"📅 {d_str} | {get_shift(target_dt)}", d_fmt); row += 1
            
            for bu in selected_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", b_fmt); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']): worksheet.write(row, col, h, h_fmt)
                row += 1
                for _, r in b_df.sort_values('시간').iterrows():
                    worksheet.set_row(row, 35)
                    worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], c_fmt)
                    row += 1
                row += 1
    return output.getvalue()

# --- 2. 데이터 중심 CSV 생성 함수 (구글 시트용) ---
def create_data_csv(df):
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(['날짜', '요일', '근무조', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태'])
    
    for _, r in df.sort_values(['full_date', '건물명', '시간']).iterrows():
        t_date = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
        day_name = ["월", "화", "수", "목", "금", "토", "일"][t_date.weekday()]
        writer.writerow([
            r['full_date'], day_name, get_shift(t_date),
            r['건물명'], r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']
        ])
    return output.getvalue().encode('utf-8-sig')

# --- 데이터 로드 함수 ---
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
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    rows.append({
                        'full_date': curr.strftime('%Y-%m-%d'), 
                        '건물명': str(item.get('buNm', '')).strip(), 
                        '장소': item.get('placeNm', '') or '-', 
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}", 
                        '행사명': item.get('eventNm', '') or '-', 
                        '부서': item.get('mgDeptNm', '') or '-', 
                        '인원': str(item.get('peopleCount', '0')), 
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# --- 메인 화면 구성 ---
st.markdown('<div class="main-title">🏫 성의교정 대관 데이터 관리 도구</div>', unsafe_allow_html=True)

BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.sidebar:
    st.header("🔍 조회 설정")
    s_date = st.date_input("시작일", value=now_today)
    e_date = st.date_input("종료일", value=s_date)
    sel_bu = st.multiselect("건물 선택", options=BUILDING_ORDER, default=BUILDING_ORDER)

df = get_data(s_date, e_date)

if not df.empty:
    st.success(f"✅ {s_date} ~ {e_date} 기간 동안 총 {len(df)}건의 데이터를 확인했습니다.")
    
    # 두 개의 컬럼으로 버튼 배치
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 보고용 엑셀")
        st.markdown('<p class="info-text">색상, 테두리, 레이아웃이 적용되어 그대로 출력하기 좋습니다.</p>', unsafe_allow_html=True)
        st.download_button(
            label="📥 편집된 XLSX 다운로드",
            data=create_styled_excel(df, sel_bu),
            file_name=f"성의교정_대관보고서_{s_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    with col2:
        st.subheader("📊 구글 시트용 CSV")
        st.markdown('<p class="info-text">필터링과 업로드에 최적화된 데이터 형식입니다.</p>', unsafe_allow_html=True)
        st.download_button(
            label="📥 데이터용 CSV 다운로드",
            data=create_data_csv(df),
            file_name=f"성의교정_데이터업로드_{s_date}.csv",
            mime="text/csv"
        )

    st.divider()
    st.dataframe(df.sort_values(['full_date', '시간']), use_container_width=True)
else:
    st.info("선택한 날짜에 조회된 데이터가 없습니다.")
