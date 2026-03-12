import io
import pandas as pd

def create_excel_with_style(df):
    output = io.BytesIO()
    
    # 건물 출력 순서 정의 (사용자 지정 순서)
    BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]
    
    # 데이터 정렬 (날짜 -> 건물 순서 -> 시간 순)
    df['순서'] = df['건물명'].apply(lambda x: BUILDING_ORDER.index(x) if x in BUILDING_ORDER else 99)
    df = df.sort_values(by=['날짜', '순서', '시간']).drop(columns=['순서'])

    # xlsxwriter 엔진을 사용하여 엑셀 파일 생성
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='대관현황')
        
        workbook  = writer.book
        worksheet = writer.sheets['대관현황']

        # 1. 서식 설정 (PDF 느낌의 깔끔한 스타일)
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'center',
            'fg_color': '#D9E1F2',  # 연한 파란색 배경
            'border': 1
        })
        
        cell_format = workbook.add_format({
            'valign': 'vcenter',
            'align': 'center',
            'border': 1
        })

        wrap_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'vcenter',
            'align': 'left',
            'border': 1
        })

        # 2. 헤더 행에 서식 적용
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # 3. 열 너비 및 데이터 서식 설정 (PDF 가독성 기준)
        worksheet.set_column('A:A', 12, cell_format)  # 날짜
        worksheet.set_column('B:B', 6, cell_format)   # 요일
        worksheet.set_column('C:C', 15, cell_format)  # 건물명
        worksheet.set_column('D:D', 18, cell_format)  # 장소
        worksheet.set_column('E:E', 15, cell_format)  # 시간
        worksheet.set_column('F:F', 45, wrap_format)  # 행사명 (길게, 줄바꿈 허용)
        worksheet.set_column('G:G', 8, cell_format)   # 인원
        worksheet.set_column('H:I', 15, cell_format)  # 부서, 상태

    return output.getvalue()
