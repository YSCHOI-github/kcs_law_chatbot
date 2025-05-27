import streamlit as st                     # 웹 인터페이스 제작을 위한 Streamlit
import os                                   # 운영체제 관련 기능 사용
import google.generativeai as genai        # Google Gemini AI API를 통한 텍스트 생성 기능
from pdf_utils import extract_text_from_pdf # PDF 문서에서 텍스트 추출 기능
import asyncio                              # 비동기 처리를 위한 asyncio 라이브러리
from concurrent.futures import ThreadPoolExecutor  # 병렬 처리를 위한 ThreadPoolExecutor
from sklearn.feature_extraction.text import TfidfVectorizer  # 텍스트 데이터를 벡터화하기 위한 TF-IDF 도구
from sklearn.metrics.pairwise import cosine_similarity       # 코사인 유사도를 계산하기 위한 함수

# --- Streamlit 페이지 설정 ---
st.set_page_config(
    page_title="법령 통합 챗봇",
    page_icon="📚",
    layout="wide"
)

# --- 유저로부터 Gemini API Key 입력 받기 ---
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = ""

with st.sidebar.expander("🔑 API Key 설정", expanded=True):
    key_input = st.text_input(
        label="Google Gemini API Key 입력",
        type="password",
        placeholder="여기에 API Key를 입력하세요",
        value=st.session_state.gemini_api_key,
    )
    if key_input:
        st.session_state.gemini_api_key = key_input

if not st.session_state.gemini_api_key:
    st.sidebar.warning("챗봇을 이용하려면 API Key를 입력해주세요.")
    st.stop()

# --- Gemini API 설정 ---
genai.configure(api_key=st.session_state.gemini_api_key)

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

LAW_CATEGORIES = {
    "관세조사": {  # Updated category name
        "관세법": "laws/관세법.pdf",
        "관세법 시행령": "laws/관세법 시행령.pdf",
        "관세법 시행규칙": "laws/관세법 시행규칙.pdf",
        "관세평가 운영에 관한 고시": "laws/관세평가 운영에 관한 고시.pdf",
        "관세조사 운영에 관한 훈령": "laws/관세조사 운영에 관한 훈령.pdf",
    },
    "관세평가": {  # Updated category name
        "WTO관세평가협정": "laws/WTO관세평가협정_영문판.pdf",
        "TCCV기술문서_영문판": "laws/TCCV기술문서_영문판.pdf",
        "관세와무역에관한일반협정제7조_영문판": "laws/관세와무역에관한일반협정제7조_영문판.pdf",
        "권고의견_영문판": "laws/권고의견_영문판.pdf",
        "사례연구_영문판": "laws/사례연구_영문판.pdf",
        "연구_영문판": "laws/연구_영문판.pdf",
        "해설_영문판": "laws/해설_영문판.pdf",
        "Customs_Valuation_Archer_part1": "laws/customs_valuation_archer_part1.pdf",
        "Customs_Valuation_Archer_part2": "laws/customs_valuation_archer_part2.pdf",
        "Customs_Valuation_Archer_part3": "laws/customs_valuation_archer_part3.pdf",
        "Customs_Valuation_Archer_part4": "laws/customs_valuation_archer_part4.pdf",
        "Customs_Valuation_Archer_part5": "laws/customs_valuation_archer_part5.pdf",
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
    },
    "대외무역거래": {
        "대외무역법": "laws/대외무역법.pdf",
        "대외무역법 시행령": "laws/대외무역법 시행령.pdf", 
        "대외무역관리규정": "laws/대외무역관리규정.pdf",
        "원산지표시제도 운영에 관한 고시": "laws/원산지표시제도 운영에 관한 고시.pdf",
    },
    "환급": {
        "환급특례법": "laws/수출용 원재료에 대한 관세 등 환급에 관한 특례법.pdf",
        "환급특례법 시행령": "laws/수출용 원재료에 대한 관세 등 환급에 관한 특례법 시행령.pdf", 
        "환급특례법 시행규칙": "laws/수출용 원재료에 대한 관세 등 환급에 관한 특례법 시행규칙.pdf",
        "수입물품에 대한 개별소비세와 주세 등의 환급에 관한 고시": "laws/수입물품에 대한 개별소비세와 주세 등의 환급에 관한 고시.pdf",
        "대체수출물품 관세환급에 따른 수출입통관절차 및 환급처리에 관한 예규":"laws/대체수출물품 관세환급에 따른 수출입통관절차 및 환급처리에 관한 예규.pdf",
        "수입원재료에 대한 환급방법 조정에 관한 고시": "laws/수입원재료에 대한 환급방법 조정에 관한 고시.pdf",
        "수출용 원재료에 대한 관세 등 환급사무에 관한 훈령": "laws/수출용 원재료에 대한 관세 등 환급사무에 관한 훈령.pdf",
        "수출용 원재료에 대한 관세 등 환급사무처리에 관한 고시": "laws/수출용 원재료에 대한 관세 등 환급사무처리에 관한 고시.pdf",
        "위탁가공 수출물품에 대한 관세 등 환급처리에 관한 예규": "laws/위탁가공 수출물품에 대한 관세 등 환급처리에 관한 예규.pdf",
    }
}

# 카테고리별 키워드 정보 (AI 분류에 도움을 주기 위한 참고 정보)
CATEGORY_KEYWORDS = {
    "관세조사": ["관세 조사", "세액심사", "관세법", "관세 평가", "관세조사", "세관장", "세액", "조사", "통관", "사후심사", "관세부과", "서면심사"],
    "관세평가": ["관세 평가", "WTO", "TCCV", "관세평가협정", "과세가격", "거래가격", "조정가격", "거래가치", "덤핑", "평가", "수입물품가격", "관세가액"],
    "자유무역협정": ["FTA", "원산지", "원산지증명서", "원산지인증", "특례법", "협정관세", "원산지결정기준", "원산지검증", "원산지조사", "인증수출자"],
    "외국환거래": ["외국환", "외국환거래", "외환", "외환거래", "송금", "환전", "외국환은행", "국외지급", "국외송금", "외국환신고", "외화"],
    "대외무역거래": ["대외무역", "무역거래", "무역법", "수출입", "원산지표시", "수출입신고", "수출신고", "수입신고", "통관", "무역관리"],
    "환급": ["환급", "관세환급", "환급금", "관세 등 환급", "환급특례법", "수출용 원재료", "관세 환급", "소요량", "정산", "과다환급", "불복"]
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
@st.cache_data
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
def get_model_head():
    return genai.GenerativeModel('gemini-2.5-flash-preview-05-20')

# 질문 카테고리 분류 함수 추가
def classify_question_category(question):
    prompt = f"""
당신은 법령 전문가로서 사용자의 질문을 분석하여 가장 관련성 높은 법령 카테고리를 선택하는 업무를 담당합니다.

다음은 사용자의 질문입니다:
"{question}"

아래 법령 카테고리 중에서 이 질문과 가장 관련성이 높은 카테고리 하나만 선택해주세요:

1. 관세조사: 관세법, 관세법 시행령, 관세법 시행규칙, 관세평가 운영에 관한 고시, 관세조사 운영에 관한 훈령 등 관련
2. 관세평가: WTO관세평가협정, 관세와무역에관한일반협정제7조, 권고의견, 사례연구 등 관련
3. 자유무역협정: FTA, 원산지증명서, 원산지인증, 원산지조사, 특례법 등 관련
4. 외국환거래: 외국환거래법, 외국환거래법 시행령, 외국환거래규정 등 관련
5. 대외무역거래: 대외무역법, 대외무역법 시행령, 대외무역관리규정, 원산지표시제도 등 관련
6. 환급: 환급특례법, 환급특례법 시행령, 환급특례법 시행규칙, 관세 등 환급 관련

반드시 위의 카테고리 중 하나만 선택하고, 다음 형식으로만 답변해주세요:
"카테고리: [선택한 카테고리명]"

예를 들어, "카테고리: 관세조사"와 같이 답변해주세요.
"""
    model = get_model()
    response = model.generate_content(prompt)
    # 응답에서 카테고리 추출
    response_text = response.text
    if "카테고리:" in response_text:
        category = response_text.split("카테고리:")[1].strip()
        # 카테고리명만 정확히 추출
        for cat in LAW_CATEGORIES.keys():
            if cat in category:
                return cat
    # 분류가 명확하지 않은 경우 기본 카테고리 반환
    return "관세조사"  # 기본 카테고리로 설정

# 법령별 에이전트 응답 (async)
async def get_law_agent_response_async(law_name, question, history):
    # 임베딩 데이터가 없으면 생성
    if law_name not in st.session_state.embedding_data:
        text = st.session_state.law_data.get(law_name, "")
        vec, mat, chunks = create_embeddings_for_text(text)
        st.session_state.embedding_data[law_name] = (vec, mat, chunks)
    else:
        vec, mat, chunks = st.session_state.embedding_data[law_name]
    context = search_relevant_chunks(question, vec, mat, chunks)
    prompt = f"""
당신은 대한민국 {law_name} 법률 전문가입니다.

아래는 질문과 관련된 법령 내용입니다. 반드시 다음 법령 내용을 기반으로 질문에 답변해주세요:
{context}

이전 대화:
{history}

질문: {question}

# 응답 지침
1. 제공된 법령 정보에 기반하여 정확하게 답변해주세요.
2. 답변에 사용한 모든 법령 출처(법령명, 조항)를 명확히 인용해주세요.
3. 법령에 명시되지 않은 내용은 추측하지 말고, 알 수 없다고 정직하게 답변해주세요.
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
당신은 관세, 외국환거래, 대외무역법 분야 전문성을 갖춘 법학 교수이자 여러 자료를 통합하여 종합적인 답변을 제공하는 전문가입니다.

{combined}

이전 대화:
{history}

질문: {question}

# 응답 지침
1 여러 에이전트로부터 받은 답변을 분석하고 통합하여 사용자의 질문에 가장 적합한 최종 답변을 제공합니다.
2. 제공된 법령 정보에 기반하여 정확하게 답변해주세요.
3. 답변에 사용한 모든 법령 출처(법령명, 조항)를 명확히 인용해주세요.
4. 법령에 명시되지 않은 내용은 추측하지 말고, 알 수 없다고 정직하게 답변해주세요.
5. 모든 답변은 두괄식으로 작성합니다.
"""
    return get_model_head().generate_content(prompt).text

# --- UI: 카테고리 선택 ---
# --- UI: 카테고리 선택 ---
with st.expander("카테고리 선택 (선택사항)", expanded=True):
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    with c1:
        if st.button("관세조사", use_container_width=True):  # Updated button label
            st.session_state.selected_category = "관세조사"  # Updated category name
            st.session_state.law_data = load_law_data("관세조사")  # Updated category name
            st.session_state.last_used_category = "관세조사"  # Updated category name
            st.rerun()
    with c2:
        if st.button("관세평가", use_container_width=True):
            st.session_state.selected_category = "관세평가"
            st.session_state.law_data = load_law_data("관세평가")
            st.session_state.last_used_category = "관세평가"
            st.rerun()
    with c3:
        if st.button("자유무역협정", use_container_width=True):
            st.session_state.selected_category = "자유무역협정"
            st.session_state.law_data = load_law_data("자유무역협정")
            st.session_state.last_used_category = "자유무역협정"
            st.rerun()
    with c4:
        if st.button("외국환거래", use_container_width=True):
            st.session_state.selected_category = "외국환거래"
            st.session_state.law_data = load_law_data("외국환거래")
            st.session_state.last_used_category = "외국환거래"
            st.rerun()
    with c5:
        if st.button("대외무역거래", use_container_width=True):
            st.session_state.selected_category = "대외무역거래"
            st.session_state.law_data = load_law_data("대외무역거래")
            st.session_state.last_used_category = "대외무역거래"
            st.rerun()
    with c6:
        if st.button("환급", use_container_width=True):
            st.session_state.selected_category = "환급"
            st.session_state.law_data = load_law_data("환급")
            st.session_state.last_used_category = "환급"
            st.rerun()
    with c7:
        if st.button("AI 자동 분류", use_container_width=True):  # 버튼 이름 변경
            st.session_state.selected_category = "auto_classify"  # 특별 마커로 변경
            st.session_state.last_used_category = "auto_classify"
            st.rerun()

if st.session_state.selected_category:
    if st.session_state.selected_category == "auto_classify":
        st.info("AI가 질문을 분석하여 자동으로 관련 카테고리를 선택합니다.")
    else:
        st.info(f"선택된 카테고리: {st.session_state.selected_category}")
else:
    st.info("카테고리를 선택하거나 AI 자동 분류를 이용해주세요.")

# 대화 기록 렌더링
for msg in st.session_state.chat_history:
    with st.chat_message(msg['role']):
        st.markdown(msg['content'])

# 사용자 입력 및 응답
if user_input := st.chat_input("질문을 입력하세요"):
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            # 자동 분류 모드인 경우 또는 선택된 카테고리가 없는 경우
            if st.session_state.selected_category == "auto_classify" or not st.session_state.selected_category:
                # AI로 카테고리 분류
                category = classify_question_category(user_input)
                st.session_state.law_data = load_law_data(category)
                st.write(f"🔍 AI 분석 결과: '{category}' 카테고리와 관련된 질문으로 판단되어 해당 법령을 참조합니다.")
            
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

**관세조사 관련:**
- 관세법, 시행령, 시행규칙
- 관세평가 운영에 관한 고시
- 관세조사 운영에 관한 훈령
                
**관세평가 관련:**
- 관세와무역에관한일반협정제7조, 
- WTO관세평가협정, TCCV기술문서, 권고의견, 사례연구, 연구, 해설
- WCO Customs Valuation Archer

**자유무역협정 관련:**
- 원산지조사 운영에 관한 훈령
- 자유무역협정 원산지인증수출자 운영에 관한 고시
- 자유무역협정의 이행을 위한 관세법의 특례에 관한 법률, 시행령, 시행규칙, 사무처리에 관한 고시

**외국환거래 관련:**
- 외국환거래법, 시행령, 규정
                
**대외무역거래 관련:**
- 대외무역법, 시행령, 관리규정
- 원산지표시제도 운영에 관한 고시
                
**환급 관련:**
- 수출용 원재료에 대한 관세 등 환급에 관한 특례법, 시행령, 시행규칙
- 수입물품에 대한 개별소비세와 주세 등의 환급에 관한 고시
- 대체수출물품 관세환급에 따른 수출입통관절차 및 환급처리에 관한 예규
- 수입원재료에 대한 환급방법 조정에 관한 고시
- 수출용 원재료에 대한 관세 등 환급사무에 관한 훈령
- 수출용 원재료에 대한 관세 등 환급사무처리에 관한 고시
- 위탁가공 수출물품에 대한 관세 등 환급처리에 관한 예규
""")
    if st.button("새 채팅 시작", type="primary"):
        st.session_state.chat_history = []
        st.rerun()