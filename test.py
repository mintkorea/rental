# [상단 생략... 4~6 섹션 로직 시작점]
if st.session_state.search_performed:
    st.markdown('<div id="result-anchor"></div>', unsafe_allow_html=True)
    d = st.session_state.target_date
    df_raw = get_data(d)
    shift = get_work_shift(d)
    is_weekend = d.isoweekday() in [6, 7]
    d_str_key = d.strftime('%Y-%m-%d')
    
    # 1. 휴일 당직 데이터 정의 (의학교육지원팀)
    duty_dict = {
        "2026-03-21": {"name": "김태남", "tel": "3147-8262", "event": "2026 WOUND MEETING"},
        "2026-03-22": {"name": "한정욱", "tel": "3147-8261", "event": "전북대학교 치과대학 학술대회"},
        "2026-03-28": {"name": "한정욱", "tel": "3147-8261", "event": "제29차 당뇨병 교육자 연수강좌"},
        "2026-03-29": {"name": "김태남", "tel": "3147-8262", "event": "제67차 대한천식알레르기학회 교육강좌"}
    }

    # 2. 노출 제어 로직: 화관/의산연 행사 여부 확인
    # 공백 제거 후 비교하여 정확도 향상
    target_bus = ["성의회관", "의생명산업연구원"]
    check_df = df_raw[df_raw['buNm'].str.replace(" ", "").isin([b.replace(" ", "") for b in target_bus])] if not df_raw.empty else pd.DataFrame()

    if not check_df.empty:
        # 날짜 헤더 출력
        w_idx = d.weekday()
        w_day_str, w_class = ['월','화','수','목','금','토','일'][w_idx], ("sat" if w_idx == 5 else ("sun" if w_idx == 6 else ""))
        st.markdown(f"""
        <div class="date-display-box">
            <span class="res-main-title">성의교정 대관 현황</span>
            <span class="res-sub-title">{d.strftime("%Y.%m.%d")}.<span class="{w_class}">({w_day_str})</span>
            <span style="background:{shift['bg']}; color:white; padding:2px 10px; border-radius:12px; font-size:14px; margin-left:5px; vertical-align:middle;">근무 : {shift['n']}</span></span>
        </div>
        <div class="nav-link-bar">
            <a href="./?d={(d-timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-item">◀ Before</a>
            <a href="./?d={today_kst().strftime('%Y-%m-%d')}" target="_self" class="nav-item">Today</a>
            <a href="./?d={(d+timedelta(1)).strftime('%Y-%m-%d')}" target="_self" class="nav-item">Next ▶</a>
        </div>
        """, unsafe_allow_html=True)

        target_wd = str(d.weekday() + 1)
        for bu in selected_bu_list:
            st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
            has_content = False
            
            # 건물별 대관 리스트 출력
            bu_df = df_raw[df_raw['buNm'].str.replace(" ", "") == bu.replace(" ", "")] if not df_raw.empty else pd.DataFrame()
            if not bu_df.empty:
                # ... [기존 당일/기간 대관 카드 출력 로직 그대로 유지] ...
                # (지면 관계상 생략하지만, 기존의 t_ev, p_ev 출력 코드가 여기에 들어갑니다)
                has_content = True 

            if not has_content:
                st.markdown('<div style="color:#999; text-align:center; padding:15px; border:1px dashed #eee; font-size:13px;">대관 내역이 없습니다.</div>', unsafe_allow_html=True)

            # [핵심] 의산연 출력 직후 당직 안내 추가
            if bu == "의생명산업연구원" and d_str_key in duty_dict:
                duty = duty_dict[d_str_key]
                st.markdown(f"""
                <div style="background-color: #FFF4F4; border-left: 5px solid #FF4B4B; padding: 12px; margin: 10px 0; border-radius: 5px; border: 1px solid #FFDADA;">
                    <div style="font-size: 15px; font-weight: bold; color: #D32F2F; margin-bottom: 5px;">📅 의학교육지원팀 당직근무 안내</div>
                    <div style="font-size: 13px; line-height: 1.5; color: #333;">
                        <b>당직자: {duty['name']} ({duty['tel']})</b><br>
                        <b>행사:</b> {duty['event']}<br>
                        <span style="color: #D32F2F; font-weight: bold;">※ 구내번호 연락 안 될 시 마리아홀 조정실 확인 바랍니다.</span><br>
                        주말 당직자 미연락 시 총무팀 주종호(1187) 선생에게 문의하세요.
                    </div>
                </div>
                """, unsafe_allow_html=True)

    else:
        st.info("선택한 날짜에 성의회관/의산연 대관 행사가 없습니다.")

    # [이하 강의실 개방 지침 로직 유지...]
