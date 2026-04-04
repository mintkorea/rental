# 1. 데이터 가져오기 로직 수정 (유형 판별 추가)
@st.cache_data(ttl=60)
def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        raw, rows = res.json().get('res', []), []
        for item in raw:
            if not item.get('startDt'): continue
            
            s_dt_str = item['startDt']
            e_dt_str = item['endDt']
            s_dt = datetime.strptime(s_dt_str, '%Y-%m-%d').date()
            e_dt = datetime.strptime(e_dt_str, '%Y-%m-%d').date()
            
            # [수정] 당일대관과 기간대관 판별 로직
            # 시작일과 종료일이 같으면 '당일', 다르면 '기간'
            rent_type = "당일" if s_dt_str == e_dt_str else "기간"
            
            allowed = [d.strip() for d in str(item.get('allowDay', '')).split(",") if d.strip().isdigit()]
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    if not allowed or str(curr.isoweekday()) in allowed:
                        rows.append({
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '유형': rent_type,  # CSV에 유형 추가
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

# 2. CSV 생성 함수 수정 (모바일 포털 호환용)
def create_csv(df):
    output = io.StringIO()
    # 모바일 버전 JS가 읽기 편하도록 컬럼 순서 조정 및 '유형' 포함
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(['날짜', '요일', '근무조', '유형', '건물명', '장소', '시간', '행사명', '부서', '인원', '상태'])
    
    for _, r in df.sort_values(['full_date', '유형', '시간']).iterrows():
        target_dt = datetime.strptime(r['full_date'], '%Y-%m-%d').date()
        day_name = ["월", "화", "수", "목", "금", "토", "일"][target_dt.weekday()]
        writer.writerow([
            r['full_date'], 
            day_name, 
            get_shift(target_dt),
            r['유형'], # 당일 vs 기간
            r['건물명'], 
            r['장소'], 
            r['시간'], 
            r['행사명'], 
            r['부서'], 
            r['인원'], 
            r['상태']
        ])
    return output.getvalue().encode('utf-8-sig')
