import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="개화파 vs 위정척사파 분류기",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ 개화파 vs 위정척사파 분류기")
st.markdown("---")

# ---------------------------------------------------------
# 2. API 키 설정
# ---------------------------------------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # 모델명은 안정적인 gemini-2.5-flash-lite를 권장합니다.
    model = genai.GenerativeModel('gemini-2.5-flash-lite') 
except Exception as e:
    st.error("⚠️ API 키 설정 오류: .streamlit/secrets.toml 파일에 GEMINI_API_KEY가 있는지 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# 3. 기능 함수 정의
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_history_data(name):
    """국사편찬위원회 데이터베이스 검색"""
    base_url = "https://db.history.go.kr/search/searchResult.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
    }
    params = {'searchKeyword': name, 'limit': '15'}
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = [item.get_text(strip=True) for item in soup.select('.search_list li .cont')[:3]]
        return " ".join(results) if results else None
    except:
        return None

def analyze_figure(name, context_text):
    """Gemini AI 분석 (결론 형식을 엄격히 제한)"""
    prompt = f"""
    당신은 한국사 전문가입니다. 인물 '{name}'을(를) 분석하여 **'개화파'**인지 **'위정척사파'**인지 판별하세요.
    
    [사료 정보]: {context_text if context_text else "제공된 사료 없음. 지식을 바탕으로 분석하시오."}

    [출력 규칙 - 반드시 지킬 것]
    1. 첫 번째 줄에 반드시 '결론: 개화파' 또는 '결론: 위정척사파'라고만 적으세요.
    2. 두 번째 줄부터 핵심 이유와 상세 분석을 마크다운 형식으로 작성하세요.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"결론: 오류\n분석 중 오류 발생: {e}"

# ---------------------------------------------------------
# 4. 화면 구성 (UI)
# ---------------------------------------------------------
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    target_name = st.text_input("인물 이름을 입력하세요", placeholder="예: 김옥균, 최익현")

with col2:
    user_prediction = st.radio(
        "본인이 생각하는 이 인물의 소속은?",
        ["개화파", "위정척사파"],
        horizontal=True
    )

with col3:
    st.write("")
    st.write("")
    run_btn = st.button("분석 실행", type="primary", use_container_width=True)

if run_btn and target_name:
    st.divider()
    
    history_context = scrape_history_data(target_name)
    
    with st.spinner(f"🤖 '{target_name}' 분석 중..."):
        full_result = analyze_figure(target_name, history_context)
    
    # --- 논리 오류 수정 부분 ---
    # 1. AI 답변에서 첫 줄(결론 줄)만 분리
    lines = full_result.strip().split('\n')
    conclusion_line = lines[0]  # 예: "결론: 개화파"
    detailed_analysis = "\n".join(lines[1:]) # 나머지 상세 분석

    # 2. 정확한 결론 키워드 추출
    actual_faction = ""
    if "개화파" in conclusion_line:
        actual_faction = "개화파"
    elif "위정척사파" in conclusion_line:
        actual_faction = "위정척사파"

    # 3. 결과 판정 및 출력
    st.subheader(f"📊 분석 결과: {target_name}")

    if actual_faction == user_prediction:
        st.success(f"🎯 **맞았습니다!** '{target_name}'님은 사용자의 예측대로 **{actual_faction}** 성향의 인물입니다.")
    else:
        st.error(f"🧐 **틀렸습니다.** 사용자는 '{user_prediction}'로 예측했으나, 실제로는 **{actual_faction}** 성향의 인물입니다.")

    # 상세 내용 표시
    with st.container(border=True):
        st.info("💡 분석 근거" if history_context else "⚠️ AI 지식 기반 분석 (사료 검색 실패)")
        st.markdown(detailed_analysis)
    
    if history_context:
        with st.expander("📜 참고 사료 보기"):
            st.text(history_context)
