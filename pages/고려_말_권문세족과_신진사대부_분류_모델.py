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
st.info("💡 국사편찬위원회 사료를 바탕으로 고려 말기 지배층의 성향을 분석합니다.")

# ---------------------------------------------------------
# 2. API 키 설정 (메인 app.py와 연동)
# ---------------------------------------------------------
try:
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
    else:
        # secrets에 없으면 사이드바에서 입력받기 (개발 편의성)
        api_key = st.sidebar.text_input("Gemini API Key", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    else:
        st.warning("⚠️ API 키가 설정되지 않았습니다. 왼쪽 사이드바나 secrets.toml을 확인해주세요.")
        st.stop()
except Exception as e:
    st.error(f"설정 오류: {e}")
    st.stop()

# ---------------------------------------------------------
# 3. 데이터 수집 함수 (국사편찬위원회)
# ---------------------------------------------------------
@st.cache_data(ttl=3600)
def scrape_goryeo_data(name):
    """국사편찬위원회 DB에서 인물 검색"""
    base_url = "https://db.history.go.kr/search/searchResult.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://db.history.go.kr/'
    }
    # 고려시대 관련 카테고리로 좁히면 좋으나, 포괄적 검색 후 AI가 필터링하는 것이 안전함
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

        for item in list_items[:4]: # 상위 4개 추출
            text = item.get_text(strip=True)
            if len(text) > 30: results.append(text)

        return " ".join(results) if results else None
    except:
        return None

# ---------------------------------------------------------
# 4. AI 분석 함수 (프롬프트 엔지니어링)
# ---------------------------------------------------------
def analyze_goryeo_figure(name, context_text):
    """Gemini를 이용한 심층 분석"""
    
    if context_text:
        source_mode = "📚 사료 기반 정밀 분석"
        base_prompt = f"다음 [사료]를 바탕으로 인물 '{name}'을 분석하세요.\n[사료]: {context_text[:2500]}"
    else:
        source_mode = "🧠 AI 지식 기반 분석 (사료 없음)"
        base_prompt = f"역사적 지식을 바탕으로 고려 말 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}

    [역사적 배경]
    고려 말기는 친원 보수 세력인 **권문세족(Gwonmun Sejok)**과 개혁적 성향의 **신진사대부(Sinjin Sadaebu)**가 대립하던 시기입니다.

    [지시사항]
    1. 이 인물이 **'권문세족'**인지 **'신진사대부'**인지, 혹은 **'신흥 무인 세력(제3지대)'**인지 명확히 분류하세요.
    2. 아래 4가지 기준에 맞춰 상세히 설명하세요:
       - **출신 성분**: 음서제(문벌) vs 과거제(향리/지방)
       - **경제 기반**: 대농장(불법 겸병) vs 중소 지주(과전법 찬성)
       - **사상적 기반**: 불교 옹호 vs 성리학 수용
       - **외교 노선**: 친원 정책 vs 친명 정책

    [출력 형식]
    반드시 마크다운(Markdown)을 사용하여 가독성 있게 작성하세요.
    - **최종 분류**: [권문세족 / 신진사대부 / 신흥무인세력 / 기타]
    - **핵심 근거**: [3줄 요약]
    - **상세 분석표**: (출신, 경제, 사상, 외교 항목별 정리)
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
    st.markdown("### 🔍 인물 검색")
    target_name = st.text_input("인물 이름 (예: 이인임, 정몽주, 이성계)", placeholder="이름을 입력하세요")
    
    st.markdown("### ℹ️ 분류 기준")
    with st.expander("권문세족이란?"):
        st.write("""
        - **시기**: 고려 후기 (원 간섭기)
        - **출신**: 친원파, 문벌 귀족
        - **특징**: 음서로 관직 진출, 대농장 소유, 불교 옹호
        """)
    with st.expander("신진사대부란?"):
        st.write("""
        - **시기**: 고려 말 ~ 조선 건국
        - **출신**: 지방 향리 출신
        - **특징**: 과거로 관직 진출, 성리학 수용, 친명 정책, 개혁 추구
        """)
        
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        st.divider()
        
        # 1. 데이터 수집 및 상태 표시
        with st.status("역사 데이터베이스 접근 중...", expanded=True) as status:
            st.write(f"국사편찬위원회에서 '{target_name}' 관련 기록을 찾고 있습니다.")
            history_data = scrape_goryeo_data(target_name)
            
            if history_data:
                status.update(label="✅ 사료 데이터 확보 완료!", state="complete", expanded=False)
            else:
                status.update(label="⚠️ 사료 검색 실패 (AI 지식으로 대체)", state="complete", expanded=False)
        
        # 2. AI 분석
        with st.spinner("📜 역사를 분석하는 중입니다..."):
            result_text, mode = analyze_goryeo_figure(target_name, history_data)
        
        # 3. 결과 출력
        st.subheader(f"📊 분석 결과: {target_name}")
        if "사료" in mode:
            st.success(mode)
        else:
            st.warning(mode)
            
        st.markdown(result_text)
        
        # 4. 원본 사료 확인
        if history_data:
            with st.expander("🔎 분석에 사용된 원본 텍스트 보기"):
                st.text(history_data)

    elif analyze_btn and not target_name:
        st.error("인물 이름을 입력해주세요.")
    else:
        st.info("👈 왼쪽에서 인물 이름을 입력하고 '분석 시작'을 눌러주세요.")
