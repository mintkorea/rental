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

# --- 공통 함수 ---
def get_weekday_names(codes):
    days = {"1":"월", "2":"화", "3":"수", "4":"목", "5":"금", "6":"토", "7":"일"}
    if not codes: return ""
    return ",".join([days.get(c.strip(), "") for c in str(codes).split(",") if c.strip() in days])

def get_shift(target_date):
    # C-조 교대 로직
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
                        # '상태' 값 추출 (Y면 확정, 아니면 대기)
                        status_val = '확정' if item.get('status') == 'Y' else '대기'
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'), 'is_period': is_p, 'period_range': p_rng, 'allowed_days': d_nms,
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

# --- 구글 시트 업데이트 함수 (상태 누락 방지 및 보정) ---
def update_google_sheet(df):
    if df.empty: return False
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_info, scope)
        client = gspread.authorize(creds)
        
        SHEET_KEY = "13P49JFl63lgA7psgGr8QYgutKwcPMIyq0_jjUcc8Fa0"
        sh = client.open_by_key(SHEET_KEY)
        
        try:
            sheet = sh.worksheet("운영용")
        except:
            st.error("'운영용' 탭을 찾을 수 없습니다.")
            return False
            
        header = ['날짜', '요일', '근무조', '유형', '대관기간', '해당요일', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태']
        
        # 1. 기존 데이터 읽기
        existing_raw = sheet.get_all_values()
        if len(existing_raw) > 1:
            existing_df = pd.DataFrame(existing_raw[1:], columns=existing_raw[0])
            existing_df = existing_df.reindex(columns=header).fillna("")
        else:
            existing_df = pd.DataFrame(columns=header)

        # 2. 신규 데이터 변환
        new_rows = []
        for _, r in df.iterrows():
            t_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
            day_name = ["월", "화", "수", "목", "금", "토", "일"][t_dt.weekday()]
            new_rows.append({
                '날짜': r['full_date'], '요일': day_name, '근무조': get_shift(t_dt),
                '유형': "기간" if r['is_period'] else "당일",
                '대관기간': r['period_range'] if r['is_period'] else r['full_date'],
                '해당요일': r['allowed_days'] if r['is_period'] else day_name,
                '건물명': r['건물명'], '장소': r['장소'], '시간': r['시간'],
                '행사명': r['행사명'], '부서': r['부서'], '인원': r['인원'], '상태': r['상태']
            })
        new_df = pd.DataFrame(new_rows)

        # 3. 합치기 및 중복 제거 (상태 누락 보정을 위해 새 데이터를 우선순위로 둠)
        # keep='last' 이므로 나중에 추가되는 new_df(상태값이 있는 데이터)가 기존 데이터를 덮어씁니다.
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(
            subset=['날짜', '시간', '장소', '행사명'], keep='last'
        )
        combined_df = combined_df.sort_values(by=['날짜', '시간'])

        # 4. 시트 업데이트
        final_values = [header] + combined_df.values.tolist()
        if len(final_values) > sheet.row_count:
            sheet.add_rows(len(final_values) - sheet.row_count + 20)
            
        sheet.clear()
        sheet.update('A1', final_values)
        sheet.update('L1', [[f"최종 업데이트: {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}"]])
        return True
    except Exception as e:
        st.error(f"운영용 전송 오류: {e}")
        return False

# --- 메인 실행 ---
st.title("🏫 성의교정 대관 관리 도구")

with st.container():
    st.info("기존 누락된 '상태' 값을 보정하려면 조회 시작일을 과거 날짜(예: 1월 1일)로 설정하고 전송하세요.")
    c1, c2 = st.columns([2, 1])
    with c1:
        # 상태 보정을 위해 시작일을 1월 1일로 기본 설정해 두었습니다.
        sel_range = st.date_input("조회 및 보정 기간", [date(2026, 1, 1), date(2026, 12, 31)])
    with c2:
        if st.button("🚀 운영용 시트 데이터 보정 및 전송", use_container_width=True, type="primary"):
            df_all = get_data(sel_range[0], sel_range[1])
            if update_google_sheet(df_all):
                st.success("데이터 보정 및 업데이트 완료!")
