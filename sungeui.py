import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 대관 관리 시스템", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# CSS 생략 (기존과 동일)
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
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'), 'is_period': is_p, 'period_range': p_rng, 'allowed_days': d_nms,
                            '건물명': str(item.get('buNm', '')).strip(), '장소': item.get('placeNm', '') or '-', 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', '') or '-', '부서': item.get('mgDeptNm', '') or '-', 
                            '인원': str(item.get('peopleCount', '0')), '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows).drop_duplicates() if rows else pd.DataFrame()
    except Exception as e:
        st.error(f"데이터 추출 실패: {e}")
        return pd.DataFrame()

# --- 구글 시트 업데이트 함수 (운영용 시트 명시) ---
def update_google_sheet(df):
    if df.empty: return False
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        SHEET_KEY = "13P49JFl63lgA7psgGr8QYgutKwcPMIyq0_jjUcc8Fa0"
        sh = client.open_by_key(SHEET_KEY)
        
        # [수정] 첫 번째 탭이 아니라 '운영용'이라는 이름의 시트를 찾습니다.
        try:
            sheet = sh.worksheet("운영용")
        except:
            sheet = sh.get_worksheet(0) # '운영용' 탭이 없으면 첫 번째 탭 사용
        
        header = ['날짜', '요일', '근무조', '유형', '대관기간', '해당요일', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태']
        
        # 기존 데이터 읽기 및 구조 맞추기
        existing_raw = sheet.get_all_values()
        if len(existing_raw) > 1:
            existing_df = pd.DataFrame(existing_raw[1:], columns=existing_raw[0])
            for col in header:
                if col not in existing_df.columns: existing_df[col] = ""
            existing_df = existing_df[header]
        else:
            existing_df = pd.DataFrame(columns=header)

        # 신규 데이터 생성
        new_rows = []
        for _, r in df.iterrows():
            t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
            new_rows.append([
                r['full_date'], ["월", "화", "수", "목", "금", "토", "일"][t_dt.weekday()], get_shift(t_dt),
                "기간" if r['is_period'] else "당일", r['period_range'] if r['is_period'] else r['full_date'],
                r['allowed_days'] if r['is_period'] else ["월", "화", "수", "목", "금", "토", "일"][t_dt.weekday()],
                r['건물명'], r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']
            ])
        new_df = pd.DataFrame(new_rows, columns=header)

        # 병합 및 정렬 (중복 제거 기준: 날짜, 시간, 장소, 행사명)
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(
            subset=['날짜', '시간', '장소', '행사명'], keep='last'
        )
        combined_df = combined_df.sort_values(by=['날짜', '시간'])

        # 저장
        final_values = [header] + combined_df.values.tolist()
        sheet.clear()
        sheet.update('A1', final_values)
        sheet.update('M1', [[datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')]]) # 업데이트 시각
        return True
    except Exception as e:
        st.error(f"구글 시트 전송 오류: {e}")
        return False

# --- 메인 실행 (수동 업데이트 버튼) ---
st.markdown('<div class="main-title">🏫 성의교정 대관 관리 도구</div>', unsafe_allow_html=True)

with st.expander("🔍 데이터 동기화", expanded=True):
    c1, c2 = st.columns([2, 1])
    with c1:
        date_range = st.date_input("업데이트 기간", [now_today, now_today + timedelta(days=30)])
    with c2:
        if st.button("🚀 운영용 시트로 전송", use_container_width=True, type="primary"):
            if len(date_range) == 2:
                with st.spinner("데이터를 추출하여 시트로 누적 중..."):
                    df_to_save = get_data(date_range[0], date_range[1])
                    if update_google_sheet(df_to_save):
                        st.success("운영용 시트 업데이트 완료!")
