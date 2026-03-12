import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

# CSS
st.markdown("""
<style>

.title{
font-size:26px;
font-weight:800;
text-align:center;
margin-bottom:20px;
}

.date{
font-size:20px;
font-weight:700;
margin-top:30px;
border-bottom:2px solid #ddd;
}

.building{
font-size:16px;
font-weight:700;
margin-top:10px;
margin-bottom:5px;
color:#1f4e79;
}

.table-wrap{
overflow-x:auto;
}

table{
border-collapse:collapse;
width:100%;
min-width:650px;
}

th{
background:#f3f3f3;
padding:8px;
border:1px solid #ddd;
font-size:13px;
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

st.markdown('<div class="title">성의교정 대관 현황</div>', unsafe_allow_html=True)

today = datetime.today().date()

# 날짜 선택
col1,col2=st.columns(2)

with col1:
    start=st.date_input("시작일",today)

with col2:
    end=st.date_input("종료일",today)

# API 조회
def get_data(start,end):

    url="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"

    params={
        "mode":"getReservedData",
        "start":start.strftime("%Y-%m-%d"),
        "end":end.strftime("%Y-%m-%d")
    }

    r=requests.get(url,params=params)

    if r.status_code!=200:
        return pd.DataFrame()

    data=r.json().get("res",[])

    rows=[]

    for item in data:

        s=item["startDt"]
        e=item["endDt"]

        start_date=datetime.strptime(s,"%Y-%m-%d").date()
        end_date=datetime.strptime(e,"%Y-%m-%d").date()

        d=start_date

        while d<=end_date:

            if start<=d<=end:

                rows.append({
                "date":d,
                "building":item.get("buNm",""),
                "place":item.get("placeNm",""),
                "time":item.get("startTime","")+"~"+item.get("endTime",""),
                "event":item.get("eventNm",""),
                "people":item.get("peopleCount",""),
                "dept":item.get("mgDeptNm",""),
                "status":"확정" if item.get("status")=="Y" else "대기"
                })

            d+=timedelta(days=1)

    df=pd.DataFrame(rows)

    if not df.empty:
        df=df.sort_values(["date","building","time"])

    return df


df=get_data(start,end)

if df.empty:

    st.info("조회된 데이터가 없습니다.")

else:

    for d in sorted(df["date"].unique()):

        day_df=df[df["date"]==d]

        st.markdown(f'<div class="date">{d}</div>', unsafe_allow_html=True)

        for b in sorted(day_df["building"].unique()):

            b_df=day_df[day_df["building"]==b]

            st.markdown(f'<div class="building">{b}</div>', unsafe_allow_html=True)

            html="""
            <div class="table-wrap">
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

            for _,r in b_df.iterrows():

                html+=f"""
                <tr>
                <td>{r['place']}</td>
                <td>{r['time']}</td>
                <td style="text-align:left">{r['event']}</td>
                <td>{r['people']}</td>
                <td>{r['dept']}</td>
                <td>{r['status']}</td>
                </tr>
                """

            html+="</table></div>"

            st.markdown(html,unsafe_allow_html=True)