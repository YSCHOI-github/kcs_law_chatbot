"""Utils 공개 API

하위 호환성을 유지하면서 기능별로 분리된 모듈을 제공합니다.
"""

# TF-IDF 모듈
from .tfidf import (
    LEGAL_STOPWORDS,
    TFIDF_CONFIG,
    SEARCH_CONFIG,
    create_tfidf_vectors_from_json,
    create_tfidf_vectors_from_text,
    search_relevant_chunks,
    # 하위 호환성
    create_embeddings_for_json_data,
    create_embeddings_for_text_optimized,
    create_embeddings_for_text
)

# AI 모듈
from .ai import (
    QueryExpander,
    QueryPreprocessor,  # 하위 호환성
    get_agent_response,
    get_head_agent_response,
    get_head_agent_response_stream,
    get_model,
    get_model_head
)

# 전처리 모듈
from .preprocessing import extract_title_terms_from_laws

# 통합 분석 함수
from typing import Tuple, List


def analyze_query(question: str, collected_laws: dict = None,
                 search_weights: dict = None) -> Tuple[str, List[str], str]:
    """사용자 쿼리 분석 및 키워드 생성 (통합 함수)

    제목 가중치 설정에 따라 다른 전략을 사용합니다.

    Args:
        question: 사용자 질문
        collected_laws: 수집된 법령 딕셔너리
        search_weights: {'content': 1.0, 'title': 0.0} 형태의 가중치

    Returns:
        (original_query, similar_queries, expanded_keywords) 튜플
    """
    # 법령 제목 용어 추출
    title_terms = []
    if collected_laws:
        title_terms = extract_title_terms_from_laws(collected_laws)

    expander = QueryExpander(title_terms)

    # 1. 유사 쿼리 3개 생성 (API 호출 1회)
    similar_questions = expander.generate_similar_questions(question, search_weights)

    # 2. 원본 + 유사 쿼리를 합쳐 키워드 및 유사어 생성 (API 호출 1회)
    combined_query_text = " ".join([question] + similar_questions)
    expanded_keywords = expander.extract_keywords_and_synonyms(combined_query_text, search_weights)

    return question, similar_questions, expanded_keywords


# 병렬 처리 래퍼 함수
def process_json_data(file_name: str, json_data: list):
    """JSON 데이터 처리 함수 (병렬 처리용 래퍼)

    Args:
        file_name: 파일명
        json_data: JSON 데이터

    Returns:
        (file_name, vec, title_vec, mat, title_mat, chunks, chunk_count)
    """
    try:
        vec, title_vec, mat, title_mat, chunks = create_tfidf_vectors_from_json(json_data, file_name)
        return file_name, vec, title_vec, mat, title_mat, chunks, len(chunks) if chunks else 0
    except Exception as e:
        return file_name, None, None, None, None, None, 0


def process_single_file(file_data):
    """단일 파일 처리 함수 (병렬 처리용 래퍼)

    Args:
        file_data: (file_name, file_content) 튜플

    Returns:
        (file_name, vec, title_vec, mat, title_mat, chunks, chunk_count)
    """
    file_name, file_content = file_data
    try:
        vec, title_vec, mat, title_mat, chunks = create_tfidf_vectors_from_text(file_content, file_name)
        return file_name, vec, title_vec, mat, title_mat, chunks, len(chunks) if chunks else 0
    except Exception as e:
        return file_name, None, None, None, None, None, 0


__all__ = [
    # TF-IDF
    'LEGAL_STOPWORDS',
    'TFIDF_CONFIG',
    'SEARCH_CONFIG',
    'create_tfidf_vectors_from_json',
    'create_tfidf_vectors_from_text',
    'search_relevant_chunks',

    # AI
    'QueryExpander',
    'get_agent_response',
    'get_head_agent_response',
    'get_head_agent_response_stream',
    'get_model',
    'get_model_head',

    # 전처리
    'extract_title_terms_from_laws',

    # 통합
    'analyze_query',
    'process_json_data',
    'process_single_file',

    # 하위 호환성
    'QueryPreprocessor',
    'create_embeddings_for_json_data',
    'create_embeddings_for_text_optimized',
    'create_embeddings_for_text',
]
