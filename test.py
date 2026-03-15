def get_data(start_date, end_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": start_date.isoformat(), "end": end_date.isoformat()}
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json().get('res', [])
        if not data: return pd.DataFrame() # 데이터 없으면 즉시 빈 판다스 반환
        
        rows = []
        for item in data:
            # 날짜 값이 유효한지 1차 검증
            s_str = item.get('startDt', '')[:10]
            e_str = item.get('endDt', '')[:10]
            if not s_str: continue
            
            s_dt = datetime.strptime(s_str, '%Y-%m-%d').date()
            e_dt = datetime.strptime(e_str, '%Y-%m-%d').date()
            
            # 검색 기간 내의 모든 날짜를 행으로 생성
            curr = s_dt
            while curr <= e_dt:
                if start_date <= curr <= end_date:
                    rows.append({
                        '날짜': curr.strftime('%Y-%m-%d'),
                        '건물명': str(item.get('buNm', '')).strip(),
                        '장소': item.get('placeNm', '') or '-',
                        '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                        '행사명': item.get('eventNm', '') or '-',
                        '부서': item.get('mgDeptNm', '') or '-',
                        '상태': '확정' if item.get('status') == 'Y' else '대기'
                    })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except Exception as e:
        # 에러 발생 시 화면에 표시하여 디버깅 지원
        st.error(f"데이터 로드 중 오류: {e}")
        return pd.DataFrame()
