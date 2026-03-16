import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 디자인 및 홈페이지 텍스트 제어 (가이드라인 반영)
st.set_page_config(page_title="성의교정 대관 현황", page_icon="🏫", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none; }
    header { visibility: hidden; }
    .block-container { padding: 1.5rem 2rem !important; max-width: 1200px; margin: 0 auto; }
    .main-title { font-size: 26px; font-weight: 800; color: #1E3A5F; text-align: center; margin-bottom: 25px; }
    
    .date-bar { background-color: #3d444b; color: white; padding: 10px; border-radius: 6px; text-align: center; font-weight: bold; margin-top: 35px; margin-bottom: 12px; }
    .bu-header { font-size: 17px; font-weight: bold; color: #1E3A5F; margin: 20px 0 10px 0; border-left: 5px solid #1E3A5F; padding-left: 12px; }
    
    /* 홈페이지 셀/카드: 2행 제한 및 폰트 자동 축소 */
    .mobile-card { background: white; border: 1px solid #eef2f6; border-radius: 8px; padding: 15px; margin-bottom: 10px; }
    .card-row-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .card-loc { font-size: 15px; font-weight: 800; color: #1E3A5F; }
    .card-time { font-size: 14px; font-weight: 700; color: #ff4b4b; }
    
    .card-event { 
        font-size: 14px; 
        font-weight: 700; 
        color: #333; 
        margin-top: 5px;
        display: -webkit-box;
        -webkit-line-clamp: 2; /* 최대 2행 제한 */
        -webkit-box-orient: vertical;
        overflow: hidden;
        line-height: 1.3;
        word-break: break-all;
        /* 긴 텍스트의 경우 브라우저가 가능한 범위 내에서 폰트 크기 미세 조정 */
    }
    .card-info { font-size: 13px; color: #777; margin-top: 3px; }
    </style>
""", unsafe_allow_html=True)

# 2. 엑셀 생성 함수 (행 높이 35 및 열 너비 가이드라인 적용)
def create_excel_report(df, selected_bu):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        title_fmt = workbook.add_format({'bold': True, 'size': 16, 'align': 'center', 'valign': 'vcenter'})
        date_fmt = workbook.add_format({'bold': True, 'bg_color': '#3d444b', 'font_color': 'white', 'align': 'center', 'border': 1})
        bu_fmt = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'font_color': '#1E3A5F', 'align': 'left', 'border': 1})
        head_fmt = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'align': 'center', 'border': 1})
        cell_fmt = workbook.add_format({'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'font_size': 10})
        
        # 열 너비 가이드라인 적용
        worksheet.set_column('A:A', 25) # 장소
        worksheet.set_column('B:B', 15) # 시간
        worksheet.set_column('C:C', 40) # 행사명 (셀 넓이 기준 반영)
        worksheet.set_column('D:D', 20) # 부서
        worksheet.set_column('E:F', 10) # 인원, 상태
        
        worksheet.merge_range('A1:F1', "성의교정 대관 현황", title_fmt)
        
        row = 2
        for d_str in sorted(df['full_date'].unique()):
            worksheet.merge_range(row, 0, row, 5, f"📅 {d_str}", date_fmt); row += 1
            for bu in selected_bu:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu.replace(" ",""))]
                worksheet.merge_range(row, 0, row, 5, f"🏢 {bu} ({len(b_df)}건)", bu_fmt); row += 1
                for col, h in enumerate(['장소', '시간', '행사명', '부서', '인원', '상태']):
                    worksheet.write(row, col, h, head_fmt)
                row += 1
                if not b_df.empty:
                    for _, r in b_df.sort_values('시간').iterrows():
                        # 행 높이 35 고정
                        worksheet.set_row(row, 35)
                        worksheet.write_row(row, 0, [r['장소'], r['시간'], r['행사명'], r['부서'], r['인원'], r['상태']], cell_fmt)
                        row += 1
                else:
                    worksheet.set_row(row, 35)
                    worksheet.merge_range(row, 0, row, 5, "내역 없음", cell_fmt); row += 1
                row += 1
    return output.getvalue()

# 3. 데이터 로직 (검색 오류 해결 및 중복 제거)
@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"})
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s, e = datetime.strptime(item['startDt'], '%Y-%m-%d').date(), datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            curr = s
            while curr <= e:
                if s_date <= curr <= e_date:
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
        df = pd.DataFrame(rows)
        # 안전한 중복 제거 로직으로 복구
        return df.drop_duplicates().reset_index(drop=True) if not df.empty else df
    except: return pd.DataFrame()

# [이후 UI 출력 부분은 이전과 동일하게 유지됩니다]
