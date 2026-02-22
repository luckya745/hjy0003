import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------
# 1. 페이지 설정
# ---------------------------------------------------------
st.set_page_config(
    page_title="고려 말 세력 분류기",
    page_icon="⚔️",
    layout="wide"
)

# ---------------------------------------------------------
# 2. API 키 및 모델 설정
# ---------------------------------------------------------
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    # 속도가 빠르고 효율적인 flash 모델 사용
    model = genai.GenerativeModel('gemini-2.5-flash')
except Exception:
    st.error("⚠️ API 키가 설정되지 않았습니다. .streamlit/secrets.toml 파일을 확인해주세요.")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 및 기능 함수
# ---------------------------------------------------------

@st.cache_data(ttl=3600)
def scrape_goryeo_data(name):
    """국사편찬위원회 사료 스크래핑 (기존 캐싱 유지)"""
    base_url = "https://db.history.go.kr/search/searchResult.do"
    headers = {'User-Agent': 'Mozilla/5.0'}
    params = {'searchKeyword': name, 'limit': '15'}
    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        results = [item.get_text(strip=True) for item in soup.select('.search_list li .cont')[:3]]
        return " ".join(results) if results else None
    except: return None

# ⭐ API 호출 최적화: 캐싱 데코레이터 추가
@st.cache_data(ttl=3600, show_spinner=False)
def analyze_goryeo_figure(name, context_text):
    """
    Gemini API 분석 결과 캐싱.
    동일한 이름과 사료 데이터가 들어오면 API를 호출하지 않고 저장된 값을 반환합니다.
    """
    prompt = f"""
    인물 '{name}'을 분석하여 '권문세족', '신진사대부', '신흥무인세력' 중 하나로 분류하세요.
    [사료]: {context_text if context_text else "지식 기반 분석"}
    [형식]: 첫 줄에 '최종 분류: [분류명]' 작성 후 아래에 상세 분석 작성.
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"최종 분류: 오류\n{e}"

# ---------------------------------------------------------
# 4. UI 구성 (초기 화면 정보 배치)
# ---------------------------------------------------------
st.title("⚔️ 고려 말 지배층: 권문세족 vs 신진사대부 vs 신흥무인세력")
st.markdown("---")

# --- 초기 화면: 파별 핵심 정보 안내 (표 형식) ---
st.subheader("📌 고려 말 주요 세력 비교")
st.markdown("""
| 구분 | 권문세족 (친원파) | 신진사대부 (개혁파) | 신흥무인세력 (군사파) |
| :--- | :--- | :--- | :--- |
| **등장 배경** | 원 간섭기 권력 세습 | 과거를 통한 정계 진출 | 홍건적·왜구 격퇴 |
| **경제 기반** | 대농장 소유 (겸병) | 중소 지주층 | 군사적 실권 |
| **사상/외교** | 불교 옹호 / 친원 | 성리학 수용 / 친명 | 실질적 무력 / 개혁 동참 |
| **주요 인물** | 이인임, 염제신 등 | 정몽주, 정도전 등 | 최영, 이성계 등 |
""")
st.markdown("---")

# ---------------------------------------------------------
# 5. 메인 기능부 (UI 로직)
# ---------------------------------------------------------
col1, col2 = st.columns([1, 2])

with col1:
    st.markdown("### 🔍 분석 및 예측")
    target_name = st.text_input("인물 이름을 입력하세요", placeholder="예: 이성계, 정몽주, 이인임")
    
    user_prediction = st.radio(
        "본인이 생각하는 이 인물의 소속은?",
        ["권문세족", "신진사대부", "신흥무인세력"],
        horizontal=False
    )
    
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)
    
    with st.expander("📝 세력별 상세 특징"):
        st.info("**권문세족**: 음서로 관직을 독점하고 대농장을 소유한 보수적 기득권층입니다.")
        st.success("**신진사대부**: 성리학을 바탕으로 과거를 통해 등장한 지방 향리 출신 지식인층입니다.")
        st.warning("**신흥무인세력**: 외세의 침략을 막아내며 성장한 무장 세력으로 신진사대부와 결탁했습니다.")

with col2:
    if analyze_btn and target_name:
        st.divider()
        
        # 1. 사료 검색 (캐싱됨)
        with st.status("역사 데이터베이스 검색 중...", expanded=False) as status:
            history_data = scrape_goryeo_data(target_name)
            status.update(label="✅ 데이터 확보 완료", state="complete")
        
        # 2. AI 분석 실행 (캐싱됨)
        with st.spinner(f"🤖 '{target_name}' 분석 중... (새로운 인물은 API를 호출합니다)"):
            full_result = analyze_goryeo_figure(target_name, history_data)
        
        # 결과 판정 로직
        lines = full_result.strip().split('\n')
        conclusion = lines[0]
        detailed_analysis = "\n".join(lines[1:])
        
        actual_faction = "기타/미분류"
        for f in ["권문세족", "신진사대부", "신흥무인세력"]:
            if f in conclusion:
                actual_faction = f
                break
        
        # 피드백 출력
        st.subheader(f"📊 {target_name} 분석 결과")
        if actual_faction == user_prediction:
            st.success(f"🎯 **정답입니다!** '{target_name}'님은 **{actual_faction}** 세력입니다.")
        else:
            st.error(f"🧐 **틀렸습니다.** 예측은 '{user_prediction}'이었어나, 분석 결과는 **{actual_faction}**입니다.")
        
        with st.container(border=True):
            st.markdown(detailed_analysis)
            
    else:
        st.info("👈 왼쪽에서 인물 이름을 입력하고 예측 버튼을 눌러보세요!")
