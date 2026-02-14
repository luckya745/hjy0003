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
st.info("💡 위키백과(Wikipedia)의 방대한 데이터를 Gemini가 요약·정리해 드립니다.")

# ---------------------------------------------------------
# 2. API 키 설정 (메인 app.py와 연동)
# ---------------------------------------------------------
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        # 속도가 빠른 Flash 모델 사용 권장
        model = genai.GenerativeModel('gemini-2.5-flash')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 위키백과 스크래핑 함수 (텍스트 + 이미지)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def get_wiki_data(name):
    """
    위키백과에서 텍스트와 대표 이미지를 가져옵니다.
    """
    # URL 인코딩 (한글 -> %EB%82...)
    encoded_name = urllib.parse.quote(name)
    url = f"https://ko.wikipedia.org/wiki/{encoded_name}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        
        # 404 등 에러 체크
        if response.status_code != 200:
            return None, None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. 본문 텍스트 추출
        content_div = soup.find('div', {'class': 'mw-parser-output'})
        text_data = ""
        if content_div:
            # 모든 p 태그의 텍스트를 수집
            paragraphs = content_div.find_all('p')
            for p in paragraphs:
                text_data += p.get_text() + "\n"
            text_data = text_data[:6000] # 너무 길면 토큰 제한, 적절히 자름

        # 2. 대표 이미지 추출 (정보상자 infobox 내부의 이미지 시도)
        image_url = None
        infobox = soup.select_one('.infobox img') # 정보상자 내 이미지
        if not infobox:
            infobox = soup.select_one('.mw-parser-output .thumb img') # 썸네일 이미지

        if infobox:
            img_src = infobox.get('src')
            if img_src.startswith('//'):
                image_url = "https:" + img_src
            elif img_src.startswith('http'):
                image_url = img_src

        return text_data, image_url

    except Exception as e:
        return None, None

# ---------------------------------------------------------
# 4. AI 분석 함수
# ---------------------------------------------------------
def analyze_wiki_text(name, wiki_text):
    """Gemini를 이용한 요약 및 분석"""
    
    prompt = f"""
    당신은 세계사 전문 역사 선생님입니다. 
    아래 [위키백과 텍스트]를 바탕으로 인물 '{name}'에 대해 학생들에게 설명하듯 정리해주세요.

    [위키백과 텍스트]
    {wiki_text}

    [출력 형식]
    반드시 마크다운(Markdown)을 사용하세요.
    
    1. **한 줄 소개**: (이 인물을 가장 잘 나타내는 한 문장)
    2. **기본 정보**:
       - **출생-사망**: (연도)
       - **국적/시대**: (국가 및 활동 시기)
       - **직업**: (황제, 장군, 예술가 등)
    3. **주요 업적 (3가지)**:
       - (업적 1)
       - (업적 2)
       - (업적 3)
    4. **역사적 평가**: (긍정적 평가와 부정적 평가 혹은 의의를 간단히 서술)
    5. **흥미로운 사실**: (교과서에 잘 안 나오는 재미있는 일화 1가지, 텍스트에 없다면 생략 가능)
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
    target_name = st.text_input("인물 이름 (예: 나폴레옹, 칭기즈 칸, 간디)", placeholder="정확한 명칭을 입력하세요")
    
    st.info("""
    **💡 검색 팁**
    - '이순신' (O)
    - '나폴레옹 1세' (O)
    - 별명보다는 **공식 명칭**이 정확합니다.
    """)
    
    search_btn = st.button("검색 및 분석", type="primary", use_container_width=True)

with col2:
    if search_btn and target_name:
        st.divider()
        
        # 1. 데이터 수집
        with st.status(f"🌐 위키백과에서 '{target_name}' 찾는 중...", expanded=True) as status:
            wiki_text, img_url = get_wiki_data(target_name)
            
            if wiki_text:
                status.update(label="✅ 데이터 수집 완료! AI 분석을 시작합니다.", state="complete", expanded=False)
            else:
                status.update(label="❌ 문서를 찾을 수 없습니다.", state="error")
                st.error("위키백과에 해당 문서가 없거나 이름이 정확하지 않습니다.")
                st.stop()
        
        # 2. 결과 출력 레이아웃
        # 상단: 이미지와 기본 요약 병렬 배치
        
        st.subheader(f"📜 {target_name} 분석 결과")
        
        result_container = st.container()
        
        # 이미지가 있으면 표시
        if img_url:
            col_img, col_desc = st.columns([1, 2])
            with col_img:
                st.image(img_url, caption=target_name, use_column_width=True)
            with col_desc:
                with st.spinner("🤖 Gemini가 열심히 요약하고 있습니다..."):
                    result_text = analyze_wiki_text(target_name, wiki_text)
                    st.markdown(result_text)
        else:
            # 이미지가 없으면 텍스트만 넓게 표시
            with st.spinner("🤖 Gemini가 열심히 요약하고 있습니다..."):
                result_text = analyze_wiki_text(target_name, wiki_text)
                st.markdown(result_text)

        # 3. 원본 텍스트 확인 (접기/펼치기)
        with st.expander("📚 위키백과 원문 텍스트 보기 (일부)"):
            st.text(wiki_text[:1000] + "\n... (중략) ...")
            st.caption(f"출처: 위키백과 ({target_name})")

    elif search_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
