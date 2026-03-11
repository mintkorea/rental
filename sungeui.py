import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="성의교정 식단 매니저", layout="centered")

st.markdown("""
    <style>
    .menu-card { padding: 20px; border-radius: 15px; border-left: 5px solid #4CAF50; 
                background-color: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.1); margin-bottom: 20px; }
    .highlight { border-left-color: #ff4b4b !important; background-color: #fff5f5; }
    </style>
    """, unsafe_allow_html=True)

# 2. 사이드바 - 테스트 및 설정
with st.sidebar:
    st.header("🛠️ 개발자 설정")
    test_mode = st.toggle("테스트 모드 활성화", value=True, help="AI 분석 대신 가짜 데이터를 사용합니다.")
    st.divider()
    # 가상 시간 설정 (큐레이션 테스트용)
    test_time = st.slider("가상 시간 설정 (시)", 0, 23, datetime.now().hour)
    
    # 실제 API 키 (나중에 권한 해결 시 사용)
    api_key = st.secrets.get("GEMINI_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)

# 3. 데이터 처리 로직
now = datetime.now()
days = ["월", "화", "수", "목", "금", "토", "일"]
today_idx = now.weekday()
today_str = days[today_idx]

# 시간대별 강조 로직 (오후 2시 기준)
focus_menu = "중식" if test_time < 14 else "석식"

# 4. 분석 함수
def analyze_menu_mock():
    # 테스트용 더미 데이터
    return {
        "월": {"중식": "수제돈까스, 크림스프", "석식": "스팸김치덮밥"},
        "화": {"중식": "우거지해장국, 제육볶음", "석식": "닭갈비비빔밥"},
        "수": {"중식": "해물쟁반짜장, 탕수육", "석식": "차돌된장찌개"},
        "목": {"중식": "치킨마요덮밥, 미니우동", "석식": "고등어무조림"},
        "금": {"중식": "곤드레밥, 달래양념장", "석식": "부대찌개, 라면사리"}
    }

# 5. 메인 UI
st.title("🍱 성의교정 실시간 식단 매니저")
st.info(f"📅 오늘은 **{today_str}요일**입니다. ({'점심' if focus_menu == '중식' else '저녁'} 추천 시간)")

uploaded_file = st.file_uploader("식단표 이미지를 업로드하세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="업로드됨", use_container_width=True)
    
    if st.button("🚀 식단 분석 시작"):
        if test_mode:
            with st.spinner("테스트 모드로 데이터를 생성 중..."):
                st.session_state['menu_data'] = analyze_menu_mock()
                st.success("✅ 테스트 데이터 로드 완료!")
        else:
            # 실제 AI 분석 로직 (현재는 404 에러 가능성 있음)
            try:
                model = genai.GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(["식단을 JSON으로 추출해줘", img])
                st.session_state['menu_data'] = json.loads(response.text)
            except Exception as e:
                st.error(f"분석 오류: {e}")

# 6. 결과 전시 (데이터가 있을 때만 표시)
if 'menu_data' in st.session_state:
    st.divider()
    # 요일 선택 (오늘 요일이 기본값)
    selected_day = st.selectbox("요일 선택", days[:5], index=today_idx if today_idx < 5 else 0)
    menu = st.session_state['menu_data'].get(selected_day, {})

    col1, col2 = st.columns(2)
    
    # 중식 카드
    with col1:
        is_focus = (focus_menu == "중식" and selected_day == today_str)
        card_class = "menu-card highlight" if is_focus else "menu-card"
        st.markdown(f"""<div class="{card_class}">
            <h3>🍴 중식 {'⭐' if is_focus else ''}</h3>
            <p>{menu.get('중식', '정보 없음')}</p>
        </div>""", unsafe_allow_html=True)

    # 석식 카드
    with col2:
        is_focus = (focus_menu == "석식" and selected_day == today_str)
        card_class = "menu-card highlight" if is_focus else "menu-card"
        st.markdown(f"""<div class="{card_class}">
            <h3>🌙 석식 {'⭐' if is_focus else ''}</h3>
            <p>{menu.get('석식', '정보 없음')}</p>
        </div>""", unsafe_allow_html=True)
