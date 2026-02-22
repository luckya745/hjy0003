import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import urllib.parse

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="세계사 인물 검색기",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 세계사 인물 백과사전")
st.markdown("---")
st.info("💡 동일한 인물에 대한 재검색 시 API를 호출하지 않고 캐싱된 분석 결과를 불러옵니다.")

# ---------------------------------------------------------
# 2. API 키 설정
# ---------------------------------------------------------
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash') # 안정적인 flash 모델 권장
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 위키백과 스크래핑 함수 (캐싱 적용됨)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def get_wiki_data(name):
    encoded_name = urllib.parse.quote(name)
    url = f"https://ko.wikipedia.org/wiki/{encoded_name}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200: return None, None
        soup = BeautifulSoup(response.text, 'html.parser')
        
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        text_data = ""
        if content_div:
            paragraphs = content_div.find_all('p')
            for p in paragraphs: text_data += p.get_text() + "\n"
            text_data = text_data[:6000]

        image_url = None
        infobox = soup.select_one('.infobox img') or soup.select_one('.mw-parser-output .thumb img')
        if infobox:
            img_src = infobox.get('src')
            image_url = "https:" + img_src if img_src.startswith('//') else img_src

        return text_data, image_url
    except: return None, None

# ---------------------------------------------------------
# 4. AI 분석 함수 (Gemini API 캐싱 추가)
# ---------------------------------------------------------
# show_spinner=False로 설정하여 캐시된 데이터를 불러올 때 불필요한 로딩창을 방지합니다.
@st.cache_data(ttl=3600, show_spinner=False)
def analyze_wiki_text(name, wiki_text):
    """
    인물 이름과 위키 텍스트가 이전 요청과 동일하면 API 호출 없이 결과를 반환합니다.
    """
    prompt = f"""
    당신은 세계사 전문 역사 선생님입니다. 
    아래 [위키백과 텍스트]를 바탕으로 인물 '{name}'에 대해 학생들에게 설명하듯 정리해주세요.

    [위키백과 텍스트]
    {wiki_text}

    [출력 형식]
    마크다운을 사용하여 한 줄 소개, 기본 정보, 주요 업적(3가지), 역사적 평가, 흥미로운 사실 순으로 작성하세요.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"분석 중 오류 발생: {e}"

# ---------------------------------------------------------
# 5. UI 구성
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔍 인물 검색")
    target_name = st.text_input("인물 이름", placeholder="예: 나폴레옹, 칭기즈 칸")
    search_btn = st.button("검색 및 분석 시작", type="primary", use_container_width=True)

with col2:
    if search_btn and target_name:
        st.divider()
        
        # 위키 데이터 수집 (캐시 적용)
        with st.status(f"🌐 데이터 찾는 중...", expanded=False):
            wiki_text, img_url = get_wiki_data(target_name)
        
        if not wiki_text:
            st.error("문서를 찾을 수 없습니다. 이름을 확인해주세요.")
            st.stop()
        
        st.subheader(f"📜 {target_name} 분석 결과")
        
        # 레이아웃 배치
        img_col, text_col = st.columns([1, 2])
        
        # AI 분석 실행 (캐시 적용)
        with st.spinner("🤖 Gemini가 내용을 정리 중입니다..."):
            result_text = analyze_wiki_text(target_name, wiki_text)
            
        if img_url:
            with img_col:
                st.image(img_url, caption=target_name, use_container_width=True)
            with text_col:
                st.markdown(result_text)
        else:
            st.markdown(result_text)

        with st.expander("📚 출처 및 원문 보기"):
            st.text(wiki_text[:500] + "...")
