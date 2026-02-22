import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="병자호란: 주전론 vs 주화론",
    page_icon="⚔️",
    layout="wide"
)

st.title("⚔️ 병자호란: 주전론 vs 주화론 분류기")
st.markdown("---")
st.info("💡 동일한 인물에 대한 재분석 시 API 호출 없이 캐싱된 결과를 불러옵니다.")

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
@st.cache_data(ttl=3600)
def scrape_byeongja_data(name):
    """국사편찬위원회 DB에서 인물 검색"""
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

# ---------------------------------------------------------
# 4. AI 분석 함수 (Gemini API 캐싱 추가)
# ---------------------------------------------------------
# 인물 이름(name)과 사료 내용(context_text)이 동일하면 API를 호출하지 않고 저장된 결과를 반환합니다.
@st.cache_data(show_spinner=False, ttl=3600)
def analyze_stance(name, context_text):
    """Gemini를 이용한 정치적 입장 분석 결과를 캐싱함"""
    if context_text:
        base_prompt = f"다음 [사료]를 바탕으로 인물 '{name}'을 분석하세요.\n[사료]: {context_text[:2500]}"
    else:
        base_prompt = f"역사적 지식을 바탕으로 병자호란 시기 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}
    [지시사항]
    1. 이 인물이 **'주전론(척화파)'**인지 **'주화론'**인지 명확히 분류하세요.
    2. **[반드시 지킬 출력 형식]**:
       - 첫 번째 줄: 반드시 "결론: [주전론(척화파) 또는 주화론]" 형식으로만 작성하세요.
       - 두 번째 줄 이하: 핵심 주장, 명분과 실리, 주요 행적을 마크다운 형식으로 상세히 설명하세요.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"결론: 오류\n분석 중 오류 발생: {e}"

# ---------------------------------------------------------
# 5. UI 구성
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔍 인물 입력 및 예측")
    target_name = st.text_input("인물 이름", placeholder="예: 김상헌, 최명길")
    
    user_prediction = st.radio(
        "본인이 생각하는 이 인물의 소속은?",
        ["주전론(척화파)", "주화론"],
        help="분석 실행 전 본인의 예측을 선택해 주세요."
    )
    
    st.markdown("---")
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)
    
    with st.expander("ℹ️ 용어 설명 보기"):
        st.write("**주전론**: 청과 끝까지 싸우자 (대의명분 중시)")
        st.write("**주화론**: 화친하여 나라를 보전하자 (현실실리 중시)")

with col2:
    if analyze_btn and target_name:
        # 1. 사료 데이터 수집 (캐싱 적용됨)
        history_data = scrape_byeongja_data(target_name)
        
        # 2. AI 분석 실행 (캐싱 적용됨)
        # 새로운 인물일 때만 로딩 바가 나타나며, 이미 검색한 인물은 즉시 결과가 뜹니다.
        with st.spinner(f"🤖 '{target_name}' 분석 중..."):
            full_result = analyze_stance(target_name, history_data)
        
        # 3. 정답 대조 로직
        lines = full_result.strip().split('\n')
        conclusion_line = lines[0]
        detailed_analysis = "\n".join(lines[1:])
        
        actual_faction = ""
        if "주전론" in conclusion_line or "척화파" in conclusion_line:
            actual_faction = "주전론(척화파)"
        elif "주화론" in conclusion_line:
            actual_faction = "주화론"
            
        # 4. 결과 출력 및 피드백
        st.subheader(f"📊 분석 결과: {target_name}")
        
        if actual_faction == user_prediction:
            st.success(f"🎯 **맞았습니다!** '{target_name}'님은 **{actual_faction}** 성향의 인물입니다.")
        else:
            st.error(f"🧐 **틀렸습니다.** 분석 결과는 **{actual_faction}**입니다.")

        with st.container(border=True):
            st.markdown(detailed_analysis)
            
        if history_data:
            with st.expander("🔎 참고 사료 보기"):
                st.text(history_data)

    elif analyze_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
