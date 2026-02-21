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
st.info("💡 1636년 병자호란 당시, 청나라와의 관계를 두고 대립했던 인물들의 정치적 입장을 분석합니다.")

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
# 3. 데이터 수집 함수 (국사편찬위원회)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_byeongja_data(name):
    """국사편찬위원회 DB에서 인물 검색"""
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
        
        # 검색 결과 추출
        list_items = soup.select('.search_list li .cont')
        if not list_items:
            list_items = soup.select('.result_list li')

        for item in list_items[:4]: 
            text = item.get_text(strip=True)
            if len(text) > 30: results.append(text)

        return " ".join(results) if results else None
    except:
        return None

# ---------------------------------------------------------
# 4. AI 분석 함수
# ---------------------------------------------------------
def analyze_stance(name, context_text):
    """Gemini를 이용한 정치적 입장 분석"""
    
    if context_text:
        source_mode = "📚 사료 기반 정밀 분석"
        base_prompt = f"다음 [사료]를 바탕으로 인물 '{name}'을 분석하세요.\n[사료]: {context_text[:2500]}"
    else:
        source_mode = "🧠 AI 지식 기반 분석 (사료 없음)"
        base_prompt = f"역사적 지식을 바탕으로 병자호란 시기 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}

    [역사적 배경: 병자호란(1636)]
    당시 조선 조정은 청나라(후금)의 요구에 대한 대응을 두고 두 파로 갈라졌습니다.
    1. **주전론 (척화파)**: "오랑캐에게 무릎 꿇을 수 없다." 대의명분과 절의 중시, 결사항전 주장. (예: 김상헌, 삼학사)
    2. **주화론 (주화파)**: "나라를 보존하는 것이 우선이다." 실리와 생존 중시, 화친 주장. (예: 최명길)

    [지시사항]
    1. 이 인물이 **'주전론(척화파)'**인지 **'주화론'**인지 명확히 분류하세요.
    2. 아래 기준에 맞춰 상세히 설명하세요:
       - **핵심 주장**: 전쟁(항전) vs 화친(강화)
       - **명분과 실리**: 명나라와의 의리 중시 vs 국가의 보존 중시
       - **주요 행적**: 남한산성에서의 언행이나 전후의 결과

    [출력 형식]
    마크다운(Markdown)을 사용하여 작성하세요.
    - **최종 분류**: [주전론(척화파) / 주화론 / 기타]
    - **한 줄 요약**: [핵심 주장 요약]
    - **상세 분석**: (주장, 논리, 결말 항목별 정리)
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
    target_name = st.text_input("인물 이름 (예: 김상헌, 최명길, 홍익한)", placeholder="이름을 입력하세요")
    
    st.markdown("### ℹ️ 용어 설명")
    with st.expander("🔥 주전론 (척화파)"):
        st.write("""
        - **입장**: 청나라와의 화친을 거부하고 끝까지 싸우자.
        - **가치**: 대의명분, 존명배금(명나라를 높이고 금나라를 배척)
        - **대표 인물**: 김상헌, 홍익한, 윤집, 오달제(삼학사)
        """)
    with st.expander("🕊️ 주화론 (주화파)"):
        st.write("""
        - **입장**: 전쟁을 멈추고 청나라와 화친하여 나라를 보존하자.
        - **가치**: 현실적 실리, 종묘사직의 보전
        - **대표 인물**: 최명길
        """)
        
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        st.divider()
        
        # 1. 데이터 수집
        with st.status("역사 데이터베이스 검색 중...", expanded=True) as status:
            st.write(f"'{target_name}'의 병자호란 당시 기록을 찾고 있습니다.")
            history_data = scrape_byeongja_data(target_name)
            
            if history_data:
                status.update(label="✅ 사료 데이터 확보 완료!", state="complete", expanded=False)
            else:
                status.update(label="⚠️ 사료 검색 실패 (AI 지식으로 대체)", state="complete", expanded=False)
        
        # 2. AI 분석
        with st.spinner("⚔️ 정치적 입장을 분석하고 있습니다..."):
            result_text, mode = analyze_stance(target_name, history_data)
        
        # 3. 결과 출력
        st.subheader(f"📊 분석 결과: {target_name}")
        
        if "사료" in mode:
            st.success(mode)
        else:
            st.warning(mode)
            
        st.markdown(result_text)
        
        # 4. 원본 사료 확인
        if history_data:
            with st.expander("🔎 분석에 사용된 원본 사료 보기"):
                st.text(history_data)

    elif analyze_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
    else:
        st.info("👈 왼쪽에서 인물 이름을 입력하고 '분석 시작'을 눌러주세요.")
