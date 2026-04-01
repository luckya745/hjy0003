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
        # 안정적인 분석을 위해 1.5 Flash 모델 권장 (2.5-flash-lite는 최신 실험 모델일 수 있음)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 수집 함수 (상세 페이지 크롤링 개선)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_aks_data(name):
    """검색 결과 리스트에서 첫 번째 항목의 상세 내용을 가져옵니다."""
    encoded_name = urllib.parse.quote(name)
    search_url = f"https://encykorea.aks.ac.kr/Article/Search/{encoded_name}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    try:
        # 1. 검색 결과 페이지 요청
        response = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 2. 검색 결과 목록에서 첫 번째 제목의 링크 찾기
        # 한국학중앙연구원(AKS)의 검색 결과 리스트 내 제목 링크 선택자
        first_item = soup.select_one('.search_list li .title a')
        
        if first_item and 'href' in first_item.attrs:
            detail_url = "https://encykorea.aks.ac.kr" + first_item['href']
            
            # 3. 상세 페이지 요청
            detail_res = requests.get(detail_url, headers=headers, timeout=10)
            detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
            
            # 4. 상세 본문 텍스트 추출 (content_view 클래스나 article 태그 등)
            content_area = detail_soup.find('div', {'class': 'content_view'}) or detail_soup.find('article') or detail_soup.body
            return content_area.get_text(strip=True)[:4000]
        
        return None
    except Exception as e:
        return None

# ---------------------------------------------------------
# 4. AI 분석 함수 (프롬프트 강화)
# ---------------------------------------------------------
@st.cache_data(show_spinner=False, ttl=3600)
def analyze_independence_activist(name, context_text):
    """자료가 부실할 경우 AI의 지식을 병합하여 분석"""
    
    # 자료 존재 여부에 따른 베이스 프롬프트 설정
    if context_text and len(context_text) > 300:
        base_prompt = f"다음 [제공된 자료]를 우선적으로 참고하여 인물 '{name}'을 분석하세요. 만약 자료에 내용이 부족하다면 당신이 알고 있는 역사적 사실을 추가하여 답변하세요.\n\n[제공된 자료]:\n{context_text}"
    else:
        base_prompt = f"당신의 역사적 전문 지식을 바탕으로 일제강점기 인물 '{name}'의 독립운동 노선과 생애를 분석하세요."

    prompt = f"""
    {base_prompt}

    ---
    [분류 기준]: 무장투쟁론, 외교독립론, 실력양성론, 의열투쟁, 친일파, 기타
    [출력 규칙]:
    1. 첫 번째 줄은 반드시 '최종 분류: [분류명]' 형식으로 시작하세요.
    2. 두 번째 줄부터는 해당 인물의 주요 활동, 소속 단체, 독립운동 노선의 특징을 상세히 설명하세요.
    3. 인물의 변절이나 논란이 있는 경우 객관적인 역사적 사실을 바탕으로 서술하세요.
    4. 마크다운 형식을 사용하여 가독성 있게 작성하세요.
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
    target_name = st.text_input("인물 이름", placeholder="예: 안중근, 김구, 이광수")
    user_prediction = st.selectbox(
        "본인이 생각하는 이 인물의 주된 노선은?",
        ["무장투쟁론", "외교독립론", "실력양성론", "의열투쟁", "친일파", "기타"]
    )
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        # 데이터 수집
        with st.spinner(f"🌐 외부 자료(AKS)에서 '{target_name}' 정보를 찾는 중..."):
            history_data = scrape_aks_data(target_name)
        
        # AI 분석
        with st.spinner(f"🤖 AI 분석 중... (새로운 인물일 경우 API를 호출합니다)"):
            full_result = analyze_independence_activist(target_name, history_data)
        
        # 결과 대조 및 파싱
        lines = full_result.strip().split('\n')
        conclusion_line = lines[0]
        detailed_analysis = "\n".join(lines[1:])
        
        # 분류명 추출 (유연하게 매칭)
        actual_faction = "기타"
        for faction in ["무장투쟁론", "외교독립론", "실력양성론", "의열투쟁", "친일파"]:
            if faction in conclusion_line:
                actual_faction = faction
                break
            
        st.subheader(f"📊 분석 결과: {target_name}")
        
        # 정답 여부 확인 UI
        if actual_faction == user_prediction:
            st.success(f"🎯 **정답입니다!** 인물의 주요 노선은 **{actual_faction}**입니다.")
        else:
            st.error(f"🧐 **틀렸습니다.** AI 분석 결과 이 인물은 **{actual_faction}**에 가깝습니다.")

        # 상세 분석 내용 표시
        with st.expander("📝 상세 분석 근거 보기", expanded=True):
            st.markdown(detailed_analysis)
            
        # 데이터 출처 표시
        if history_data:
            st.caption("📍 출처: 한국학중앙연구원(AKS) 한국민족문화대백과사전 자료 기반 분석")
        else:
            st.caption("📍 출처: AI 내부 학습 데이터 기반 분석 (외부 자료 검색 실패)")
