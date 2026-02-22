import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="개화파 vs 위정척사파 분류기",
    page_icon="⚖️",
    layout="wide"
)

st.title("⚖️ 개화파 vs 위정척사파 분류기")
st.markdown("---")
st.info("💡 인물 이름을 입력하고, 어느 세력에 속할지 먼저 예측해 보세요!")

# ---------------------------------------------------------
# 2. API 키 설정
# ---------------------------------------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # 모델명은 현재 사용 가능한 안정적인 모델로 설정하는 것이 좋습니다 (예: gemini-2.5-flash-lite)
    model = genai.GenerativeModel('gemini-2.5-flash-lite') 
except Exception as e:
    st.error("⚠️ API 키 설정 오류: .streamlit/secrets.toml 파일에 GEMINI_API_KEY가 있는지 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# 3. 기능 함수 정의
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_history_data(name):
    """국사편찬위원회 데이터베이스 검색"""
    base_url = "https://db.history.go.kr/search/searchResult.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://db.history.go.kr/'
    }
    params = {'searchKeyword': name, 'limit': '20'}

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=5)
        if response.status_code != 200: return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        
        list_items = soup.select('.search_list li .cont')
        if not list_items:
            list_items = soup.select('.result_list li')

        for item in list_items[:3]:
            text = item.get_text(strip=True)
            if len(text) > 30: results.append(text)

        return " ".join(results) if results else None
    except:
        return None

def analyze_figure(name, context_text):
    """Gemini AI 분석"""
    if context_text:
        prompt = f"""
        당신은 한국 근대사 역사학자입니다. 
        아래 [사료]를 바탕으로 인물 '{name}'의 성향을 분석하세요.

        [사료]: {context_text[:2500]}
        
        [지시사항]
        1. 이 인물이 **'개화파(급진/온건)'**인지 **'위정척사파'**인지 명확히 분류하세요.
        2. 판단 근거를 사료 내용을 인용하여 설명하세요.
        """
        source_type = "📚 사료 기반 분석 완료"
    else:
        prompt = f"""
        당신은 한국사 전문가입니다. 인물 '{name}'에 대해 알고 있는 지식을 바탕으로 분석하세요.
        
        [지시사항]
        1. 이 인물이 **'개화파'**인지 **'위정척사파'**인지 분류하세요.
        2. 해당 파벌로 분류되는 결정적인 역사적 사건이나 주장을 설명하세요.
        """
        source_type = "🧠 AI 지식 기반 분석 (사료 검색 실패)"

    prompt += "\n출력 형식: 반드시 첫 줄에 '결론: [개화파/위정척사파]' 형식으로 답하고, 이후 마크다운으로 핵심 이유, 상세 분석을 작성해주세요."

    try:
        response = model.generate_content(prompt)
        return response.text, source_type
    except Exception as e:
        return f"분석 중 오류 발생: {e}", "Error"

# ---------------------------------------------------------
# 4. 화면 구성 (UI)
# ---------------------------------------------------------
# 레이아웃 수정: 이름 입력, 예측 선택, 실행 버튼
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    target_name = st.text_input("인물 이름을 입력하세요", placeholder="예: 김옥균, 최익현, 민영익")

with col2:
    # 사용자의 예측 입력 부분 추가
    user_prediction = st.radio(
        "본인이 생각하는 이 인물의 소속은?",
        ["개화파", "위정척사파"],
        horizontal=True,
        help="분석 실행 전 본인의 지식을 테스트해보세요!"
    )

with col3:
    st.write("") # 간격 맞춤용
    st.write("")
    run_btn = st.button("분석 실행", type="primary", use_container_width=True)

if run_btn and target_name:
    st.divider()
    
    # 1. 검색 단계
    with st.status("🕵️ 역사 데이터베이스 검색 중...") as status:
        history_context = scrape_history_data(target_name)
        if history_context:
            status.update(label="✅ 사료 데이터 확보 성공!", state="complete")
        else:
            status.update(label="⚠️ 사료 검색 실패 (AI 지식으로 전환)", state="complete")
            
    # 2. 분석 단계
    with st.spinner(f"🤖 Gemini가 '{target_name}'의 성향을 분석하고 있습니다..."):
        result, mode = analyze_figure(target_name, history_context)

    # 3. 결과 출력 및 비교
    st.subheader(f"📊 분석 결과: {target_name}")
    
    # 비교 로직: AI 결과 텍스트 안에 사용자가 선택한 단어가 있는지 확인
    is_correct = user_prediction in result
    
    # 결과 비교 알림창
    if is_correct:
        st.success(f"🎯 **맞았습니다!** '{target_name}'님은 사용자의 예측대로 **{user_prediction}** 성향의 인물입니다.")
    else:
        st.error(f"🧐 **예측과 다릅니다.** 사용자는 '{user_prediction}'로 예측하셨으나, 분석 결과는 다르게 나타났습니다.")

    # 상세 분석 결과 박스
    with st.container(border=True):
        if "사료" in mode:
            st.caption(f"✅ {mode}")
        else:
            st.caption(f"⚠️ {mode}")
        st.markdown(result)
    
    # 사료 원문 보기
    if history_context:
        with st.expander("📜 참고한 사료 원문 보기"):
            st.text(history_context)
