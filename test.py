import streamlit as st

# 1. 관리할 앱 목록 (여기에 추가/삭제만 하면 화면에 자동 반영됩니다)
APPS = [
    {
        "title": "📱 대관 조회 (모바일)",
        "url": "https://klzsyte9n8ftnuwcuid9tw.streamlit.app/",
        "desc": "현장용 대관 및 당직 내역 확인",
        "color": "#1E3A5F"
    },
    {
        "title": "💻 대관/입주 관리 (PC)",
        "url": "https://rental-2q7nwue9hmapek9nuir6vh.streamlit.app/",
        "desc": "엑셀 다운로드 및 상세 행정 관리",
        "color": "#1E3A5F"
    },
    {
        "title": "🍱 주간 식단표",
        "url": "https://3y2krzjwosv86ccxobc38i.streamlit.app/",
        "desc": "교내 식당 메뉴 및 식사 정보",
        "color": "#4CAF50"
    },
    {
        "title": "🚨 보안 비상연락망",
        "url": "https://t78ulrec88a9tku62zekge.streamlit.app/",
        "desc": "보안/미화 파트별 긴급 연락처",
        "color": "#F44336"
    }
]

# 2. 페이지 설정
st.set_page_config(page_title="성의 워크플레이스 허브", page_icon="🏫")

# 3. 디자인 스타일 (CSS)
st.markdown("""
<style>
    .hub-title { font-size: 24px; font-weight: 800; text-align: center; color: #1E3A5F; margin-bottom: 25px; }
    .app-card {
        display: block; padding: 18px; border-radius: 12px; border: 1px solid #E0E0E0;
        text-decoration: none !important; margin-bottom: 12px; transition: 0.2s;
        background: white; border-left: 6px solid #1E3A5F;
    }
    .app-card:hover { background: #F0F4F8; transform: scale(1.02); }
    .app-title { font-size: 18px; font-weight: bold; color: #1E3A5F; }
    .app-desc { font-size: 13px; color: #666; margin-top: 4px; }
</style>
""", unsafe_allow_html=True)

# 4. 화면 구성
st.markdown('<div class="hub-title">🏫 성의교정 업무 통합 포털</div>', unsafe_allow_html=True)

# 리스트를 순회하며 자동으로 카드 생성
for app in APPS:
    st.markdown(f'''
        <a href="{app['url']}" target="_blank" class="app-card" style="border-left-color: {app['color']};">
            <div class="app-title">{app['title']}</div>
            <div class="app-desc">{app['desc']}</div>
        </a>
    ''', unsafe_allow_html=True)

st.markdown("---")
st.caption("새로운 기능 추가 문의: 시설관리팀 (내선 1187)")
