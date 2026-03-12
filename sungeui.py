def create_formatted_excel(df, target_date, shift_name, selected_buildings):
    output = io.BytesIO()
    date_str = target_date.strftime("%Y. %m. %d")
    wd_names = ['','월','화','수','목','금','토','일']
    wd_name = wd_names[target_date.isoweekday()]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 1. 서식 정의 (폰트 크기 11 반영)
        title_fmt = workbook.add_format({'bold': True, 'font_size': 18, 'align': 'center', 'valign': 'vcenter'})
        info_fmt = workbook.add_format({'font_size': 12, 'align': 'center', 'valign': 'vcenter'})
        bu_fmt = workbook.add_format({'bold': True, 'font_size': 12, 'bg_color': '#EBF1F8', 'border': 1, 'valign': 'vcenter'})
        hdr_fmt = workbook.add_format({'bold': True, 'font_size': 11, 'bg_color': '#F2F2F2', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
        
        # 일반 데이터 셀 (폰트 11, 줄바꿈, 상하중앙)
        cell_fmt = workbook.add_format({
            'border': 1, 
            'align': 'left', 
            'valign': 'vcenter', 
            'text_wrap': True, 
            'font_size': 11  # 요청하신 11폰트 적용
        })
        
        # 숫자/상태용 중앙 정렬 셀 (폰트 11)
        cnt_fmt = workbook.add_format({
            'border': 1, 
            'align': 'center', 
            'valign': 'vcenter', 
            'font_size': 11  # 요청하신 11폰트 적용
        })

        # 상단 타이틀 중앙 배열
        worksheet.merge_range('A1:G1', "성의교정 대관 현황", title_fmt)
        worksheet.merge_range('A2:G2', f"일자: {date_str}({wd_name})  |  근무조: {shift_name}", info_fmt)
        worksheet.set_row(0, 40) # 타이틀 높이 확대
        worksheet.set_row(1, 28) # 정보행 높이 확대

        curr_row = 3
        for bu in BUILDING_ORDER:
            if bu in selected_buildings:
                bu_df = df[df['건물명'] == bu] if not df.empty else pd.DataFrame()
                
                # 건물명 행
                worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_fmt)
                worksheet.set_row(curr_row, 30)
                curr_row += 1
                
                # 헤더
                headers = ['장소', '시간', '행사명', '부서', '인원', '부스', '상태']
                for col_num, header in enumerate(headers):
                    worksheet.write(curr_row, col_num, header, hdr_fmt)
                worksheet.set_row(curr_row, 28)
                curr_row += 1
                
                if not bu_df.empty:
                    for _, row in bu_df.iterrows():
                        worksheet.write(curr_row, 0, row['장소'], cell_fmt)
                        worksheet.write(curr_row, 1, row['시간'], cnt_fmt)
                        worksheet.write(curr_row, 2, row['행사명'], cell_fmt)
                        worksheet.write(curr_row, 3, row['부서'], cell_fmt)
                        worksheet.write(curr_row, 4, row['인원'], cnt_fmt)
                        worksheet.write(curr_row, 5, row['부스'], cnt_fmt)
                        worksheet.write(curr_row, 6, row['상태'], cnt_fmt)
                        
                        # 폰트 11에 맞춰 행 높이를 35로 상향 조정 (가독성 최적화)
                        worksheet.set_row(curr_row, 35) 
                        curr_row += 1
                else:
                    worksheet.merge_range(curr_row, 0, curr_row, 6, "대관 내역이 없습니다.", cnt_fmt)
                    worksheet.set_row(curr_row, 35)
                    curr_row += 1
                curr_row += 1 

        # 열 너비 설정 (폰트가 커졌으므로 너비도 소폭 조정)
        worksheet.set_column('A:A', 25) # 장소
        worksheet.set_column('B:B', 16) # 시간
        worksheet.set_column('C:C', 50) # 행사명
        worksheet.set_column('D:D', 22) # 부서
        worksheet.set_column('E:G', 10) # 인원, 부스, 상태

    return output.getvalue()
