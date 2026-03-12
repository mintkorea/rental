import streamlit as st
import pandas as pd
from datetime import datetime, date
import io

# ... [기존 get_data, get_shift 로직 동일] ...

def create_formatted_excel(df, target_date, shift_name, selected_buildings):
    output = io.BytesIO()
    date_str = target_date.strftime("%Y. %m. %d")
    wd_name = ['','월','화','수','목','금','토','일'][target_date.isoweekday()]
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet('대관현황')
        
        # 1. 서식 정의
        # 타이틀: 중앙 정렬 및 폰트 확대
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'
        })
        # 날짜/근무조 정보: 중앙 정렬
        info_fmt = workbook.add_format({
            'font_size': 11, 'align': 'center', 'valign': 'vcenter'
        })
        # 건물명 행: 배경색 및 상단 여백 느낌
        bu_name_fmt = workbook.add_format({
            'bold': True, 'font_size': 12, 'font_color': '#1E3A5F', 
            'bg_color': '#EBF1F8', 'border': 1, 'valign': 'vcenter'
        })
        # 헤더 행: 중앙 정렬 및 테두리
        header_fmt = workbook.add_format({
            'bold': True, 'bg_color': '#F2F2F2', 'border': 1, 
            'align': 'center', 'valign': 'vcenter'
        })
        # 일반 데이터 셀: 높이 대응 및 안쪽 여백(vcenter)
        cell_fmt = workbook.add_format({
            'border': 1, 'align': 'left', 'valign': 'vcenter', 'text_wrap': True, 'font_size': 10
        })
        # 숫자/상태 셀: 중앙 정렬 및 안쪽 여백
        center_cell_fmt = workbook.add_format({
            'border': 1, 'align': 'center', 'valign': 'vcenter', 'font_size': 10
        })

        # 2. 타이틀 배치 (A~G열까지 병합하여 중앙 배열)
        worksheet.merge_range('A1:G1', "성의교정 대관 현황", title_fmt)
        worksheet.merge_range('A2:G2', f"일자: {date_str}({wd_name})  |  근무조: {shift_name}", info_fmt)
        worksheet.set_row(0, 30) # 타이틀 행 높이
        worksheet.set_row(1, 20) # 정보 행 높이

        curr_row = 3
        
        for bu in BUILDING_ORDER:
            if bu in selected_buildings:
                bu_df = df[df['건물명'] == bu]
                
                # 건물 구분선 및 타이틀
                worksheet.merge_range(curr_row, 0, curr_row, 6, f"  📍 {bu}", bu_name_fmt)
                worksheet.set_row(curr_row, 25) # 건물명 행 높이
                curr_row += 1
                
                # 헤더
                headers = ['장소', '시간', '행사명', '부서', '인원', '부스', '상태']
                for col_num, header in enumerate(headers):
                    worksheet.write(curr_row, col_num, header, header_fmt)
                worksheet.set_row(curr_row, 22) # 헤더 행 높이
                curr_row += 1
                
                if not bu_df.empty:
                    for _, row in bu_df.iterrows():
                        # 데이터 쓰기
                        worksheet.write(curr_row, 0, row['장소'], cell_fmt)
                        worksheet.write(curr_row, 1, row['시간'], center_cell_fmt)
                        worksheet.write(curr_row, 2, row['행사명'], cell_fmt)
                        worksheet.write(curr_row, 3, row['부서'], cell_fmt)
                        worksheet.write(curr_row, 4, row['인원'], center_cell_fmt)
                        worksheet.write(curr_row, 5, row['부스'], center_cell_fmt)
                        worksheet.write(curr_row, 6, row['상태'], center_cell_fmt)
                        
                        # 셀 높이 설정 (가독성을 위한 21px)
                        worksheet.set_row(curr_row, 21) 
                        curr_row += 1
                else:
                    worksheet.merge_range(curr_row, 0, curr_row, 6, "대관 내역이 없습니다.", center_cell_fmt)
                    worksheet.set_row(curr_row, 21)
                    curr_row += 1
                
                curr_row += 1 # 건물 간 여백
        
        # 3. 열 너비 설정
        worksheet.set_column('A:A', 22) # 장소
        worksheet.set_column('B:B', 14) # 시간
        worksheet.set_column('C:C', 45) # 행사명
        worksheet.set_column('D:D', 20) # 부서
        worksheet.set_column('E:G', 8)  # 인원, 부스, 상태

    return output.getvalue()
