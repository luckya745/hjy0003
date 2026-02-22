import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import re

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="개화파 vs 위정척사파 분류기",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ 근대 개혁의 갈림길: 개화파 vs 위정척사파")
st.markdown("---")
st.info("💡 동일한 인물에 대한 재분석 시 API 호출 없이 캐싱된 결과를 불러와 호출 횟수를 절약합니다.")

# ---------------------------------------------------------
# 2. API 키 설정
# ---------------------------------------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # 모델명은 사용자의 환경에 맞춰 유지합니다.
    model = genai.GenerativeModel('gemini-2.5-flash-lite') 
except Exception as e:
    st.error("⚠️ API 키 설정 오류: .streamlit/secrets.toml 파일에 GEMINI_API_KEY가 있는지 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# 3. 기능 함수 정의
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_history_data(name):
    """국사편찬위원회 데이터베이스 검색 (기존 캐싱 유지)"""
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

# ⭐ API 호출 최적화: 캐싱 데코레이터 추가
@st.cache_data(ttl=3600, show_spinner=False)
def analyze_figure(name, context_text):
    """
    Gemini AI 분석 결과를 캐싱합니다.
    이름(name)과 사료(context_text)가 동일하면 API를 호출하지 않고 저장된 결과를 즉시 반환합니다.
    """
    prompt = f"""
    당신은 한국사 전문가입니다. 인물 '{name}'을(를) 분석하여 **'개화파'**인지 **'위정척사파'**인지 판별하세요.
    
    [사료 정보]: {context_text if context_text else "제공된 사료 없음. 지식을 바탕으로 분석하시오."}

    [출력 규칙 - 반드시 지킬 것]
    1. 첫 번째 줄에 반드시 '결론: 개화파' 또는 '결론: 위정척사파'라고만 적으세요.
    2. 두 번째 줄부터 핵심 이유와 상세 분석을 마크다운 형식으로 작성하세요.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"결론: 오류\n분석 중 오류 발생: {e}"

# ---------------------------------------------------------
# 4. 화면 구성 (UI) - 초기 정보 섹션 (기존 유지)
# ---------------------------------------------------------
st.subheader("📌 주요 세력 비교 안내")
st.markdown("""
| 구분 | 개화파 (Enlightenment Faction) | 위정척사파 (Rejection of Heterodoxy) |
| :--- | :--- | :--- |
| **핵심 가치** | 근대적 개혁, 서구 문물 수용 | 성리학적 질서 수호, 전통 유지 |
| **대외 정책** | 통상 수교 거부 반대, 개항 찬성 | 척화 주전론, 개항 반대 |
| **사상적 배경** | 북학파 실학, 동도서기/변법개화 | 성리학, 존왕양미(尊王攘夷) |
| **주요 인물** | 김옥균, 박영효, 김홍집 등 | 최익현, 이항로, 기정진 등 |
""")

info_col1, info_col2 = st.columns(2)
with info_col1:
    st.info("**💡 개화파란?**\n서양의 기술과 제도를 수용해 근대 국가를 꿈꾼 세력입니다.")
with info_col2:
    st.warning("**🛡️ 위정척사파란?**\n전통 질서를 지키고 서양 문물을 배척한 보수 유림 세력입니다.")

st.markdown("---")

# ---------------------------------------------------------
# 5. 분석 기능 UI 및 결과 처리 로직
# ---------------------------------------------------------
st.subheader("🔍 인물 분석 및 예측")
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    target_name = st.text_input("인물 이름을 입력하세요", placeholder="예: 김옥균, 최익현")

with col2:
    user_prediction = st.radio(
        "본인이 생각하는 이 인물의 소속은?",
        ["개화파", "위정척사파"],
        horizontal=True
    )

with col3:
    st.write("")
    st.write("")
    run_btn = st.button("분석 실행", type="primary", use_container_width=True)

if run_btn and target_name:
    st.divider()
    
    # 1. 사료 데이터 수집 (캐싱 적용됨)
    history_context = scrape_history_data(target_name)
    
    # 2. AI 분석 실행 (캐싱 적용됨)
    # 이미 분석한 인물이라면 로딩 바가 나타나지 않고 즉시 결과가 출력됩니다.
    with st.spinner(f"🤖 '{target_name}' 분석 중... (새로운 인물은 API를 호출합니다)"):
        full_result = analyze_figure(target_name, history_context)
    
    # 결과 처리 로직 (첫 줄에서 결론 추출)
    lines = full_result.strip().split('\n')
    conclusion_line = lines[0]
    detailed_analysis = "\n".join(lines[1:])

    actual_faction = ""
    if "개화파" in conclusion_line:
        actual_faction = "개화파"
    elif "위정척사파" in conclusion_line:
        actual_faction = "위정척사파"

    st.subheader(f"📊 분석 결과: {target_name}")

    if actual_faction == user_prediction:
        st.success(f"🎯 **정답입니다!** '{target_name}'님은 **{actual_faction}** 성향입니다.")
    else:
        st.error(f"🧐 **틀렸습니다.** 실제 결과는 **{actual_faction}**입니다.")

    with st.container(border=True):
        st.markdown(detailed_analysis)
    
    if history_context:
        with st.expander("📜 참고 사료 보기"):
            st.text(history_context)
