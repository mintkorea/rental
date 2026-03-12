import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="성의교정 대관 조회", layout="wide")

st.title("성의교정 대관 현황")

today = datetime.today().date()

col1,col2 = st.columns(2)

with col1:
    start = st.date_input("시작일", today)

with col2:
    end = st.date_input("종료일", today)


def get_data(start,end):

    url="https://songeui.catholic.ac.kr/ko/service/application-for-rental_calendar.do"

    params={
        "mode":"getReservedData",
        "start":start.strftime("%Y-%m-%d"),
        "end":end.strftime("%Y-%m-%d")
    }

    try:

        r=requests.get(url,params=params,timeout=10)

        if r.status_code!=200:
            st.error("API 연결 실패")
            return pd.DataFrame()

        try:
            json_data=r.json()
        except:
            st.error("API JSON 변환 오류")
            return pd.DataFrame()

        data=json_data.get("res",[])

    except Exception as e:

        st.error("데이터 조회 오류")
        return pd.DataFrame()

    rows=[]

    for item in data:

        start_date=datetime.strptime(item["startDt"],"%Y-%m-%d").date()
        end_date=datetime.strptime(item["endDt"],"%Y-%m-%d").date()

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

        st.subheader(str(d))

        day_df=df[df["date"]==d]

        for b in sorted(day_df["building"].unique()):

            st.write("###",b)

            st.dataframe(
                day_df[day_df["building"]==b][
                    ["place","time","event","people","dept","status"]
                ],
                use_container_width=True
            )