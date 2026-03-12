# ... (상단 생략)

# 5. 메인 UI
st.sidebar.title("📅 설정")
start_selected = st.sidebar.date_input("시작일", value=now_today)
end_selected = st.sidebar.date_input("종료일", value=start_selected)
selected_bu = st.sidebar.multiselect("건물 필터", options=BUILDING_ORDER, default=DEFAULT_BUILDINGS)

# [중요] raw_df를 먼저 가져옵니다.
raw_df = get_data(start_selected, end_selected)

if not raw_df.empty:
    # [중요] 여기서 filtered_df를 정의해야 NameError가 나지 않습니다.
    filtered_df = raw_df[raw_df['건물명'].isin(selected_bu)].copy()
    filtered_df['건물명'] = pd.Categorical(filtered_df['건물명'], categories=BUILDING_ORDER, ordered=True)
    filtered_df = filtered_df.sort_values(by=['full_date', '건물명', '시간'])

    # 정의된 후 검사
    if not filtered_df.empty:
        with st.sidebar:
            if st.button("📄 PDF 생성 및 준비"):
                try:
                    pdf_bytes = create_pdf(filtered_df)
                    st.download_button(
                        label="📥 PDF 다운로드",
                        data=pdf_bytes,
                        file_name=f"rental_{start_selected}.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"PDF 생성 오류: {e}")

        st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>', unsafe_allow_html=True)
        
        # 날짜별 출력 루프
        for date in sorted(filtered_df['full_date'].unique()):
            day_df = filtered_df[filtered_df['full_date'] == date]
            st.markdown(f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>', unsafe_allow_html=True)
            
            for bu in selected_bu:
                bu_df = day_df[day_df['건물명'] == bu]
                if not bu_df.empty:
                    st.markdown(f'<div class="building-header">🏢 {bu}</div>', unsafe_allow_html=True)
                    # ... (이하 테이블 출력 HTML 로직 생략)
    else:
        st.info("선택한 건물 필터에 해당하는 내역이 없습니다.")
else:
    st.info("조회된 내역이 없습니다.")
