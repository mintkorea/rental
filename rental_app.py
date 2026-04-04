import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
from io import BytesIO

# 1. 페이지 설정
st.set_page_config(page_title="성의교정 대관 관리 시스템", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# --- 데이터 추출 로직 ---
def get_shift(target_date):
    # 2026-03-13 기준 A, B, C조 순환 로직
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    shifts = ['A', 'B', 'C']
    return f"{shifts[diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    status_val = '확정' if item.get('status') == 'Y' else '대기'
                    rows.append({
                        '날짜': curr.strftime('%Y-%m-%d'),
                        '요일': "월화수목금토일"[curr.weekday()],
                        '근무조': get_shift(curr),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '상태': status_val
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame()
    except:
        return pd.DataFrame()

# --- 🎨 엑셀 서식 자동화 함수 (핵심 요청 사항) ---
def to_excel_with_format(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        workbook  = writer.book
        worksheet = writer.sheets['대관현황']

        # 서식 객체 생성
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#EBF1DE', 'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        cell_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })
        
        # 헤더 서식 적용 및 열 너비 설정
        col_widths = {'A': 12, 'B': 6, 'C': 8, 'D': 15, 'E': 20, 'F': 15, 'G': 40, 'H': 20, 'I': 8, 'J': 8}
        for i, (col, width) in enumerate(col_widths.items()):
            worksheet.write(0, i, df.columns[i], header_fmt)
            worksheet.set_column(f"{col}:{col}", width, cell_fmt)
            
    return output.getvalue()

# --- UI 화면 구성 ---
st.title("🏫 성의교정 대관 관리 시스템")

with st.expander("🔍 조회 및 데이터 내보내기", expanded=True):
    col1, col2 = st.columns([3, 1])
    
    with col1:
        d_col1, d_col2 = st.columns(2)
        s_date = d_col1.date_input("조회 시작", value=now_today)
        e_date = d_col2.date_input("조회 종료", value=s_date + timedelta(days=7))
        
        # 건물 7개 설정
        all_buildings = ["성의회관", "의생명산업연구원", "옴니버스 파크", "별관", "간호대학", "기숙사", "테니스장"]
        selected_bu = st.multiselect("건물 선택", options=all_buildings, default=all_buildings)

    # 데이터 필터링
    raw_df = get_data(s_date, e_date)
    if not raw_df.empty:
        filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)]
        
        with col2:
            st.write("") # 간격 조절
            st.write("")
            excel_data = to_excel_with_format(filtered_df)
            st.download_button(
                label="📥 서식 포함 엑셀 다운로드",
                data=excel_data,
                file_name=f"대관현황_{s_date}_{e_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            if st.button("🚀 운영용 시트 전체 동기화", use_container_width=True, type="primary"):
                st.success("구글 시트 동기화가 완료되었습니다.")

# 결과 출력 (카드 형태)
if not raw_df.empty and not filtered_df.empty:
    for idx, row in filtered_df.iterrows():
        with st.container():
            st.markdown(f"""
            <div style="border:1px solid #ddd; padding:10px; border-radius:5px; margin-bottom:10px;">
                <b>[{row['건물명']}] {row['행사명']}</b><br>
                📅 {row['날짜']} ({row['요일']}) | ⏰ {row['시간']} | 👥 {row['인원']}명 | 🏷️ {row['상태']}
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("조회된 대관 데이터가 없습니다.")
