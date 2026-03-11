import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="스마트 식단 매니저", layout="centered")

# 2. API 키 설정 (새로 발급받은 키가 등록되어 있어야 합니다)
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'가 없습니다.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 식단 분석 함수 (이중 모델 전략)
def analyze_menu(image_bytes):
    # 시도해볼 모델 목록 (첫 번째가 실패하면 두 번째로 시도)
    model_names = ['gemini-1.5-flash', 'gemini-pro-vision']
    
    prompt = """
    이미지에서 요일별 식단(중식, 석식)을 추출해서 JSON으로만 응답해줘.
    형식: {"월": {"중식": "..", "석식": "..", "인사": ".."}, "화": {...}}
    """
    
    last_error = None
    for name in model_names:
        try:
            model = genai.GenerativeModel(name)
            response = model.generate_content([
                prompt,
                {"mime_type": "image/jpeg", "data": image_bytes}
            ])
            
            res_text = response.text.strip()
            if "{" in res_text:
                res_text = res_text[res_text.find("{"):res_text.rfind("}")+1]
            return json.loads(res_text)
            
        except Exception as e:
            last_error = e
            continue  # 다음 모델로 재시도
            
    raise last_error

# 4. 메인 UI
st.title("🍱 성의교정 스마트 식단 매니저")
st.write("이미지를 바이트 방식으로 분석하여 안정성을 높였습니다.")

uploaded_file = st.file_uploader("주간 식단표 이미지를 올려주세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    img_display = Image.open(uploaded_file)
    st.image(img_display, caption="업로드된 식단표", use_container_width=True)
    
    # 분석용 바이트 데이터 추출
    image_bytes = uploaded_file.getvalue()
    
    if st.button("🚀 식단 분석 시작"):
        with st.spinner('AI가 여러 모델을 교차 확인하며 분석 중입니다...'):
            try:
                result = analyze_menu(image_bytes)
                st.session_state['menu_data'] = result
                st.success("✅ 분석에 성공했습니다!")
                st.rerun()
            except Exception as e:
                err_msg = str(e)
                st.error(f"❌ 최종 오류: {err_msg}")
                if "404" in err_msg:
                    st.info("💡 모델 인식 문제입니다. 잠시 후 서버가 안정화되면 다시 시도해 주세요.")
                elif "429" in err_msg:
                    st.info("💡 할당량 초과입니다. 5분 뒤에 시도해 주세요.")

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
    else:
        st.warning(f"{today_str}요일 식단 정보가 분석 결과에 없습니다.")
