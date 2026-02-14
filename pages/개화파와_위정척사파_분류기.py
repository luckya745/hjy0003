import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 1. 페이지 설정 (이 파일만의 설정)
# ---------------------------------------------------------
st.set_page_config(
    page_title="개화파 vs 위정척사파 분류기",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ 개화파 vs 위정척사파 분류기")
st.markdown("---")
st.info("💡 국사편찬위원회 사료를 분석하여 개화파와 위정척사파 성향을 판단합니다.")

# ---------------------------------------------------------
# 2. API 키 설정 (app.py와 공유되는 secrets 사용)
# ---------------------------------------------------------
try:
    # streamlit secrets에서 키를 가져옵니다.
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception as e:
    st.error("⚠️ API 키 설정 오류: .streamlit/secrets.toml 파일에 GEMINI_API_KEY가 있는지 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# 3. 기능 함수 정의 (스크래핑 & AI 분석)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_history_data(name):
    """국사편찬위원회 데이터베이스 검색"""
    base_url = "https://db.history.go.kr/search/searchResult.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://db.history.go.kr/'
    }
    params = {'searchKeyword': name, 'limit': '20'}

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=5)
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        # 검색 결과 추출 시도
        list_items = soup.select('.search_list li .cont')
        if not list_items:
            list_items = soup.select('.result_list li')

        for item in list_items[:3]:
            text = item.get_text(strip=True)
            if len(text) > 30: results.append(text)

        return " ".join(results) if results else None
    except:
        return None

def analyze_figure(name, context_text):
    """Gemini AI 분석"""
    if context_text:
        # 사료가 있을 때 (RAG)
        prompt = f"""
        당신은 한국 근대사 역사학자입니다. 
        아래 [사료]를 바탕으로 인물 '{name}'의 성향을 분석하세요.

        [사료]: {context_text[:2500]}
        
        [지시사항]
        1. 이 인물이 **'개화파(급진/온건)'**인지 **'위정척사파'**인지 명확히 분류하세요.
        2. 판단 근거를 사료 내용을 인용하여 설명하세요.
        """
        source_type = "📚 사료 기반 분석"
    else:
        # 사료가 없을 때 (AI 지식)
        prompt = f"""
        당신은 한국사 전문가입니다. 인물 '{name}'에 대해 알고 있는 지식을 바탕으로 분석하세요.
        
        [지시사항]
        1. 이 인물이 **'개화파'**인지 **'위정척사파'**인지 분류하세요.
        2. 해당 파벌로 분류되는 결정적인 역사적 사건이나 주장을 설명하세요.
        """
        source_type = "🧠 AI 지식 기반 분석 (사료 검색 실패)"

    prompt += "\n출력 형식: 마크다운으로 **결론**, **핵심 이유**, **상세 분석** 순으로 작성해주세요."

    try:
        response = model.generate_content(prompt)
        return response.text, source_type
    except Exception as e:
        return f"분석 중 오류 발생: {e}", "Error"

# ---------------------------------------------------------
# 4. 화면 구성 (UI)
# ---------------------------------------------------------
col1, col2 = st.columns([3, 1])
with col1:
    target_name = st.text_input("인물 이름을 입력하세요", placeholder="예: 김옥균, 최익현, 민영익")
with col2:
    st.write("")
    st.write("")
    run_btn = st.button("분석 실행", type="primary", use_container_width=True)

if run_btn and target_name:
    st.divider()
    
    # 1. 검색 단계
    with st.status("🕵️ 역사 데이터베이스 검색 중...") as status:
        history_context = scrape_history_data(target_name)
        if history_context:
            status.update(label="✅ 사료 데이터 확보 성공!", state="complete")
        else:
            status.update(label="⚠️ 사료 검색 실패 (AI 지식으로 전환)", state="complete")
            
    # 2. 분석 단계
    with st.spinner(f"🤖 Gemini가 '{target_name}'의 성향을 분석하고 있습니다..."):
        result, mode = analyze_figure(target_name, history_context)

    # 3. 결과 출력
    st.subheader(f"📊 분석 결과: {target_name}")
    if "사료" in mode:
        st.success(mode)
    else:
        st.warning(mode)
        
    st.markdown(result)
    
    # 사료 원문 보기
    if history_context:
        with st.expander("📜 참고한 사료 원문 보기"):
            st.text(history_context)
