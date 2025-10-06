"""TF-IDF 벡터화 및 검색 모듈

법령 데이터를 TF-IDF 벡터로 변환하고 코사인 유사도 기반 검색을 제공합니다.
"""

from .config import LEGAL_STOPWORDS, TFIDF_CONFIG, SEARCH_CONFIG
from .vectorizer import (
    create_tfidf_vectors_from_json,
    create_tfidf_vectors_from_text,
    # 하위 호환성
    create_embeddings_for_json_data,
    create_embeddings_for_text_optimized,
    create_embeddings_for_text
)
from .search import search_relevant_chunks

__all__ = [
    'LEGAL_STOPWORDS',
    'TFIDF_CONFIG',
    'SEARCH_CONFIG',
    'create_tfidf_vectors_from_json',
    'create_tfidf_vectors_from_text',
    'search_relevant_chunks',
    # 하위 호환성
    'create_embeddings_for_json_data',
    'create_embeddings_for_text_optimized',
    'create_embeddings_for_text',
]
