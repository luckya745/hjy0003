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
st.info("💡 인물 이름을 입력하고, 어느 독립운동 노선이나 행적에 속할지 먼저 예측해 보세요!")

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
        # 안정적인 gemini-2.5-flash-lite 모델 사용 권장
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
    encoded_name = urllib.parse.quote(name)
    url = f"https://encykorea.aks.ac.kr/Article/Search/{encoded_name}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200: return None
        soup = BeautifulSoup(response.text, 'html.parser')
        content_area = soup.find('div', {'class': 'search_list'}) or soup.body
        text_content = content_area.get_text(strip=True)
        return text_content[:4000] if len(text_content) > 50 else None
    except: return None

# ---------------------------------------------------------
# 4. AI 분석 함수 (정확한 비교를 위해 출력 형식 강화)
# ---------------------------------------------------------
def analyze_independence_activist(name, context_text):
    if context_text:
        base_prompt = f"다음 [자료]를 바탕으로 인물 '{name}'을 분석하세요.\n[자료]: {context_text}"
    else:
        base_prompt = f"역사적 지식을 바탕으로 일제강점기 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}

    [분류 기준]
    다음 중 하나로 분류하세요: 무장투쟁론, 외교독립론, 실력양성론, 의열투쟁, 친일파, 기타

    [지시사항]
    1. 이 인물을 위 분류 기준 중 하나로 명확히 분류하세요.
    2. **[반드시 지킬 출력 형식]**:
       - 첫 번째 줄: 반드시 "최종 분류: [분류명]" 형식으로만 작성하세요. (예: 최종 분류: 무장투쟁론)
       - 두 번째 줄 이하: 핵심 근거와 상세 활동 내역을 마크다운 형식으로 설명하세요.
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
    st.markdown("### 🔍 인물 입력 및 예측")
    target_name = st.text_input("인물 이름", placeholder="예: 김구, 안창호, 이완용")
    
    # [수정] 사용자의 사전 예측 입력 추가
    user_prediction = st.selectbox(
        "본인이 생각하는 이 인물의 주된 노선은?",
        ["무장투쟁론", "외교독립론", "실력양성론", "의열투쟁", "친일파", "기타"],
        help="분석 실행 전 본인의 지식을 바탕으로 예측해 보세요."
    )
    
    st.markdown("---")
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)
    
    st.markdown("### ℹ️ 노선 설명")
    with st.expander("🔫 무장투쟁 / 의열투쟁"):
        st.write("무력이나 직접 행동을 통해 독립을 쟁취하려 했던 노선입니다.")
    with st.expander("🌍 외교독립론"):
        st.write("국제 사회의 외교적 지원을 통해 독립을 달성하려 했던 노선입니다.")
    with st.expander("📚 실력양성론"):
        st.write("교육과 산업 진흥으로 민족의 실력을 키우고자 했던 노선입니다.")
    with st.expander("👺 친일파"):
        st.write("일제에 협력하여 민족에게 해를 끼친 반민족행위자입니다.")

with col2:
    if analyze_btn and target_name:
        st.divider()
        
        # 1. 사료 데이터 수집
        with st.status("한국민족문화대백과사전 검색 중...", expanded=False) as status:
            history_data = scrape_aks_data(target_name)
            status.update(label="✅ 자료 데이터 확인 완료" if history_data else "⚠️ 자료 검색 실패 (AI 지식 활용)", state="complete")
        
        # 2. AI 분석 실행
        with st.spinner(f"🇰🇷 '{target_name}'의 활동 노선을 분석 중입니다..."):
            full_result = analyze_independence_activist(target_name, history_data)
        
        # 3. 정답 대조 로직 (첫 줄에서 결론 추출)
        lines = full_result.strip().split('\n')
        conclusion_line = lines[0] # 예: "최종 분류: 무장투쟁론"
        detailed_analysis = "\n".join(lines[1:])
        
        # AI가 내린 실제 정답 추출
        actual_faction = "기타"
        for faction in ["무장투쟁론", "외교독립론", "실력양성론", "의열투쟁", "친일파"]:
            if faction in conclusion_line:
                actual_faction = faction
                break
            
        # 4. 결과 출력 및 피드백
        st.subheader(f"📊 분석 결과: {target_name}")
        
        if actual_faction == user_prediction:
            st.success(f"🎯 **정답입니다!** '{target_name}'님은 사용자의 예측대로 **{actual_faction}** 노선의 인물입니다.")
        else:
            st.error(f"🧐 **틀렸습니다.** 사용자는 '{user_prediction}'로 예측했으나, 분석 결과 **{actual_faction}** 노선으로 확인됩니다.")

        # 상세 내용 표시
        with st.container(border=True):
            st.info("📚 자료 기반 분석" if history_data else "🧠 AI 지식 기반 분석")
            st.markdown(detailed_analysis)
        
        if history_data:
            with st.expander("🔎 한국민족문화대백과 검색 원문 보기"):
                st.text(history_data[:1000] + "...")

    elif analyze_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
    else:
        st.info("👈 왼쪽에서 인물 이름을 입력하고 소속 노선을 예측한 뒤 '분석 시작'을 눌러주세요.")
