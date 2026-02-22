import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="권문세족 vs 신진사대부 분류기",
    page_icon="⚔️",
    layout="wide"
)

st.title("⚔️ 고려 말: 권문세족 vs 신진사대부")
st.markdown("---")
st.info("💡 인물 이름을 입력하고, 어느 세력에 속할지 먼저 예측해 보세요!")

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
        # 안정적인 버전인 gemini-2.5-flash 권장
        model = genai.GenerativeModel('gemini-2.5-flash')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다. 왼쪽 사이드바나 secrets.toml을 확인해주세요.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 수집 함수
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_goryeo_data(name):
    base_url = "https://db.history.go.kr/search/searchResult.do"
    headers = {'User-Agent': 'Mozilla/5.0'}
    params = {'searchKeyword': name, 'limit': '15'}
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = [item.get_text(strip=True) for item in soup.select('.search_list li .cont')[:3]]
        return " ".join(results) if results else None
    except:
        return None

# ---------------------------------------------------------
# 4. AI 분석 함수 (프롬프트 강화)
# ---------------------------------------------------------
def analyze_goryeo_figure(name, context_text):
    if context_text:
        base_prompt = f"다음 [사료]를 바탕으로 인물 '{name}'을 분석하세요.\n[사료]: {context_text[:2500]}"
    else:
        base_prompt = f"역사적 지식을 바탕으로 고려 말 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}

    [지시사항]
    1. 이 인물을 **'권문세족'**, **'신진사대부'**, **'신흥무인세력'** 중 하나로 분류하세요.
    2. **[반드시 지킬 출력 형식]**:
       - 첫 번째 줄: 반드시 "최종 분류: [분류명]" 형식으로만 작성하세요. (예: 최종 분류: 권문세족)
       - 두 번째 줄 이하: 구체적인 이유(출신, 경제, 사상, 외교)를 상세히 설명하세요.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"최종 분류: 오류\n분석 중 오류 발생: {e}"

# ---------------------------------------------------------
# 5. UI 구성
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔍 인물 검색 & 예측")
    target_name = st.text_input("인물 이름", placeholder="이름을 입력하세요 (예: 이인임, 정몽주)")
    
    # 사용자의 예측 입력 추가
    user_prediction = st.radio(
        "본인이 생각하는 이 인물의 소속은?",
        ["권문세족", "신진사대부", "신흥무인세력"],
        help="분석 시작 전 본인의 예측을 선택해 주세요."
    )
    
    st.markdown("---")
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        # 1. 사료 검색
        with st.status("역사 데이터베이스 접근 중...", expanded=False) as status:
            history_data = scrape_goryeo_data(target_name)
            status.update(label="✅ 데이터 확보 완료", state="complete")
        
        # 2. AI 분석 실행
        with st.spinner("📜 사료와 역사를 대조하여 분석 중입니다..."):
            full_result = analyze_goryeo_figure(target_name, history_data)
        
        # 3. 논리적 비교 및 피드백 처리
        lines = full_result.strip().split('\n')
        conclusion_line = lines[0]  # AI의 첫 줄 (예: "최종 분류: 신진사대부")
        detailed_content = "\n".join(lines[1:]) # 나머지 내용
        
        # AI가 내린 실제 정답 추출
        actual_faction = "미분류"
        for faction in ["권문세족", "신진사대부", "신흥무인세력"]:
            if faction in conclusion_line:
                actual_faction = faction
                break
        
        # 결과 대조 및 피드백 출력
        st.subheader(f"📊 분석 결과: {target_name}")
        
        if actual_faction == user_prediction:
            st.success(f"🎯 **맞았습니다!** '{target_name}'님은 사용자의 예측대로 **{actual_faction}** 세력입니다.")
        else:
            st.error(f"🧐 **틀렸습니다.** 사용자는 '{user_prediction}'로 예측했으나, 분석 결과 **{actual_faction}** 세력으로 확인됩니다.")

        # 상세 분석 내용 표시
        with st.container(border=True):
            st.markdown(detailed_content)
        
        if history_data:
            with st.expander("🔎 참고 사료 원문 보기"):
                st.text(history_data)

    elif analyze_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
    else:
        st.info("👈 왼쪽에서 인물 이름을 입력하고 소속을 예측한 뒤 '분석 시작'을 눌러주세요.")
