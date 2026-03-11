import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="스마트 식단 매니저", layout="centered")

# 2. API 키 설정 (image_c359dc.png에서 확인된 키를 사용합니다)
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Secrets에 'GEMINI_API_KEY'가 없습니다.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 식단 분석 함수 (성공할 때까지 모델을 바꿔가며 시도)
def analyze_menu(image_bytes):
    # 404 에러를 피하기 위해 가능한 모든 모델 이름을 리스트에 넣었습니다.
    model_list = [
        'gemini-1.5-flash', 
        'gemini-1.5-pro', 
        'gemini-pro-vision',
        'models/gemini-1.5-flash'
    ]
    
    prompt = """
    이미지에서 요일별 식단(중식, 석식)을 추출해서 JSON으로 응답해줘.
    형식: {"월": {"중식": "..", "석식": "..", "인사": ".."}, "화": {...}}
    반드시 마크다운 없이 순수 JSON 데이터만 출력해.
    """
    
    last_err = None
    for model_name in model_list:
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
            last_err = e
            continue # 실패하면 다음 모델명으로 즉시 재시도
            
    raise last_err

# 4. 메인 UI
st.title("🍱 성의교정 스마트 식단 매니저")
st.write("모델 자동 매칭 기능을 적용하여 404 에러를 방어합니다.")

uploaded_file = st.file_uploader("주간 식단표 이미지를 올려주세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    img_display = Image.open(uploaded_file)
    st.image(img_display, caption="업로드된 식단표", use_container_width=True)
    image_bytes = uploaded_file.getvalue()
    
    if st.button("🚀 식단 분석 시작"):
        with st.spinner('가장 적합한 AI 모델을 찾는 중입니다...'):
            try:
                result = analyze_menu(image_bytes)
                st.session_state['menu_data'] = result
                st.success("✅ 드디어 분석에 성공했습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ 모든 모델 시도 실패: {str(e)}")
                st.info("💡 이 문제가 지속되면 새 구글 계정으로 API 키를 발급받는 것이 유일한 해결책입니다.")

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
