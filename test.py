import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date, timedelta
import pytz
import io

# 1. 페이지 설정 및 레이아웃 교정
st.set_page_config(page_title="성의교정 대관 현황 조회", page_icon="📋", layout="wide")

st.markdown("""
    <style>
    /* 1. 타이틀 잘림 방지: 상단 여백을 넉넉히 4rem으로 조정 */
    .block-container { 
        padding-top: 4rem !important; 
        padding-bottom: 2rem !important; 
        max-width: 800px; /* 모바일 가독성을 위해 최대폭 제한 (선택사항) */
        margin: 0 auto;
    }
    
    /* 타이틀 디자인 */
    .main-title {
        font-size: 20px !important;
        font-weight: bold;
        color: #333;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
        line-height: 1.2;
    }
    .main-title span { margin-right: 10px; font-size: 24px; }

    /* 남색 엑셀 버튼 디자인 유지 */
    div.stDownloadButton > button {
        background-color: #1e3a5f !important;
        color: white !important;
        border-radius: 8px !important;
        height: 45px !important;
        font-weight: bold !important;
        width: 100%;
        border: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# ... (중간 get_shift, get_data 함수는 기존과 동일) ...

# --- 메인 화면 ---
st.markdown('<div class="main-title"><span>📋</span> 성의교정 대관 현황 조회</div>', unsafe_allow_html=True)

df = get_data(s_date, e_date)

if not df.empty:
    # 엑셀 다운로드 버튼 (중복 생성 방지를 위해 상단에 배치)
    excel_out = io.BytesIO()
    with pd.ExcelWriter(excel_out, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False)
    st.download_button("📊 조회 결과 엑셀 파일 다운로드", data=excel_out.getvalue(), file_name=f"현황.xlsx", use_container_width=True)

    for d_str in sorted(df['full_date'].unique()):
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        # 날짜 헤더 (회색 바)
        st.markdown(f"""
            <div style="background-color:#555; color:white; padding:8px; border-radius:6px; text-align:center; margin: 15px 0 10px 0; font-weight:bold; font-size:14px;">
                📅 {d_str} | {get_shift(d_obj)}
            </div>
        """, unsafe_allow_html=True)
        
        for bu in sel_bu:
            # 건물 필터링 로직 수정 (공백 제거 후 비교)
            b_df = df[(df['full_date'] == d_str) & (df['건물명'].str.replace(" ", "") == bu.replace(" ", ""))]
            
            if not b_df.empty:
                st.markdown(f"""
                    <div style="display:flex; justify-content:space-between; align-items:flex-end; border-bottom:2px solid #1e3a5f; padding:5px 0; margin-top:15px;">
                        <div style="font-size:16px; font-weight:bold; color:#1e3a5f;">🏢 {bu}</div>
                        <div style="font-size:12px; color:#666; margin-bottom:2px;">총 {len(b_df)}건</div>
                    </div>
                """, unsafe_allow_html=True)

                if v_mode == "PC":
                    st.dataframe(b_df[['장소', '시간', '행사명', '부서', '상태']], use_container_width=True, hide_index=True)
                else:
                    for _, r in b_df.iterrows():
                        # [핵심 수정] 
                        # 1. white-space: nowrap으로 상태 배지 줄바꿈 강제 방지
                        # 2. 우측 정렬 및 너비 고정으로 텍스트 겹침 방지
                        st.markdown(f"""
                            <div style="padding:12px 0; border-bottom:1px solid #eee;">
                                <div style="display:flex; justify-content:space-between; align-items:flex-start; gap: 10px;">
                                    <div style="flex: 1; min-width: 0;">
                                        <div style="font-weight:bold; color:#333; font-size:15px; word-break:break-all;">📍 {r['장소']}</div>
                                    </div>
                                    <div style="text-align:right; flex-shrink:0;">
                                        <div style="font-size:13px; margin-bottom:4px;">
                                            <span style="color:#666;">🕒</span> <span style="color:#e74c3c; font-weight:bold; white-space:nowrap;">{r['시간']}</span>
                                        </div>
                                        <div style="background-color:{'#27ae60' if r['상태']=='확정' else '#95a5a6'}; 
                                                    color:white; padding:3px 8px; border-radius:4px; font-size:11px; 
                                                    display:inline-block; font-weight:bold; white-space:nowrap;">
                                            {r['상태']}
                                        </div>
                                    </div>
                                </div>
                                <div style="font-size:12px; color:#777; margin-top:6px; line-height:1.4;">
                                    <span style="margin-right:4px;">📄</span> {r['행사명']} <span style="color:#ccc;">|</span> {r['부서']}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            # 데이터가 없는 건물은 모바일 가독성을 위해 생략하거나 아주 흐리게 표시
else:
    st.info("해당 날짜에 대관 내역이 없습니다.")
