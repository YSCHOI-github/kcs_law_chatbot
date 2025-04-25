import streamlit as st                     # 웹 인터페이스 제작을 위한 Streamlit
import google.generativeai as genai        # Google Gemini AI API를 통한 텍스트 생성 기능
from dotenv import load_dotenv             # 환경변수 로드를 위한 모듈
import os                                   # 운영체제 관련 기능 사용
from pdf_utils import extract_text_from_pdf # PDF 문서에서 텍스트 추출 기능
import asyncio                              # 비동기 처리를 위한 asyncio 라이브러리
from concurrent.futures import ThreadPoolExecutor  # 병렬 처리를 위한 ThreadPoolExecutor
import numpy as np                          # 수치 계산용 Numpy 라이브러리
from sklearn.feature_extraction.text import TfidfVectorizer  # 텍스트 데이터를 벡터화하기 위한 TF-IDF 도구
from sklearn.metrics.pairwise import cosine_similarity       # 코사인 유사도를 계산하기 위한 함수

# --- 환경 변수 및 Gemini API 설정 ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Streamlit 페이지 설정
st.set_page_config(
    page_title="법령 통합 챗봇",
    page_icon="📚",
    layout="wide"
)

# --- 세션 상태 초기화 ---
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'law_data' not in st.session_state:
    st.session_state.law_data = {}
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None
if 'last_used_category' not in st.session_state:
    st.session_state.last_used_category = None
# 임베딩 캐싱용 상태
if 'embedding_data' not in st.session_state:
    st.session_state.embedding_data = {}
# 재사용 가능한 asyncio 이벤트 루프
if 'event_loop' not in st.session_state:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    st.session_state.event_loop = loop

# 법령 카테고리 및 PDF 파일 경로
LAW_CATEGORIES = {
    "관세법": {
        "관세법": "laws/관세법.pdf",
        "관세법 시행령": "laws/관세법 시행령.pdf",
        "관세법 시행규칙": "laws/관세법 시행규칙.pdf",
        "관세평가 운영에 관한 고시": "laws/관세평가 운영에 관한 고시.pdf",
        "관세조사 운영에 관한 훈령": "laws/관세조사 운영에 관한 훈령.pdf",
        "Customs_Valuation_Archer": "laws/customs_valuation_archer.pdf",
    },
    "자유무역협정": {
        "원산지조사 운영에 관한 훈령": "laws/원산지조사 운영에 관한 훈령.pdf",
        "자유무역협정 원산지인증수출자 운영에 관한 고시": "laws/자유무역협정 원산지인증수출자 운영에 관한 고시.pdf",
        "특례법 사무처리에 관한 고시": "laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 사무처리에 관한 고시.pdf",
        "특례법 시행규칙": "laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 시행규칙.pdf",
        "특례법 시행령": "laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 시행령.pdf",
        "특례법": "laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률.pdf"
    },
    "외국환거래": {
        "외국환거래법": "laws/외국환거래법.pdf",
        "외국환거래법 시행령": "laws/외국환거래법 시행령.pdf", 
        "외국환거래규정": "laws/외국환거래규정.pdf"
    }
}

# PDF 로드 및 임베딩 생성 함수
@st.cache_data
def load_law_data(category=None):
    law_data = {}
    missing_files = []
    if category:
        pdf_files = LAW_CATEGORIES[category]
    else:
        pdf_files = {}
        for cat in LAW_CATEGORIES.values():
            pdf_files.update(cat)
    for law_name, pdf_path in pdf_files.items():
        if os.path.exists(pdf_path):
            text = extract_text_from_pdf(pdf_path)
            law_data[law_name] = text
            # 임베딩 생성 및 캐싱
            vec, mat, chunks = create_embeddings_for_text(text)
            st.session_state.embedding_data[law_name] = (vec, mat, chunks)
        else:
            missing_files.append(pdf_path)
    if missing_files:
        st.warning(f"다음 파일들을 찾을 수 없습니다: {', '.join(missing_files)}")
    return law_data

# 임베딩 및 청크 생성
def create_embeddings_for_text(text, chunk_size=1000):
    chunks = []
    step = chunk_size // 2
    for i in range(0, len(text), step):
        segment = text[i:i+chunk_size]
        if len(segment) > 100:
            chunks.append(segment)
    vectorizer = TfidfVectorizer()
    matrix = vectorizer.fit_transform(chunks)
    return vectorizer, matrix, chunks

# 쿼리 유사 청크 검색
def search_relevant_chunks(query, vectorizer, tfidf_matrix, text_chunks, top_k=3, threshold=0.005):
    q_vec = vectorizer.transform([query])
    sims = cosine_similarity(q_vec, tfidf_matrix).flatten()
    indices = sims.argsort()[-top_k:][::-1]
    sel = [text_chunks[i] for i in indices if sims[i] > threshold]
    if not sel:
        sel = [text_chunks[i] for i in indices]
    return "\n\n".join(sel)

# Gemini 모델 반환
def get_model():
    return genai.GenerativeModel('gemini-2.0-flash')

# 법령별 에이전트 응답 (async)
async def get_law_agent_response_async(law_name, question, history):
    vec, mat, chunks = st.session_state.embedding_data[law_name]
    context = search_relevant_chunks(question, vec, mat, chunks)
    prompt = f"""
당신은 {law_name} 전문가입니다.

아래는 질문과 관련된 법령 내용입니다. 반드시 다음 법령 내용을 기반으로 질문에 답변해주세요:
{context}

이전 대화:
{history}

질문: {question}
답변할 때 법조항과 출처를 명확히 제시해주세요.
"""
    model = get_model()
    loop = st.session_state.event_loop
    with ThreadPoolExecutor() as pool:
        res = await loop.run_in_executor(pool, lambda: model.generate_content(prompt))
    return law_name, res.text

# 모든 에이전트 병렬 실행
async def gather_agent_responses(question, history):
    tasks = [get_law_agent_response_async(name, question, history)
             for name in st.session_state.law_data]
    return await asyncio.gather(*tasks)

# 헤드 에이전트 통합 답변
def get_head_agent_response(responses, question, history):
    combined = "\n\n".join([f"=== {n} 전문가 답변 ===\n{r}" for n, r in responses])
    prompt = f"""
당신은 법령 통합 전문가입니다.

{combined}

이전 대화:
{history}

질문: {question}

다음 단계에 따라 답변을 생성해주세요:

1. 질문 분석
   - 질문의 핵심 주제 파악
   - 필요한 법령 영역 식별
   - 관련 키워드 추출

2. 법령 검색
   - 관련 법령 조항 찾기
   - 법령 간 연관성 분석
   - 적용 가능한 예외 조항 확인

3. 해석 및 적용
   - 법령의 구체적인 내용 해석
   - 실제 사례에 적용 방안 검토
   - 예외 상황 고려

4. 답변 구성
   - 법령 근거 명시, 반드시 주어진 법령에 기반하여 답변변
   - 단계별 설명 제공
   - 필요한 경우 예시 제시

위 구조에 따라 단계별 추론을 명확히 보여주면서 최종 통합 답변을 작성해주세요.
"""
    return get_model().generate_content(prompt).text

# --- UI: 카테고리 선택 ---
with st.expander("카테고리 선택 (선택사항)", expanded=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("관세법", use_container_width=True):
            st.session_state.selected_category = "관세법"
            st.session_state.law_data = load_law_data("관세법")
            st.session_state.last_used_category = "관세법"
            st.rerun()
    with c2:
        if st.button("자유무역협정", use_container_width=True):
            st.session_state.selected_category = "자유무역협정"
            st.session_state.law_data = load_law_data("자유무역협정")
            st.session_state.last_used_category = "자유무역협정"
            st.rerun()
    with c3:
        if st.button("외국환거래", use_container_width=True):
            st.session_state.selected_category = "외국환거래"
            st.session_state.law_data = load_law_data("외국환거래")
            st.session_state.last_used_category = "외국환거래"
            st.rerun()
    with c4:
        if st.button("자동 분석", use_container_width=True):
            st.session_state.selected_category = None
            st.session_state.law_data = load_law_data()
            st.session_state.last_used_category = "all"
            st.rerun()

if st.session_state.selected_category:
    st.info(f"선택된 카테고리: {st.session_state.selected_category}")
else:
    st.info("카테고리 선택 없이 자동 분석 중...")

# 대화 기록 렌더링
for msg in st.session_state.chat_history:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

# 사용자 입력 및 응답
if user_input := st.chat_input("질문을 입력하세요"):
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("assistant"):
        history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history])
        responses = st.session_state.event_loop.run_until_complete(
            gather_agent_responses(user_input, history)
        )
        answer = get_head_agent_response(responses, user_input, history)
        st.markdown(answer)
        st.session_state.chat_history.append({"role": "assistant", "content": answer})

# 사이드바 안내
with st.sidebar:
    st.markdown("""
### ℹ️ 사용 안내

다음 법령들을 기반으로 답변을 제공합니다:

**관세법 관련:**
- 관세법
- 관세법 시행령
- 관세법 시행규칙
- 관세평가 운영에 관한 고시
- 관세조사 운영에 관한 훈령
- Customs_Valuation_Archer

**자유무역협정 관련:**
- 원산지조사 운영에 관한 훈령
- 자유무역협정 원산지인증수출자 운영에 관한 고시
- 자유무역협정의 이행을 위한 관세법의 특례에 관한 법률
- 자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 시행령
- 자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 시행규칙
- 자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 사무처리에 관한 고시

**외국환거래 관련:**
- 외국환거래법
- 외국환거래법 시행령
- 외국환거래규정
""")
    if st.button("새 채팅 시작", type="primary"):
        st.session_state.chat_history = []
        st.rerun()