import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="온건파 vs 급진파 사대부 분류기",
    page_icon="📜",
    layout="wide"
)

st.title("📜 고려 말: 온건파 vs 급진파 사대부")
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
        # 안정적인 gemini-2.5-flash-lite 모델 사용 권장
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 수집 함수
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_history_db(name):
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
# 4. AI 분석 함수 (비교 로직을 위한 프롬프트 강화)
# ---------------------------------------------------------
def analyze_sadaebu(name, context_text):
    if context_text:
        base_prompt = f"다음 [사료]를 바탕으로 인물 '{name}'을 분석하세요.\n[사료]: {context_text[:2500]}"
    else:
        base_prompt = f"역사적 지식을 바탕으로 고려 말 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}

    [지시사항]
    1. 이 인물이 **'온건파 사대부'**인지 **'급진파 사대부'**인지 명확히 분류하세요.
    2. **[반드시 지킬 출력 형식]**:
       - 첫 번째 줄: 반드시 "최종 분류: [분류명]" 형식으로만 작성하세요. (예: 최종 분류: 온건파 사대부)
       - 두 번째 줄 이하: 왕조에 대한 태도, 토지 개혁, 행적 등을 마크다운 형식으로 상세히 설명하세요.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"최종 분류: 오류\n분석 중 오류 발생: {e}"

# ---------------------------------------------------------
# 5. UI 구성
# ---------------------------------------------------------
# 초기 화면에 파벌 비교 표 추가
st.subheader("📌 사대부 세력 비교")
st.markdown("""
| 구분 | 온건파 사대부 | 급진파 사대부 |
| :--- | :--- | :--- |
| **개혁 방향** | 고려 왕조 유지, 점진적 개혁 | 역성혁명(새 왕조 개창), 급격한 개혁 |
| **토지 제도** | 과전법 시행에 신중 | 사전 혁파, 과전법 강행 |
| **사상/종교** | 불교 폐단 비판 (종교적 절충) | 불교 전면 부정 (배불숭유) |
| **대표 인물** | 정몽주, 이색, 길재 | 정도전, 조준, 권근 |
""")
st.markdown("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔍 인물 입력 및 예측")
    target_name = st.text_input("인물 이름", placeholder="예: 정몽주, 정도전")
    
    # 사용자의 예측 선택 추가
    user_prediction = st.radio(
        "본인이 생각하는 이 인물의 소속은?",
        ["온건파 사대부", "급진파 사대부"],
        help="분석 실행 전 본인의 지식을 테스트해보세요!"
    )
    
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        # 1. 데이터 수집
        with st.status("역사 데이터베이스 검색 중...", expanded=False) as status:
            history_data = scrape_history_db(target_name)
            status.update(label="✅ 데이터 검색 완료", state="complete")
        
        # 2. AI 분석
        with st.spinner(f"🤖 '{target_name}'의 성향을 분석 중입니다..."):
            full_result = analyze_sadaebu(target_name, history_data)
        
        # 3. 결과 대조 로직 (첫 줄에서 결론 추출)
        lines = full_result.strip().split('\n')
        conclusion_line = lines[0] # 예: "최종 분류: 온건파 사대부"
        detailed_analysis = "\n".join(lines[1:])
        
        # 실제 AI가 판단한 파벌 명칭 추출
        actual_faction = "기타"
        if "온건파" in conclusion_line:
            actual_faction = "온건파 사대부"
        elif "급진파" in conclusion_line:
            actual_faction = "급진파 사대부"
            
        # 4. 피드백 출력
        st.subheader(f"📊 분석 결과: {target_name}")
        
        if actual_faction == user_prediction:
            st.success(f"🎯 **정답입니다!** '{target_name}'님은 예측하신 대로 **{actual_faction}**입니다.")
        else:
            st.error(f"🧐 **틀렸습니다.** 예측은 '{user_prediction}'이었으나, 분석 결과는 **{actual_faction}**입니다.")

        # 상세 내용 표시
        with st.container(border=True):
            st.caption("AI 분석 상세 근거")
            st.markdown(detailed_analysis)
        
        if history_data:
            with st.expander("🔎 참고 사료 원문 보기"):
                st.text(history_data)

    elif analyze_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
    else:
        st.info("👈 왼쪽에서 인물 이름을 입력하고 소속을 예측한 뒤 '분석 시작'을 눌러주세요.")
