# 검색 및 음성 입력 섹션 수정
col1, col2, col3 = st.columns([3, 1, 1])

# 검색어 입력
search_query = col1.text_input("검색어를 입력하세요", key="search_input", label_visibility="collapsed")

# 음성 입력 버튼
if col2.button("🎤 음성"):
    st.components.v1.html("<script>startDictation();</script>", height=0)

# [추가] 초기화 버튼: 클릭 시 세션 상태를 비우고 리런(Rerun)
if col3.button("🔄 초기화"):
    st.session_state.search_input = ""
    st.rerun()

# 결과 출력 로직 (가이드라인 준수: 정확한 매칭 및 리스트 복귀)
if search_query:
    # 검색어가 있을 때만 필터링된 결과 표출
    filtered_df = master_df[master_df.apply(lambda row: search_query in str(row.values), axis=1)]
    st.write(f"🔍 '{search_query}' 검색 결과입니다.")
else:
    # 검색어가 없으면 전체 리스트 표출
    filtered_df = master_df
    st.write("📋 전체 입주 현황 리스트입니다.")

st.table(filtered_df)
