import streamlit as st
import google.generativeai as genai
from google.cloud import vision
import json
from datetime import datetime

# 1. API 설정
# Gemini 키와 Google Cloud Vision 키(JSON)가 모두 필요할 수 있습니다.
api_key = st.secrets.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 2. Vision API를 이용한 텍스트 추출 함수
def get_text_from_vision(image_bytes):
    # Streamlit Secrets에 저장된 서비스 계정 키를 사용합니다.
    client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    response = client.text_detection(image=image)
    texts = response.text_annotations
    return texts[0].description if texts else ""

# 3. 추출된 텍스트를 Gemini로 분석하는 함수
def analyze_menu_text(extracted_text):
    # 이미지가 아닌 '텍스트'만 보내기 때문에 404 에러가 나지 않습니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"""
    아래는 식단표 이미지에서 추출한 텍스트야. 요일별 중식, 석식 메뉴를 JSON으로 정리해줘.
    텍스트: {extracted_text}
    형식: {{"월": {{"중식": "..", "석식": ".."}}, ...}}
    """
    response = model.generate_content(prompt)
    return json.loads(response.text)

# 4. 메인 UI (버튼 클릭 시 위 함수들을 순차 실행)
