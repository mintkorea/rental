```python
import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import pytz
from fpdf import FPDF

st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

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
min-width:700px;
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

KST = pytz.timezone('Asia/Seoul')
today = datetime.now(KST).date()

BUILDING_ORDER = [
"성의회관",
"의생명산업연구원",
"옴니버스 파크",
"옴니버스파크 의과대학",
"옴니버스파크 간호대학",
"대학본관",
"서울성모별관"
]

DEFAULT_BUILDINGS = ["성의회관","의생명산업연구원"]

@st.cache_data(ttl=60)
def get_data(start,end):

    url="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"

    params={
    "mode":"getReservedData",
    "start":start.isoformat(),
    "end":end.isoformat()
    }

    try:
        res=requests.get(url,params=params,timeout=10)

        if res.status_code != 200:
            return pd.DataFrame()

        raw=res.json().get("res",[])

        rows=[]

        for item in raw:

            if not item.get("startDt"):
                continue

            s=datetime.strptime(item["startDt"],"%Y-%m-%d").date()
            e=datetime.strptime(item["endDt"],"%Y-%m-%d").date()

            d=s

            while d<=e:

                if start<=d<=end:

                    rows.append({
                    "날짜":d.strftime("%Y-%m-%d"),
                    "요일":['월','화','수','목','금','토','일'][d.weekday()],
                    "건물":item.get("buNm",""),
                    "장소":item.get("placeNm",""),
                    "시간":f"{item.get('startTime')}~{item.get('endTime')}",
                    "행사":item.get("eventNm",""),
                    "인원":item.get("peopleCount",""),
                    "부서":item.get("mgDeptNm",""),
                    "상태":"확정" if item.get("status")=="Y" else "대기"
                    })

                d+=timedelta(days=1)

        df=pd.DataFrame(rows)

        if not df.empty:
            df["건물"]=pd.Categorical(df["건물"],categories=BUILDING_ORDER,ordered=True)
            df=df.sort_values(["날짜","건물","시간"])

        return df

    except:
        return pd.DataFrame()

def create_pdf(df):

    pdf=FPDF("L","mm","A4")
    pdf.set_font("Arial",size=10)

    for date in sorted(df["날짜"].unique()):

        pdf.add_page()

        day_df=df[df["날짜"]==date]

        weekday=day_df.iloc[0]["요일"]

        pdf.set_font("Arial","B",16)
        pdf.cell(0,10,f"Rental Status {date} {weekday}",0,1,"C")

        pdf.ln(5)

        for bu in BUILDING_ORDER:

            bu_df=day_df[day_df["건물"]==bu]

            if bu_df.empty:
                continue

            pdf.set_font("Arial","B",12)
            pdf.cell(0,8,bu,0,1)

            headers=["Place","Time","Event","People","Dept","Status"]
            widths=[40,35,120,20,60,20]

            pdf.set_font("Arial","B",10)

            for h,w in zip(headers,widths):
                pdf.cell(w,8,h,1,0,"C")

            pdf.ln()

            pdf.set_font("Arial",size=9)

            for _,r in bu_df.iterrows():

                pdf.cell(40,8,str(r["장소"])[:20],1)
                pdf.cell(35,8,str(r["시간"]),1)
                pdf.cell(120,8=str(r["행사"])[:50],border=1)
                pdf.cell(20,8,str(r["인원"]),1)
                pdf.cell(60,8,str(r["부서"])[:25],1)
                pdf.cell(20,8,str(r["상태"]),1)

                pdf.ln()

            pdf.ln(3)

    return pdf.output(dest="S").encode("latin1")

st.sidebar.title("조회 설정")

start=st.sidebar.date_input("시작일",today)
end=st.sidebar.date_input("종료일",start)

buildings=st.sidebar.multiselect(
"건물 선택",
BUILDING_ORDER,
default=DEFAULT_BUILDINGS
)

df=get_data(start,end)

if not df.empty:

    pdf=create_pdf(df)

    st.sidebar.download_button(
    "PDF 다운로드",
    data=pdf,
    file_name="rental.pdf",
    mime="application/pdf"
    )

st.markdown('<div class="main-title">성의교정 대관 현황</div>',unsafe_allow_html=True)

if not df.empty:

    for date in sorted(df["날짜"].unique()):

        day_df=df[df["날짜"]==date]

        st.markdown(
        f'<div class="date-header">{date} ({day_df.iloc[0]["요일"]})</div>',
        unsafe_allow_html=True
        )

        for bu in buildings:

            bu_df=day_df[day_df["건물"]==bu]

            if bu_df.empty:
                continue

            st.markdown(
            f'<div class="building-header">{bu}</div>',
            unsafe_allow_html=True
            )

            html="""
            <div class="table-container">
            <table>
            <tr>
            <th>장소</th>
            <th>시간</th>
            <th>행사</th>
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
                <td style="text-align:left">{r['행사']}</td>
                <td>{r['인원']}</td>
                <td>{r['부서']}</td>
                <td>{r['상태']}</td>
                </tr>
                """

            html+="</table></div>"

            st.markdown(html,unsafe_allow_html=True)

else:
    st.info("조회 결과가 없습니다.")
```
