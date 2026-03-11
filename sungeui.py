import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
from datetime import datetime
import easyocr
import numpy as np

# 1. API 설정
api_key = st.secrets.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# 2. OCR 기반 분석 함수
def analyze_menu_with_ocr(image):
    # A. 이미지에서 텍스트 추출 (OCR)
    reader = easyocr.Reader(['ko', 'en'])
    img_array = np.array(image)
    ocr_result = reader.readtext(img_array, detail=0)
    extracted_text = " ".join(ocr_result)
    
    # B. 추출된 텍스트를 Gemini에게 전달 (이미지 없이 텍스트만!)
    # 이 방식은 이미지 모델 권한 오류(404)를 원천 차단합니다.
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    아래 텍스트는 식단표를 OCR로 읽은 결과야. 
    여기서 요일별 중식과 석식 메뉴를 정리해서 JSON으로 응답해줘.
    텍스트: {extracted_text}
    형식: {{"월": {{"중식": "..", "석식": ".."}}, ...}}
    """
    
    try:
        response = model.generate_content(prompt)
        res_text = response.text.strip()
        if "{" in res_text:
            res_text = res_text[res_text.find("{"):res_text.rfind("}")+1]
        return json.loads(res_text)
    except Exception as e:
        raise e

# 3. 메인 UI (생략 - 동일)
# ... 버튼 클릭 시 analyze_menu_with_ocr(img) 호출 ...
