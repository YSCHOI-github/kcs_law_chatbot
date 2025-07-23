import PyPDF2
import google.generativeai as genai
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st
import re
# utils.py 상단에 추가
from pdfminer.high_level import extract_text as pdfminer_extract_text

# 법령 카테고리 및 PDF 파일 경로
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

# 불용어 정의
LEGAL_STOPWORDS = [
    # 기본 불용어
    '제', '것', '등', '때', '경우', '바', '수', '점', '면', '이', '그', '저', '은', '는', '을', '를', '에', '의', '으로', 
    '따라', '또는', '및', '있다', '한다', '되어', '인한', '대한', '관한', '위한', '통한', '같은', '다른',
    
    # 법령 구조 불용어
    '조항', '규정', '법률', '법령', '조문', '항목', '세부', '내용', '사항', '요건', '기준', '방법', '절차',
    
    # 일반적인 동사/형용사
    '해당', '관련', '포함', '제외', '적용', '시행', '준용', '의하다', '하다', '되다', '있다', '없다', '같다'
]

# PDF를 JSON 구조의 조문으로 변환하는 새 함수들

def convert_pdf_to_json_articles(pdf_path: str) -> list[dict]:
    """PDF 파일을 구조화된 조문 리스트(JSON)로 변환하는 메인 함수"""
    try:
        # 1. pdfminer를 사용하여 PDF에서 텍스트 추출
        text = pdfminer_extract_text(pdf_path)
        if not text:
            print(f"경고: {pdf_path}에서 텍스트를 추출하지 못했습니다.")
            return []

        # 2. 텍스트를 조문별로 파싱
        articles = _parse_text_to_articles(text)
        if not articles:
            print(f"경고: {pdf_path}에서 조문을 찾지 못했습니다.")
            return []
            
        # 3. 조문 내용 정제 (불필요한 괄호 및 구조 표시어 제거)
        refined_articles = _refine_articles(articles)
        return refined_articles
        
    except Exception as e:
        print(f"'{pdf_path}' 파일 변환 중 오류 발생: {e}")
        return []

def _parse_text_to_articles(text: str) -> list[dict]:
    """추출된 텍스트를 '조/제목/내용' 구조로 파싱하는 함수"""
    lines = text.splitlines()
    articles = []
    # "제X조(제목)" 패턴을 찾는 정규식
    article_pattern = re.compile(r"^(제\d+(?:-\d+)?조(?:의\d+)?)\s*\((.*?)\)")
    
    current_article = None
    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = article_pattern.match(line)
        if match:
            # 새로운 조문이 시작되면, 이전 조문을 리스트에 추가
            if current_article:
                articles.append(current_article)
            
            # 새 조문 정보 추출
            number = match.group(1)
            title = match.group(2)
            content = line[match.end():].strip()
            
            current_article = {"조번호": number, "제목": title, "내용": content}
        elif current_article:
            # 현재 조문의 내용이 다음 줄로 이어지는 경우
            current_article["내용"] += f"\n{line}"
    
    # 마지막 조문을 리스트에 추가
    if current_article:
        articles.append(current_article)
        
    return articles

def _refine_articles(articles: list[dict]) -> list[dict]:
    """조문 내용에서 불필요한 텍스트(장/절/관, 꺾쇠/대괄호)를 제거하는 함수"""
    # "제X장", "제X절" 등 구조 표시어 제거를 위한 정규식
    structure_pattern = re.compile(r"제\d+(장|절|관)")
    
    for article in articles:
        content = article["내용"]
        # <...> 또는 [...] 형태의 텍스트 제거
        content = re.sub(r"<.*?>|\[.*?\]", "", content)
        # 제X장, 제X절 등 구조 표시어 제거
        content = structure_pattern.sub("", content).strip()
        article["내용"] = content
    return articles

# 사용자 쿼리 전처리 및 유사어 생성 클래스 (새로 추가)
class QueryPreprocessor:
    """사용자 쿼리 전처리 및 유사어 생성 클래스"""
    
    def __init__(self):
        # 첫 번째 파일에서 사용하던 모델을 그대로 활용합니다.
        self.model = get_model() 
        
    def extract_keywords_and_synonyms(self, query: str) -> str:
        """키워드 추출 및 유사어 생성"""
        prompt = f"""
당신은 대한민국 법령 전문가입니다. 다음 질문을 분석하여 검색에 도움이 되는 키워드와 유사어를 생성해주세요.

질문: "{query}"

다음 작업을 수행해주세요:
1. 핵심 키워드 추출
2. 각 키워드의 유사어, 동의어, 관련어 생성
3. 복합어의 경우 단어 분리도 포함
4. 검색에 유용한 모든 관련 단어들을 나열

응답 형식: 키워드와 유사어들을 공백으로 구분하여 한 줄로 나열해주세요.
예시: 관세조사 세액심사 관세법 세관장 세액 통관 사후심사

단어들만 나열하고 다른 설명은 하지 마세요.
"""
        
        try:
            response = self.model.generate_content(prompt)
            keywords_text = response.text.strip()
            keywords = re.findall(r'[가-힣]{2,}', keywords_text)
            return ' '.join(keywords)
            
        except Exception as e:
            print(f"키워드 추출 오류: {e}")
            fallback_keywords = re.findall(r'[가-힣]{2,}', query)
            return ' '.join(fallback_keywords)
    
    def generate_similar_questions(self, original_query: str) -> list[str]:
        """유사한 질문 생성"""
        prompt = f"""
다음 질문과 유사한 의미를 가진 질문들을 3개 생성해주세요. 
법령 검색에 도움이 되도록 다양한 표현과 용어를 사용해주세요.

원본 질문: "{original_query}"

유사 질문 3개를 다음 형식으로 생성해주세요:
1. (첫 번째 유사 질문)
2. (두 번째 유사 질문)
3. (세 번째 유사 질문)

각 질문은 원본과 의미는 같지만 다른 표현이나 용어를 사용해주세요.
"""
        
        try:
            response = self.model.generate_content(prompt)
            questions = []
            lines = response.text.strip().split('\n')
            for line in lines:
                match = re.search(r'^\d+\.\s*(.+)', line.strip())
                if match:
                    questions.append(match.group(1))
            
            return questions[:3]
            
        except Exception as e:
            print(f"유사 질문 생성 오류: {e}")
            return [original_query]


def extract_text_from_pdf(pdf_path):
    """
    PDF 파일에서 텍스트를 추출하는 함수
    """
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
    except Exception as e:
        print(f"Error processing {pdf_path}: {str(e)}")
    return text

# 임베딩 및 청크 생성
@st.cache_data
def create_embeddings_for_text(text, chunk_size=1000):
    chunks = []
    step = chunk_size // 2
    for i in range(0, len(text), step):
        segment = text[i:i+chunk_size]
        if len(segment) > 100:
            chunks.append(segment)
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words=LEGAL_STOPWORDS,
        min_df=1,
        max_df=0.8,
        sublinear_tf=True,
        use_idf=True,
        smooth_idf=True,
        norm='l2'
    )
    matrix = vectorizer.fit_transform(chunks)
    return vectorizer, matrix, chunks

# JSON 구조의 조문을 위한 임베딩 생성 함수 (새로 추가)
@st.cache_data
def create_embeddings_for_json(articles):
    """JSON 형식의 조문 리스트로부터 TF-IDF 임베딩을 생성합니다."""
    if not articles:
        return None, None, []
    
    # 각 조문을 "조번호 (제목): 내용" 형식의 문자열로 변환하여 청크로 사용
    chunks = [f"{article['조번호']} ({article['제목']}): {article['내용']}" for article in articles if article['내용']]
    
    if not chunks:
        return None, None, []

    # TfidfVectorizer를 사용하여 벡터화 (기존과 동일)
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        stop_words=LEGAL_STOPWORDS,
        min_df=1,
        max_df=0.8,
        sublinear_tf=True,
        use_idf=True,
        smooth_idf=True,
        norm='l2'
    )
    matrix = vectorizer.fit_transform(chunks)
    return vectorizer, matrix, chunks

# 쿼리 유사 청크 검색 (수정)
def search_relevant_chunks(query, expanded_keywords, vectorizer, tfidf_matrix, text_chunks, top_k=3, threshold=0.01):
    """원본 쿼리와 확장된 키워드를 모두 사용하여 관련 청크 검색"""
    
    # 원본 쿼리와 확장 키워드로 각각 검색 벡터 생성
    search_queries = [query, expanded_keywords]
    all_similarities = []

    for search_query in search_queries:
        q_vec = vectorizer.transform([search_query])
        sims = cosine_similarity(q_vec, tfidf_matrix).flatten()
        
        # 원본 쿼리에 가중치 부여
        weight = 1.0 if search_query == query else 0.8
        weighted_sims = sims * weight
        
        all_similarities.append(weighted_sims)
    
    # 각 청크에 대해 가장 높은 유사도 점수를 선택
    if all_similarities:
        combined_sims = np.maximum.reduce(all_similarities)
    else:
        # 비상시 원본 쿼리로만 검색
        combined_sims = cosine_similarity(vectorizer.transform([query]), tfidf_matrix).flatten()
    
    # 상위 결과 선택
    indices = combined_sims.argsort()[-top_k:][::-1]
    
    selected_chunks = [text_chunks[i] for i in indices if combined_sims[i] > threshold]
    
    # 임계값을 넘는 결과가 없으면 상위 K개 반환
    if not selected_chunks:
        selected_chunks = [text_chunks[i] for i in indices[:top_k]]
    
    return "\n\n".join(selected_chunks)

# PDF 로드 및 임베딩 생성 함수 (수정)
@st.cache_data
def load_law_data(category=None):
    law_data = {}
    missing_files = []
    
    # 로드할 파일 목록 결정
    if category:
        pdf_files = LAW_CATEGORIES.get(category, {})
    else:
        pdf_files = {}
        for cat_files in LAW_CATEGORIES.values():
            pdf_files.update(cat_files)

    for law_name, pdf_path in pdf_files.items():
        if os.path.exists(pdf_path):
            # 현재 법령의 카테고리 확인
            current_category = category
            if not current_category:
                for cat, laws in LAW_CATEGORIES.items():
                    if law_name in laws:
                        current_category = cat
                        break
            
            # --- 카테고리에 따른 분기 처리 ---
            if current_category == "관세평가":
                # '관세평가'는 기존 방식(일반 텍스트 추출) 사용
                text = extract_text_from_pdf(pdf_path)
                law_data[law_name] = text
                vec, mat, chunks = create_embeddings_for_text(text)
                if vec is not None:
                    st.session_state.embedding_data[law_name] = (vec, mat, chunks)
            else:
                # 나머지 카테고리는 새로운 방식(JSON 구조화) 사용
                articles = convert_pdf_to_json_articles(pdf_path)
                if articles:
                    law_data[law_name] = articles  # JSON 데이터를 저장
                    vec, mat, chunks = create_embeddings_for_json(articles)
                    if vec is not None:
                        st.session_state.embedding_data[law_name] = (vec, mat, chunks)
                else:
                    # JSON 변환 실패 시, 기존 방식으로 대체 처리
                    st.warning(f"'{law_name}' 파일의 구조 분석에 실패하여 일반 텍스트로 처리합니다.")
                    text = extract_text_from_pdf(pdf_path)
                    law_data[law_name] = text
                    vec, mat, chunks = create_embeddings_for_text(text)
                    if vec is not None:
                        st.session_state.embedding_data[law_name] = (vec, mat, chunks)
        else:
            missing_files.append(pdf_path)

    if missing_files:
        st.warning(f"다음 파일들을 찾을 수 없습니다: {', '.join(missing_files)}")
    return law_data

# Gemini 모델 반환
def get_model():
    return genai.GenerativeModel('gemini-2.0-flash')

def get_model_head():
    return genai.GenerativeModel('gemini-2.5-flash')

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

# 법령별 에이전트 응답 (async) (수정)
async def get_law_agent_response_async(law_name, question, history, expanded_keywords):
    # 임베딩 데이터가 없으면 생성
    if law_name not in st.session_state.embedding_data:
        law_data = st.session_state.law_data.get(law_name, "")
        
        # 데이터 타입에 따라 적절한 임베딩 함수 호출
        if isinstance(law_data, list):  # JSON 형식 (조문 리스트)
            vec, mat, chunks = create_embeddings_for_json(law_data)
        else:  # 텍스트 형식
            vec, mat, chunks = create_embeddings_for_text(law_data)
            
        st.session_state.embedding_data[law_name] = (vec, mat, chunks)
    else:
        vec, mat, chunks = st.session_state.embedding_data[law_name]

    # 수정된 검색 함수 호출
    context = search_relevant_chunks(question, expanded_keywords, vec, mat, chunks) 

    # 이하 prompt 부분은 기존과 동일합니다.
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

# 모든 에이전트 병렬 실행 (수정)
async def gather_agent_responses(question, history):
    # 1. QueryPreprocessor를 사용하여 질문 분석 및 키워드 생성
    preprocessor = QueryPreprocessor()
    
    similar_questions = preprocessor.generate_similar_questions(question)
    combined_query_text = " ".join([question] + similar_questions)
    expanded_keywords = preprocessor.extract_keywords_and_synonyms(combined_query_text)

    # 디버깅 또는 확인용으로 화면에 출력할 수 있습니다.
    # st.info(f"유사 질문: {similar_questions}")
    # st.info(f"확장 키워드: {expanded_keywords}")

    # 2. 각 에이전트에게 '확장된 키워드'를 전달하여 병렬 실행
    tasks = [get_law_agent_response_async(name, question, history, expanded_keywords) # expanded_keywords 전달
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