import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 (사이드바 기본 확장)
st.set_page_config(
    page_title="성의교정 실시간 대관 현황", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. CSS 스타일: 장소명 1줄 고정 및 레이아웃 최적화
st.markdown("""
<style>
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 5px; background: white; }
    .row-main { display: flex; align-items: center; justify-content: space-between; gap: 5px; }
    
    /* [가이드라인] 장소명 1줄 고정 및 말줄임 처리 */
    .col-place { 
        flex: 5.8; 
        font-weight: 700; 
        color: #1e3a5f; 
        white-space: nowrap; 
        overflow: hidden; 
        text-overflow: ellipsis; 
        display: block;
    }
    
    .col-time { flex: 2.7; font-size: 13px; color: #d9534f; font-weight: bold; text-align: center; white-space: nowrap;
