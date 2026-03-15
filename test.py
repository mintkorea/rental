import io
import pandas as pd
from datetime import datetime

# [추출] 엑셀 생성 함수 (행 높이 35, 폰트 자동조정 적용)
def create_formatted_excel(df, selected_buildings):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        worksheet.set_landscape()
        
        # 서식 정의
        date_hdr_fmt = workbook.add_format({
            'bold': True, 'font_size': 12, 'bg_color': '#333333', 'font_color': 'white', 
            'align': 'center', 'valign': 'vcenter', 'border': 1
        })
        bu_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#EBF1F8', 
            'align': 'left', 'valign': 'vcenter', 'border': 1
        })
        # 줄바꿈 + 폰트 자동 줄임(shrink) 적용
        left_fmt = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'shrink': True
        })
        center_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter', 'shrink': True
        })

        curr_row = 1
        # BUILDING_ORDER는 전역 변수 혹은 리스트로 정의되어 있어야 함
        for d_str in sorted(df['full_date'].unique()):
            d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
            
            # 날짜 헤더 행 높이 35
            worksheet.set_row(curr_row, 35)
            # get_shift 함수는 기존 코드의 로직을 따름
            worksheet.merge_range(curr_row, 0, curr_row, 6, f"📅 {d_str} | 근무조: {get_shift(d_obj)}", date_hdr_fmt)
            curr_row += 1
            
            for bu in BUILDING_ORDER:
                if bu in selected_buildings:
                    bu_clean = bu.replace(" ", "")
                    b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ","") == bu_clean)]
                    
                    if not b_df.empty:
                        # 건물명 행 높이 35
                        worksheet.set_row(curr_row, 35)
                        worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                        curr_row += 1
                        
                        for _, r in b_df.iterrows():
                            # 데이터 행 높이 35 고정
                            worksheet.set_row(curr_row, 35)
                            worksheet.write(curr_row, 0, r['장소'], left_fmt)
                            worksheet.write(curr_row, 1, r['시간'], center_fmt)
                            worksheet.write(curr_row, 2, r['행사명'], left_fmt)
                            worksheet.write(curr_row, 3, r['부서'], left_fmt)
                            worksheet.write(curr_row, 4, r['인원'], center_fmt)
                            worksheet.write(curr_row, 5, r['부스'], center_fmt)
                            worksheet.write(curr_row, 6, r['상태'], center_fmt)
                            curr_row += 1
                        curr_row += 1

        # 열 너비 설정
        worksheet.set_column('A:A', 20)  # 장소
        worksheet.set_column('B:B', 12)  # 시간
        worksheet.set_column('C:C', 35)  # 행사명
        worksheet.set_column('D:D', 18)  # 부서
        worksheet.set_column('E:G', 7)   # 인원, 부스, 상태
        
    return output.getvalue()

# [추출] Streamlit 화면에 다운로드 버튼을 만드는 부분
if not df.empty:
    excel_data = create_formatted_excel(df, sel_bu)
    st.download_button(
        label="📥 엑셀 다운로드",
        data=excel_data,
        file_name=f"대관현황_{s_date}.xlsx",
        use_container_width=True
    )
