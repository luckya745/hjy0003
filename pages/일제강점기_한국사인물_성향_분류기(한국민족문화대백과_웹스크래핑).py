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
st.info("💡 한국민족문화대백과사전 데이터를 기반으로 독립운동 노선(무장, 외교, 실력양성) 또는 친일 행적을 분석합니다.")

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
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 수집 함수 (한국민족문화대백과사전)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_aks_data(name):
    """한국민족문화대백과사전 검색 결과 스크래핑"""
    
    # URL 인코딩 (한글 이름 처리)
    encoded_name = urllib.parse.quote(name)
    # 한국민족문화대백과 통합검색 URL
    url = f"https://encykorea.aks.ac.kr/Article/Search/{encoded_name}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://encykorea.aks.ac.kr/'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 검색 결과 텍스트 추출 (사이트 구조에 따라 유연하게 대처)
        # 검색 결과의 요약문이나 본문 내용을 가져옵니다.
        results = []
        
        # 일반적인 본문 컨테이너 시도
        content_area = soup.find('div', {'class': 'search_list'})
        if not content_area:
            content_area = soup.body

        # 텍스트 추출 및 정제
        text_content = content_area.get_text(strip=True)
        
        # 너무 짧으면(검색결과 없음 등) 실패 처리
        if len(text_content) < 50:
            return None

        return text_content[:4000] # 토큰 제한 고려하여 자름

    except Exception as e:
        return None

# ---------------------------------------------------------
# 4. AI 분석 함수
# ---------------------------------------------------------
def analyze_independence_activist(name, context_text):
    """Gemini를 이용한 성향 분류"""
    
    if context_text:
        source_mode = "📚 한국민족문화대백과사전 기반 분석"
        base_prompt = f"다음 [자료]를 바탕으로 인물 '{name}'을 분석하세요.\n[자료]: {context_text}"
    else:
        source_mode = "🧠 AI 지식 기반 분석 (자료 검색 실패)"
        base_prompt = f"당신의 역사적 지식을 바탕으로 일제강점기 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}

    [분류 기준]
    일제강점기 활동 양상에 따라 다음 중 하나로 분류하세요.
    1. **무장투쟁론 (Armed Struggle)**: 만주/연해주 등에서 무력으로 독립 쟁취 (예: 김좌진, 홍범도, 김원봉)
    2. **외교독립론 (Diplomatic Independence)**: 국제 사회의 지지를 통해 독립 달성 (예: 이승만, 김규식)
    3. **실력양성론 (Cultural/Ability Enhancement)**: 교육, 산업 육성으로 민족의 힘 기르기 (예: 안창호, 이광수 초기)
    4. **의열투쟁 (Heroic Struggle)**: 요인 암살, 기관 파괴 등 직접 행동 (예: 김구, 윤봉길, 이봉창)
    5. **친일파 (Pro-Japanese)**: 변절하거나 적극적으로 일제에 협력 (예: 이완용, 송병준)
    6. **기타**: 위 분류에 속하지 않거나 복합적인 경우

    [지시사항]
    1. 위 기준에 따라 인물을 **가장 주된 성향**으로 분류하세요.
    2. 판단의 근거가 되는 주요 단체, 사건, 활동을 구체적으로 명시하세요.

    [출력 형식]
    마크다운(Markdown)을 사용하여 작성하세요.
    - **최종 분류**: [분류명]
    - **핵심 근거**: [한 문장 요약]
    - **상세 분석**: (활동 내역 및 노선 설명)
    """

    try:
        response = model.generate_content(prompt)
        return response.text, source_mode
    except Exception as e:
        return f"분석 중 오류 발생: {e}", "Error"

# ---------------------------------------------------------
# 5. UI 구성
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔍 인물 입력")
    target_name = st.text_input("인물 이름 (예: 김구, 안창호, 이완용)", placeholder="이름을 입력하세요")
    
    st.markdown("### ℹ️ 노선 설명")
    with st.expander("🔫 무장투쟁 / 의열투쟁"):
        st.write("직접적인 무력 사용이나 요인 암살 등을 통해 독립을 쟁취하려 했던 노선입니다.")
    with st.expander("🌍 외교독립론"):
        st.write("미국, 유럽 등 열강의 외교적 지원을 통해 독립을 달성하려 했던 노선입니다.")
    with st.expander("📚 실력양성론"):
        st.write("교육과 산업 진흥을 통해 민족의 실력을 먼저 키워야 한다고 주장한 노선입니다.")
    with st.expander("👺 친일파 (반민족행위자)"):
        st.write("일제 강점기에 일제에 협력하여 우리 민족에게 해를 끼친 인물들입니다.")
        
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        st.divider()
        
        # 1. 데이터 수집
        with st.status("한국민족문화대백과사전 검색 중...", expanded=True) as status:
            history_data = scrape_aks_data(target_name)
            
            if history_data:
                status.update(label="✅ 자료 데이터 확보 완료!", state="complete", expanded=False)
            else:
                status.update(label="⚠️ 자료 검색 실패 (AI 지식으로 대체)", state="complete", expanded=False)
        
        # 2. AI 분석
        with st.spinner(f"🇰🇷 '{target_name}'의 독립운동 노선을 분석하고 있습니다..."):
            result_text, mode = analyze_independence_activist(target_name, history_data)
        
        # 3. 결과 출력
        st.subheader(f"📊 분석 결과: {target_name}")
        
        # 분류에 따른 색상 강조 (친일파는 빨간색 경고)
        if "친일파" in result_text:
            st.error("🚨 이 인물은 '친일파' 또는 '반민족행위' 관련 내용이 포함되어 있습니다.")
        elif "사료" in mode:
            st.success(mode)
        else:
            st.warning(mode)
            
        st.markdown(result_text)
        
        # 4. 원본 텍스트 확인
        if history_data:
            with st.expander("🔎 한국민족문화대백과 검색 결과 보기"):
                st.text(history_data[:1000] + "...") # 너무 길면 생략

    elif analyze_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
    else:
        st.info("👈 왼쪽에서 인물 이름을 입력하고 '분석 시작'을 눌러주세요.")
