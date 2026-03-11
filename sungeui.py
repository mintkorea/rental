import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="스마트 식단 매니저", layout="centered")

# 2. API 키 설정 (신규 키가 등록되어 있어야 합니다)
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("⚠️ Streamlit Secrets에 'GEMINI_API_KEY'를 등록해주세요.")
    st.stop()

genai.configure(api_key=api_key)

# 3. 식단 분석 함수 (이미지를 바이트 데이터로 직접 전달)
def analyze_menu(image_bytes):
    # 가장 안정적인 기본 모델명을 사용합니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = """
    이미지에서 요일별 식단(중식, 석식)을 추출해서 JSON으로 응답해줘.
    형식: {"월": {"중식": "..", "석식": "..", "인사": ".."}, "화": {...}}
    반드시 마크다운(```json) 기호 없이 순수 JSON 데이터만 출력해.
    """
    
    try:
        # 이미지를 바이트 데이터와 MIME 타입을 포함한 딕셔너리 형태로 전달
        response = model.generate_content([
            prompt,
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])
        
        res_text = response.text.strip()
        
        # JSON 데이터 클렌징 (AI가 추가 설명을 붙일 경우 대비)
        if "{" in res_text:
            res_text = res_text[res_text.find("{"):res_text.rfind("}")+1]
            
        return json.loads(res_text)
    except Exception as e:
        raise e

# 4. 메인 UI
st.title("🍱 성의교정 스마트 식단 매니저")
st.write("식단표 이미지를 업로드하면 오늘 메뉴를 쏙 뽑아드려요!")

uploaded_file = st.file_uploader("주간 식단표 이미지를 올려주세요", type=['png', 'jpg', 'jpeg'])

if uploaded_file:
    # 1. 화면 표시용 이미지 객체 생성
    img_display = Image.open(uploaded_file)
    st.image(img_display, caption="업로드된 식단표", use_container_width=True)
    
    # 2. 분석용 바이트 데이터 추출
    image_bytes = uploaded_file.getvalue()
    
    if st.button("🚀 식단 분석 시작"):
        with st.spinner('새로운 방식으로 이미지를 분석 중입니다...'):
            try:
                # 분석 함수에 바이트 데이터를 전달합니다.
                result = analyze_menu(image_bytes)
                st.session_state['menu_data'] = result
                st.success("✅ 분석 완료!")
                st.rerun()
            except Exception as e:
                err_msg = str(e)
                st.error(f"❌ 오류 발생: {err_msg}")
                # 에러 메시지별 안내
                if "404" in err_msg:
                    st.info("💡 모델 인식 오류입니다. 이 방식에서도 에러가 나면 모델명을 'gemini-pro-vision'으로 바꿔보겠습니다.")
                elif "429" in err_msg:
                    st.info("💡 할당량 초과입니다. 약 5분 뒤에 다시 시도해 주세요.")

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
    else:
        st.warning(f"{today_str}요일 식단 정보가 없습니다.")
        
    with st.expander("📝 전체 데이터 보기"):
        st.json(st.session_state['menu_data'])
