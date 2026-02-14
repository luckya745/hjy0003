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
st.info("💡 고려 말기 사회 개혁의 방향을 두고 갈라진 두 사대부 세력을 분석합니다.")

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
        model = genai.GenerativeModel('gemini-2.5-flash')
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
def scrape_history_db(name):
    """국사편찬위원회 DB에서 인물 검색"""
    # [수정] 최신 검색 URL 적용
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
        
        # 검색 결과 추출 로직
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
def analyze_sadaebu(name, context_text):
    """Gemini를 이용한 사대부 성향 분석"""
    
    if context_text:
        source_mode = "📚 사료 기반 정밀 분석"
        base_prompt = f"다음 [사료]를 바탕으로 인물 '{name}'을 분석하세요.\n[사료]: {context_text[:2500]}"
    else:
        source_mode = "🧠 AI 지식 기반 분석 (사료 없음)"
        base_prompt = f"역사적 지식을 바탕으로 고려 말 인물 '{name}'을 분석하세요."

    prompt = f"""
    {base_prompt}

    [역사적 배경]
    고려 말 신진사대부는 개혁의 방향에 따라 두 파벌로 나뉘었습니다.
    1. **온건파 사대부 (Moderate Reformists)**: 고려 왕조의 틀 안에서 점진적 개혁 추구 (예: 정몽주, 이색, 길재)
    2. **급진파 사대부 (Radical Reformists)**: 역성혁명 주장, 새 왕조(조선) 개창 주도 (예: 정도전, 조준, 권근)

    [지시사항]
    1. 이 인물이 **'온건파 사대부'**인지 **'급진파 사대부'**인지 명확히 분류하세요.
    2. 아래 3가지 기준에 맞춰 상세히 설명하세요:
       - **왕조에 대한 태도**: 고려 왕조 유지 vs 역성혁명(조선 건국)
       - **토지 제도 개혁**: 사전 혁파에 대한 입장 (온건 vs 급진)
       - **최후 및 행적**: 조선 건국 참여 여부 혹은 절의를 지켰는지 여부

    [출력 형식]
    마크다운(Markdown)을 사용하여 작성하세요.
    - **최종 분류**: [온건파 사대부 / 급진파 사대부 / 기타]
    - **핵심 이유**: [한 문장 요약]
    - **상세 분석**: (왕조관, 개혁론, 주요 행적 항목별 정리)
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
    target_name = st.text_input("인물 이름 (예: 정몽주, 정도전)", placeholder="이름을 입력하세요")
    
    st.markdown("### ℹ️ 파벌 설명")
    with st.expander("🌿 온건파 사대부란?"):
        st.write("""
        - **입장**: 고려 왕조 유지, 점진적 개혁
        - **대표 인물**: 정몽주, 이색, 길재
        - **결말**: 조선 건국 반대, 낙향하거나 피살됨
        """)
    with st.expander("🔥 급진파 사대부란?"):
        st.write("""
        - **입장**: 역성혁명(왕조 교체), 급진적 개혁
        - **대표 인물**: 정도전, 조준, 권근
        - **결말**: 조선 건국 주도, 개국공신 책봉
        """)
        
    analyze_btn = st.button("분석 시작", type="primary", use_container_width=True)

with col2:
    if analyze_btn and target_name:
        st.divider()
        
        # 1. 데이터 수집
        with st.status("역사 데이터베이스 검색 중...", expanded=True) as status:
            st.write(f"국사편찬위원회에서 '{target_name}' 관련 기록을 찾는 중입니다.")
            history_data = scrape_history_db(target_name)
            
            if history_data:
                status.update(label="✅ 사료 데이터 확보 완료!", state="complete", expanded=False)
            else:
                status.update(label="⚠️ 사료 검색 실패 (AI 지식으로 대체)", state="complete", expanded=False)
        
        # 2. AI 분석
        with st.spinner("📜 사대부의 성향을 분석하고 있습니다..."):
            result_text, mode = analyze_sadaebu(target_name, history_data)
        
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
