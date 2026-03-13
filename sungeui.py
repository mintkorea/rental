import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 초기화 (반드시 최상단 배치)
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

# 2. 전역 스타일 설정 (PC/모바일 대응 반응형 디자인)
st.markdown("""
<style>
    .main-title { font-size: 26px !important; font-weight: 800; color: #1E3A5F; border-bottom: 3px solid #1E3A5F; padding-bottom: 10px; margin-bottom: 25px; }
    .date-header { background-color: #f1f3f5; padding: 15px; border-radius: 8px; border-left: 8px solid #1E3A5F; margin-top: 40px; margin-bottom: 10px; }
    .building-label { color: #2E5077; font-size: 18px; font-weight: 700; margin-top: 25px; margin-bottom: 12px; display: flex; align-items: center; }
    
    /* [핵심] 모바일 찌그러짐 방지 및 PC 가변 너비 설정 */
    .table-container { width: 100%; overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
    .res-table { 
        width: 100%; 
        min-width: 850px; /* 모바일에서 셀이 좁아지는 것을 방지하는 방어선 */
        border-collapse: collapse; 
        font-size: 14px; 
        table-layout: fixed; 
        background-color: white;
    }
    .res-table th { background-color: #f8f9fa; font-weight: bold; border: 1px solid #dee2e6; padding: 12px 8px; text-align: center; }
    .res-table td { border: 1px solid #dee2e6; padding: 10px 8px; text-align: center; vertical-align: middle; word-break: break-all; }
    
    .scroll-info { text-align: right; color: #999; font-size: 11px; margin-top: 5px; margin-bottom: 15px; }
    
    /* 사이드바 너비 조정 */
    section[data-testid="stSidebar"] { width: 300px !important; }
</style>
""", unsafe_allow_html=True)

# 3. 주요 로직 함수
def get_shift(target_date):
    """3교대 근무조 계산 (기준일: 2026-03-13)"""
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3]}조"

@st.cache_data(ttl=60)
def fetch_rental_data(start_date, end_date):
    """웹사이트에서 실시간 대관 데이터를 가져와 데이터프레임으로 변환"""
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw_data = res.json().get('res', [])
        processed_rows = []
        for item in raw_data:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    processed_rows.append({
                        'full_date': curr.strftime('%Y-%m-%d'),
                        '요일': ['','월','화','수','목','금','토','일'][curr.isoweekday()],
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '인원': str(item.get('peopleCount', '0')),
                        '부스': str(item.get('boothCount', '0')),
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(processed_rows)
    except:
        return pd.DataFrame()

def create_excel(df, selected_buildings):
    """보고서용 엑셀 파일 생성"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        ws = workbook.add_worksheet('대관현황')
        # 인쇄 설정
        ws.set_landscape()
        ws.set_paper(9)
        ws.fit_to_pages(1, 0)
        
        # 스타일
        h_style = workbook.add_format({'bold': True, 'bg_color': '#D9E1F2', 'border': 1, 'align': 'center'})
        c_style = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True})
        
        curr = 0
        for d_str in sorted(df['full_date'].unique()):
            ws.write(curr, 0, f"📅 날짜: {d_str}", workbook.add_format({'bold': True, 'font_size': 14}))
            curr += 1
            for b in selected_buildings:
                b_df = df[(df['full_date'] == d_str) & (df['건물명'] == b)]
                ws.write(curr, 0, f"📍 {b}", workbook.add_format({'bold': True, 'bg_color': '#F2F2F2'}))
                curr += 1
                b_df[['장소','시간','행사명','부서','인원','부스','상태']].to_excel(writer, sheet_name='대관현황', startrow=curr, index=False)
                curr += len(b_df) + 2
    return output.getvalue()

# 4. 사이드바 UI
BUILDING_LIST = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

with st.sidebar:
    st.title("⚙️ 설정")
    s_date = st.date_input("조회 시작일", value=now_today)
    e_date = st.date_input("조회 종료일", value=s_date)
    sel_bu = st.multiselect("대상 건물 선택", options=BUILDING_LIST, default=["성의회관", "의생명산업연구원"])

# 5. 메인 화면 출력
st.markdown('<div class="main-title">🏫 성의교정 대관 현황 실시간 조회</div>', unsafe_allow_html=True)
data_df = fetch_rental_data(s_date, e_date)

if not data_df.empty:
    # 엑셀 다운로드 버튼
    excel_file = create_excel(data_df, sel_bu)
    st.sidebar.download_button("📥 엑셀 보고서 다운로드", data=excel_file, file_name=f"대관현황_{s_date}.xlsx", use_container_width=True)

    for d_val in sorted(data_df['full_date'].unique()):
        d_obj = datetime.strptime(d_val, '%Y-%m-%d').date()
        st.markdown(f'<div class="date-header"><h3>📅 {d_val} ({data_df[data_df["full_date"]==d_val]["요일"].iloc[0]}) | 근무조: {get_shift(d_obj)}</h3></div>', unsafe_allow_html=True)
        
        for b_name in sel_bu:
            display_df = data_df[(data_df['full_date'] == d_val) & (data_df['건물명'] == b_name)]
            st.markdown(f'<div class="building-label">🏢 {b_name}</div>', unsafe_allow_html=True)
            
            if not display_df.empty:
                rows_html = ""
                for _, r in display_df.iterrows():
                    rows_html += f"""
                    <tr>
                        <td style="width:12%;">{r['장소']}</td>
                        <td style="width:13%;">{r['시간']}</td>
                        <td style="width:35%; text-align:left;">{r['행사명']}</td>
                        <td style="width:15%;">{r['부서']}</td>
                        <td style="width:8%;">{r['인원']}</td>
                        <td style="width:8%;">{r['부스']}</td>
                        <td style="width:9%;">{r['상태']}</td>
                    </tr>"""
                
                st.markdown(f"""
                <div class="table-container">
                    <table class="res-table">
                        <thead>
                            <tr>
                                <th>장소</th><th>시간</th><th>행사명</th><th>부서</th><th>인원</th><th>부스</th><th>상태</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                </div>
                <div class="scroll-info">↔ 모바일은 옆으로 밀어서 확인하세요</div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"{b_name}에 예정된 대관 내역이 없습니다.")
else:
    st.warning("선택하신 기간에 데이터가 없거나 불러올 수 없습니다.")
