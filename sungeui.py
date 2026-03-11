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
            
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # allowDay 처리: "1,2,3" 형태를 리스트로 변환 (1:월, ..., 7:일)
            # 만약 allowDay가 없거나 비어있으면 모든 요일 허용으로 간주하거나 
            # 데이터 구조에 따라 적절히 처리합니다.
            allowed_days = str(item.get('allowDay', '')).split(',')
            allowed_days = [d.strip() for d in allowed_days if d.strip()]
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    # 요일 체크 로직 추가 (isoweekday: 월=1, ..., 일=7)
                    curr_weekday = str(curr.isoweekday())
                    
                    # 기간 대관인데 특정 요일만 지정된 경우 필터링
                    # (단일 날짜 대관은 s_dt == e_dt 이므로 요일과 상관없이 포함)
                    is_allowed = True
                    if s_dt != e_dt and allowed_days:
                        if curr_weekday not in allowed_days:
                            is_allowed = False
                    
                    if is_allowed:
                        rows.append({
                            '날짜': curr.strftime('%m-%d'),
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
            return df.sort_values(by=['날짜', '건물명', '시간'])
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()
