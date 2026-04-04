import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from io import BytesIO

# 1. 페이지 설정 및 디자인 (기존 모바일 레이아웃 유지)
st.set_page_config(page_title="성의교정 대관 관리 시스템", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# CSS 스타일 생략 (기존과 동일)
st.markdown("""<style>...</style>""", unsafe_allow_html=True)

# --- 공통 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            is_p = (item['startDt'] != item['endDt'])
            p_rng = f"{item['startDt']}~{item['endDt']}"
            d_nms = get_weekday_names(item.get('allowDay', ''))
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        status_val = '확정' if item.get('status') == 'Y' else '대기'
                        rows.append({
                            '날짜': curr.strftime('%Y-%m-%d'), '요일': "월화수목금토일"[curr.weekday()],
                            '근무조': get_shift(curr), '유형': "기간" if is_p else "당일",
                            '대관기간': p_rng if is_p else curr.strftime('%Y-%m-%d'), 
                            '해당요일': d_nms if is_p else "월화수목금토일"[curr.weekday()],
                            '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', 
                            '인원': str(item.get('peopleCount', '0')), '상태': status_val
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 추출 실패: {e}")
        return pd.DataFrame()

# --- 🎨 전문가용 엑셀 서식 적용 함수 ---
def to_excel_with_style(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관명단')
        workbook  = writer.book
        worksheet = writer.sheets['대관명단']

        # 서식 정의
        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        cell_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter'})
        date_fmt = workbook.add_format({'border': 1, 'align': 'center', 'num_format': 'yyyy-mm-dd'})

        # 헤더 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_fmt)
        
        # 열 너비 및 데이터 서식 자동 적용
        worksheet.set_column('A:A', 12, date_fmt) # 날짜
        worksheet.set_column('B:C', 8, cell_fmt)  # 요일, 근무조
        worksheet.set_column('D:F', 15, cell_fmt) # 유형, 기간, 요일
        worksheet.set_column('G:H', 20, cell_fmt) # 건물, 장소
        worksheet.set_column('I:I', 15, cell_fmt) # 시간
        worksheet.set_column('J:K', 35, cell_fmt) # 행사명, 부서 (넓게)
        worksheet.set_column('L:M', 8, cell_fmt)  # 인원, 상태

    return output.getvalue()

# --- 구글 시트 동기화 (기존 로직 유지) ---
def update_google_sheet(df):
    # (생략: 기존과 동일하게 O1 셀에 업데이트 시간 기록)
    pass

# --- UI 레이아웃 ---
st.markdown('<div class="main-title">🏫 성의교정 대관 관리 시스템</div>', unsafe_allow_html=True)

with st.expander("🔍 조회 및 엑셀 보고서 출력", expanded=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        s_date = st.date_input("조회 시작", value=now_today)
        e_date = st.date_input("조회 종료", value=s_date + timedelta(days=7))
        sel_bu = st.multiselect("건물 선택", options=["성의회관", "의생명산업연구원", "옴니버스 파크"], default=["성의회관", "의생명산업연구원", "옴니버스 파크"])
    
    df_current = get_data(s_date, e_date)
    
    with c2:
        if not df_current.empty:
            # 서식이 적용된 엑셀 파일 생성
            excel_bin = to_excel_with_style(df_current)
            st.download_button(
                label="📥 서식 포함 엑셀 다운로드",
                data=excel_bin,
                file_name=f"대관보고서_{s_date}_{e_date}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        # 동기화 버튼 (생략)

# 카드형 레이아웃 표시
if not df_current.empty:
    # (생략: 기존의 모바일 카드 레이아웃 코드)
    pass
