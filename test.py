import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 (사이드바 기본 오픈)
st.set_page_config(
    page_title="성의교정 실시간 대관 현황", 
    page_icon="🏢", 
    layout="wide",
    initial_sidebar_state="expanded"
)

KST = pytz.timezone('Asia/Seoul')
now_today = datetime.now(KST).date()
BUILDING_ORDER = ["성의회관", "의생명산업연구원", "옴니버스 파크", "옴니버스파크 의과대학", "옴니버스파크 간호대학", "대학본관", "서울성모별관"]

# 2. 모바일 셸 디자인 CSS
st.markdown("""
<style>
    .event-shell { border-bottom: 1px solid #eee; padding: 12px 5px; background: white; }
    .row-main { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
    .col-place { flex: 5; font-size: 15px; font-weight: 700; color: #1e3a5f; }
    .col-time { flex: 3.5; font-size: 14px; color: #d9534f; font-weight: bold; text-align: center; }
    .col-status { flex: 1.5; font-size: 13px; font-weight: bold; text-align: right; }
    .row-sub { font-size: 13px; color: #666; margin-top: 6px; }
    .main-title { font-size: 2.2rem; font-weight: 900; color: #1e3a5f; text-align: center; margin-bottom: 20px; line-height: 1.2; }
</style>
""", unsafe_allow_html=True)

def get_shift(target_date):
    base_date = date(2026, 3, 13)
    diff = (target_date - base_date).days
    return f"{['A', 'B', 'C'][diff % 3
