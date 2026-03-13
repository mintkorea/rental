# 전역 CSS 수정: PC에서는 가로로 꽉 차게, 모바일에서는 스크롤 발생
st.markdown("""
<style>
    .main-title { font-size: 24px !important; font-weight: 800; color: #1E3A5F; border-bottom: 3px solid #1E3A5F; padding-bottom: 10px; margin-bottom: 20px; }
    .date-container { background-color: #f1f3f5; padding: 15px; border-radius: 8px; margin-top: 35px; margin-bottom: 10px; }
    .building-title { color: #2E5077; margin-top: 20px; margin-bottom: 10px; border-left: 5px solid #2E5077; padding-left: 12px; font-weight: 700; }
    
    /* 스크롤 컨테이너: PC에서는 100%, 모바일에서만 작동 */
    .scroll-wrapper { width: 100%; overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
    
    /* 표 설정: PC에서는 100% 너비, 모바일에서도 최소 750px 유지 */
    .custom-table { width: 100% !important; min-width: 750px; border-collapse: collapse; font-size: 14px; table-layout: fixed !important; }
    .custom-table th, .custom-table td { border: 1px solid #ddd; padding: 12px 8px; text-align: center; vertical-align: middle; word-break: break-all; }
    .custom-table th { background-color: #f8f9fa; font-weight: bold; }
    
    .scroll-hint { text-align: right; color: #888; font-size: 11px; margin-top: 5px; margin-bottom: 15px; }
    
    /* PC에서 너무 넓게 퍼지는 것 방지 (가독성 조절) */
    @media (min-width: 1200px) {
        .custom-table { font-size: 15px; }
    }
</style>
""", unsafe_allow_html=True)

# ... (중략: 데이터 로직 및 엑셀 함수) ...

# 표 출력 부분 (HTML 구조 동일, 클래스 유지)
# table-rows 생성부에서 너비를 % 비율로 조정하여 PC 대응
table_rows = ""
for _, r in b_df.iterrows():
    table_rows += f"""
    <tr>
        <td style="width:12%;">{r['장소']}</td>
        <td style="width:13%;">{r['시간']}</td>
        <td style="width:35%; text-align:left; padding-left:10px;">{r['행사명']}</td>
        <td style="width:15%;">{r['부서']}</td>
        <td style="width:8%;">{r['인원']}</td>
        <td style="width:8%;">{r['부스']}</td>
        <td style="width:9%;">{r['상태']}</td>
    </tr>"""

table_html = f"""
<div class="scroll-wrapper">
    <table class="custom-table">
        <thead>
            <tr>
                <th style="width:12%;">장소</th>
                <th style="width:13%;">시간</th>
                <th style="width:35%;">행사명</th>
                <th style="width:15%;">부서</th>
                <th style="width:8%;">인원</th>
                <th style="width:8%;">부스</th>
                <th style="width:9%;">상태</th>
            </tr>
        </thead>
        <tbody>{table_rows}</tbody>
    </table>
</div>
<div class="scroll-hint">↔ 모바일은 옆으로 밀어서 보세요</div>"""
st.markdown(table_html, unsafe_allow_html=True)
