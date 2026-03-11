import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="스마트 식단 매니저", layout="centered")

# 2. API 키 설정 (새로 발급받은 키가 Secrets에 있어야 합니다)
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 없습니다.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 식단 분석 함수 (자동 모델 전환 로직 탑재)
def analyze_menu(image_bytes):
    # 시도해볼 모델 이름 목록 (최신순/안정순)
    # 404 에러를 피하기 위해 다양한 표기법을 순차적으로 시도합니다.
    model_candidates = [
        'gemini-1.5-flash', 
        'gemini-1.5-pro', 
        'models/gemini-1.5-flash',
        'gemini-pro-vision'
    ]
    
    prompt = """
    이미지에서 요일별 식단(중식, 석식)을 추출해서 JSON으로만 응답해줘.
    형식: {"월": {"중식": "..", "석식": "..", "인사": ".."}, "화": {...}}
    """
    
    last_exception = None
    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": image_bytes}
            ])
            
            res_text = response.text.strip()
            if "{" in res_text:
                res_text = res_text[res_text.find("{"):res_text.rfind("}")+1]
            return json.loads(res_text)
            
        except Exception as e:
            last_exception = e
            continue # 실패 시 다음 모델로 자동 시도
            
    # 모든 모델이 실패했을 경우에만 에러를 던집니다.
    raise last_exception

# 4. 메인 UI
st.title("🍱 성의교정 스마트 식단 매니저")
st.write("모델 자동 전환 기능을 추가하여 안정성을 극대화했습니다.")

uploaded_file = st.file_uploader("주간 식단표 이미지를 올려주세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    img_display = Image.open(uploaded_file)
    st.image(img_display, caption="업로드된 식단표", use_container_width=True)
    image_bytes = uploaded_file.getvalue()
    
    if st.button("🚀 식단 분석 시작"):
        with st.spinner('가장 안정적인 모델을 찾아 분석 중입니다...'):
            try:
                result = analyze_menu(image_bytes)
                st.session_state['menu_data'] = result
                st.success("✅ 분석 성공!")
                st.rerun()
            except Exception as e:
                err_msg = str(e)
                st.error(f"❌ 최종 오류 발생: {err_msg}")
                if "404" in err_msg:
                    st.info("💡 구글 API 설정에서 모델 사용 권한을 확인해야 합니다. (Google AI Studio에서 키 확인)")
                elif "429" in err_msg:
                    st.info("💡 할당량 초과입니다. 5분 뒤에 다시 시도해 주세요.")

# 5. 결과 표시
if 'menu_data' in st.session_state:
    days = ["월", "화", "수", "목", "금", "토", "일"]
    today_str = days[datetime.now().weekday()]
    
    st.divider()
    st.header(f"📅 오늘의 식단 ({today_str}요일)")
    
    menu = st.session_state['menu_data'].get(today_str, {})
    if menu:
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"🍴 **중식**\n\n{menu.get('중식', '정보 없음')}")
        with col2:
            st.error(f"🌙 **석식**\n\n{menu.get('석식', '정보 없음')}")
        if menu.get("인사"):
            st.chat_message("assistant").write(menu["인사"])
