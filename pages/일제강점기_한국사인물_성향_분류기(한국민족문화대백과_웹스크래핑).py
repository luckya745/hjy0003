import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import urllib.parse

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="일제강점기 인물 성향 분류기",
    page_icon="🇰🇷",
    layout="wide"
)

st.title("🇰🇷 일제강점기 인물 성향 분류기")
st.markdown("---")
st.info("💡 동일한 인물에 대한 재분석 시 API 호출 없이 캐싱된 결과를 불러옵니다.")

# ---------------------------------------------------------
# 2. API 키 및 모델 설정
# ---------------------------------------------------------
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 수집 함수 (기존 캐싱 유지)
# ---------------------------------------------------------
@st.cache_data(ttl=3600) # 1시간 동안 결과 유지
def scrape_aks_data(name):
    encoded_name = urllib.parse.quote(name)
    url = f"https://encykorea.aks.ac.kr/Article/Search/{encoded_name}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        content_area = soup.find('div', {'class': 'search_list'}) or soup.body
        return content_area.get_text(strip=True)[:4000]
    except: return None

# ---------------------------------------------------------
# 4. AI 분석 함수 (Gemini API 캐싱 추가)
# ---------------------------------------------------------
# 인물 이름과 수집된 사료 내용이 같으면 이전에 생성된 결과를 그대로 반환합니다.
@st.cache_data(show_spinner=False, ttl=3600)
def analyze_independence_activist(name, context_text):
    """Gemini API 호출 결과를 캐싱하여 호출 횟수 절약"""
    if context_text:
        base_prompt = f"다음 [자료]를 바탕으로 인물 '{name}'을 분석하세요.\n[자료]: {context_text}"
    else:
        base_prompt = f"당신의 역사적 지식을 바탕으로 일제강점기 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}
    [분류 기준]: 무장투쟁론, 외교독립론, 실력양성론, 의열투쟁, 친일파, 기타
    [출력 형식]: 
    첫 번째 줄: 최종 분류: [분류명]
    두 번째 줄 이하: 핵심 근거와 상세 분석 (마크다운)
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"최종 분류: 오류\n오류 내용: {e}"

# ---------------------------------------------------------
# 5. UI 구성 및 로직
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔍 인물 입력 및 예측")
    target_name = st.text_input("인물 이름", placeholder="예: 안중근, 이광수")
    user_prediction = st.selectbox(
        "본인이 생각하는 이 인물의 주된 노선은?",
        ["무장투쟁론", "외교독립론", "실력양성론", "의열투쟁", "친일파", "기타"]
    )
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        # 데이터 수집 (캐싱 적용됨)
        history_data = scrape_aks_data(target_name)
        
        # AI 분석 (캐싱 적용됨)
        with st.spinner(f"🤖 '{target_name}' 분석 중... (새로운 인물일 경우 API를 호출합니다)"):
            full_result = analyze_independence_activist(target_name, history_data)
        
        # 결과 대조
        lines = full_result.strip().split('\n')
        conclusion_line = lines[0]
        detailed_analysis = "\n".join(lines[1:])
        
        actual_faction = "기타"
        for faction in ["무장투쟁론", "외교독립론", "실력양성론", "의열투쟁", "친일파"]:
            if faction in conclusion_line:
                actual_faction = faction
                break
            
        st.subheader(f"📊 분석 결과: {target_name}")
        if actual_faction == user_prediction:
            st.success(f"🎯 **정답입니다!** ({actual_faction})")
        else:
            st.error(f"🧐 **틀렸습니다.** 분석 결과는 **{actual_faction}**입니다.")

        st.markdown(detailed_analysis)
