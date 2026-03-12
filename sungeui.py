@st.cache_data(ttl=60)
def get_data(s_date, e_date):
    url = "https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"
    params = {"mode": "getReservedData", "start": s_date.isoformat(), "end": e_date.isoformat()}
    try:
        res = requests.get(url, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        res.raise_for_status()
        raw = res.json().get('res', [])
        rows = []
        for item in raw:
            if not item.get('startDt'): continue
            s_dt = datetime.strptime(item['startDt'], '%Y-%m-%d').date()
            e_dt = datetime.strptime(item['endDt'], '%Y-%m-%d').date()
            
            # --- 수정된 요일 파싱 로직 ---
            allow_day_raw = str(item.get('allowDay', ''))
            allowed_days = []
            if allow_day_raw and allow_day_raw.lower() != 'none':
                # 숫자인 것만 추출하여 정수로 변환
                allowed_days = [int(d.strip()) for d in allow_day_raw.split(',') if d.strip().isdigit()]
            # --------------------------
            
            curr = s_dt
            while curr <= e_dt:
                if s_date <= curr <= e_date:
                    # allowed_days가 비어있으면 매일 대관, 있으면 해당 요일만 추가
                    if not allowed_days or (curr.weekday() + 1) in allowed_days:
                        rows.append({
                            '요일': ['월','화','수','목','금','토','일'][curr.weekday()],
                            'full_date': curr.strftime('%Y-%m-%d'),
                            '건물명': str(item.get('buNm', '')).strip(),
                            '장소': item.get('placeNm', ''), 
                            '시간': f"{item.get('startTime', '')}~{item.get('endTime', '')}",
                            '행사명': item.get('eventNm', ''), 
                            '인원': item.get('peopleCount', '') or '-',
                            '부서': item.get('mgDeptNm', '') or '-',
                            '상태': '확정' if item.get('status') == 'Y' else '대기'
                        })
                curr += timedelta(days=1)
        return pd.DataFrame(rows)
    except Exception as e:
        # 에러 메시지를 좀 더 구체적으로 표시
        st.error(f"데이터를 가져오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()
