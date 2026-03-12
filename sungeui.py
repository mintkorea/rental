```python
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF
import os

# 페이지 설정
st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# 모바일 줌 허용
st.markdown("""
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, user-scalable=yes">
""", unsafe_allow_html=True)

# CSS
st.markdown("""
<style>

.main-title{
font-size:22px;
font-weight:800;
text-align:center;
margin-bottom:10px;
}

.date-header{
font-size:18px;
font-weight:700;
color:#1E3A5F;
margin-top:25px;
border-bottom:2px solid #eee;
padding-bottom:5px;
}

.building-header{
font-size:15px;
font-weight:700;
margin-top:10px;
margin-bottom:5px;
border-left:5px solid #2E5077;
padding-left:10px;
}

.table-container{
width:100%;
overflow-x:auto;
-webkit-overflow-scrolling:touch;
}

table{
border-collapse:collapse;
width:100%;
min-width:750px;
}

th{
background:#f5f5f5;
padding:8px;
border:1px solid #ddd;
font-size:13px;
text-align:center;
}

td{
padding:8px;
border:1px solid #eee;
font-size:13px;
white-space:nowrap;
text-align:center;
}

</style>
""", unsafe_allow_html=True)

# 기본 설정
KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()

BUILDING_ORDER = [
"성의회관",
"의생명산업연구원",
"옴니버스 파크",
"옴니버스파크 의과대학",
"옴니버스파크 간호대학",
"대학본관",
"서울성모별관"
]

DEFAULT_BUILDINGS = [
"성의회관",
"의생명산업연구원"
]

# 데이터 로드
@st.cache_data(ttl=60)
def get_data(s_date, e_date):

    url="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"

    params={
        "mode":"getReservedData",
        "start":s_date.isoformat(),
        "end":e_date.isoformat()
    }

    try:

        res=requests.get(url,params=params,headers={"User-Agent":"Mozilla/5.0"},timeout=10)

        raw=res.json().get("res",[])

        rows=[]

        for item in raw:

            if not item.get("startDt"):
                continue

            s_dt=datetime.strptime(item["startDt"],"%Y-%m-%d").date()
            e_dt=datetime.strptime(item["endDt"],"%Y-%m-%d").date()

            curr=s_dt

            while curr<=e_dt:

                if s_date<=curr<=e_date:

                    rows.append({

                    "날짜":curr.strftime("%Y-%m-%d"),
                    "요일":['월','화','수','목','금','토','일'][curr.weekday()],
                    "건물명":item.get("buNm",""),
                    "장소":item.get("placeNm",""),
                    "시간":f"{item.get('startTime')}~{item.get('endTime')}",
                    "행사명":item.get("eventNm",""),
                    "인원":item.get("peopleCount",""),
                    "부서":item.get("mgDeptNm",""),
                    "상태":"확정" if item.get("status")=="Y" else "대기"

                    })

                curr+=timedelta(days=1)

        df=pd.DataFrame(rows)

        if not df.empty:

            df["건물명"]=pd.Categorical(df["건물명"],categories=BUILDING_ORDER,ordered=True)

            df=df.sort_values(["날짜","건물명","시간"])

        return df

    except:
        return pd.DataFrame()

# PDF 생성
def create_pdf(df,selected_buildings):

    pdf=FPDF("L","mm","A4")

    font_path="NanumGothic.ttf"

    if os.path.exists(font_path):

        pdf.add_font("Nanum","",font_path,uni=True)
        pdf.set_font("Nanum",size=10)

    for date in sorted(df["날짜"].unique()):

        pdf.add_page()

        day_df=df[df["날짜"]==date]

        weekday=day_df.iloc[0]["요일"]

        pdf.set_font("Nanum",size=16)

        pdf.cell(0,12,f"성의교정 대관 현황 ({date} {weekday}요일)",ln=True,align="C")

        pdf.ln(5)

        for bu in selected_buildings:

            bu_df=day_df[day_df["건물명"]==bu]

            if bu_df.empty:
                continue

            pdf.set_font("Nanum",size=12)
            pdf.cell(0,8,f"■ {bu}",ln=True)

            headers=["장소","시간","행사명","인원","부서","상태"]
            widths=[40,35,120,15,60,20]

            pdf.set_font("Nanum",size=9)

            for h,w in zip(headers,widths):
                pdf.cell(w,8,h,1,0,"C")

            pdf.ln()

            for _,r in bu_df.iterrows():

                pdf.cell(40,8,str(r["장소"])[:20],1)
                pdf.cell(35,8,str(r["시간"]),1)
                pdf.cell(120,8,str(r["행사명"])[:50],1)
                pdf.cell(15,8,str(r["인원"]),1)
                pdf.cell(60,8,str(r["부서"])[:25],1)
                pdf.cell(20,8,str(r["상태"]),1)

                pdf.ln()

            pdf.ln(3)

    return pdf.output(dest="S").encode("latin1")

# 사이드바
st.sidebar.title("📅 대관 조회 설정")

start=st.sidebar.date_input("시작일",value=now_today)
end=st.sidebar.date_input("종료일",value=start)

selected_bu=st.sidebar.multiselect(
"건물 선택",
BUILDING_ORDER,
default=DEFAULT_BUILDINGS
)

df=get_data(start,end)

# PDF 다운로드
if not df.empty:

    pdf=create_pdf(df,selected_bu)

    st.sidebar.download_button(
        "📥 PDF 다운로드",
        data=pdf,
        file_name=f"rental_{start}_{end}.pdf",
        mime="application/pdf"
    )

# 타이틀
st.markdown('<div class="main-title">🏫 성의교정 대관 현황</div>',unsafe_allow_html=True)

# 화면 출력
if not df.empty:

    for date in sorted(df["날짜"].unique()):

        day_df=df[df["날짜"]==date]

        st.markdown(
        f'<div class="date-header">📅 {date} ({day_df.iloc[0]["요일"]}요일)</div>',
        unsafe_allow_html=True
        )

        for bu in selected_bu:

            bu_df=day_df[day_df["건물명"]==bu]

            if bu_df.empty:
                continue

            st.markdown(
            f'<div class="building-header">🏢 {bu}</div>',
            unsafe_allow_html=True
            )

            html="""
            <div class="table-container">
            <table>
            <tr>
            <th>장소</th>
            <th>시간</th>
            <th>행사명</th>
            <th>인원</th>
            <th>부서</th>
            <th>상태</th>
            </tr>
            """

            for _,r in bu_df.iterrows():

                html+=f"""
                <tr>
                <td>{r['장소']}</td>
                <td>{r['시간']}</td>
                <td style="text-align:left">{r['행사명']}</td>
                <td>{r['인원']}</td>
                <td>{r['부서']}</td>
                <td>{r['상태']}</td>
                </tr>
                """

            html+="</table></div>"

            st.markdown(html,unsafe_allow_html=True)

else:

    st.info("조회된 내역이 없습니다.")
```
