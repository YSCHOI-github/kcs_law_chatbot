"""TF-IDF 코사인 유사도 검색 엔진

통계 기반 TF-IDF 벡터 간 코사인 유사도를 계산하여 관련 법령 조문을 검색합니다.
"""
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from .config import SEARCH_CONFIG


def search_relevant_chunks(query: str, expanded_keywords: str,
                          vectorizer, title_vectorizer,
                          tfidf_matrix, title_matrix, text_chunks,
                          top_k: int = 3, threshold: float = 0.01,
                          search_weights: dict = None) -> str:
    """TF-IDF 유사도 기반 검색 (함수형 인터페이스)

    제목과 전체 내용을 모두 고려한 검색 함수 (사용자 정의 가중치 적용)

    Args:
        query: 원본 쿼리
        expanded_keywords: AI 확장 키워드
        vectorizer: 내용용 TfidfVectorizer
        title_vectorizer: 제목용 TfidfVectorizer
        tfidf_matrix: 내용 TF-IDF 행렬
        title_matrix: 제목 TF-IDF 행렬
        text_chunks: 원본 텍스트 청크 리스트
        top_k: 반환할 상위 결과 수
        threshold: 최소 유사도 임계값
        search_weights: {'content': 1.0, 'title': 0.0} 형태의 가중치

    Returns:
        검색된 청크들 (개행 구분 문자열)
    """
    # 기본 가중치 설정 (안전한 처리)
    try:
        if search_weights is None or not isinstance(search_weights, dict):
            content_weight = 0.5
            title_weight = 0.5
        else:
            content_weight = search_weights.get('content', 0.5)
            title_weight = search_weights.get('title', 0.5)
    except Exception as e:
        print(f"가중치 설정 오류: {e}")
        content_weight = 0.5
        title_weight = 0.5

    try:
        # 1. 원본 쿼리와 미리 확장된 키워드로 검색
        search_queries = [query, expanded_keywords]

        # 2. 전체 내용 기반 유사도 계산
        all_content_similarities = []
        all_title_similarities = []

        for search_query in search_queries:
            # 전체 내용 유사도
            try:
                content_vec = vectorizer.transform([search_query])
                content_sims = cosine_similarity(content_vec, tfidf_matrix).flatten()
            except:
                content_sims = np.zeros(tfidf_matrix.shape[0])

            # 제목 유사도 (title_vectorizer가 search_query를 처리할 수 있는지 확인)
            try:
                title_vec = title_vectorizer.transform([search_query])
                title_sims = cosine_similarity(title_vec, title_matrix).flatten()
            except:
                # 제목 벡터라이저가 처리할 수 없는 경우 0으로 설정
                title_sims = np.zeros(len(content_sims))

            # 확장 키워드(법령 제목 기반)에 더 높은 가중치 (제목 가중치가 0이 아닌 경우에만)
            if title_weight > 0.0:
                weight = 1.0 if search_query == query else 2.0
            else:
                # 제목 가중치가 0이면 확장 키워드도 일반 키워드와 동일하게 처리
                weight = 1.0

            weighted_content_sims = content_sims * weight
            weighted_title_sims = title_sims * weight

            all_content_similarities.append(weighted_content_sims)
            all_title_similarities.append(weighted_title_sims)

        # 3. 전체 내용과 제목 유사도를 각각 최고 점수로 결합
        if all_content_similarities:
            combined_content_sims = np.maximum.reduce(all_content_similarities)
            combined_title_sims = np.maximum.reduce(all_title_similarities)
        else:
            try:
                combined_content_sims = cosine_similarity(vectorizer.transform([query]), tfidf_matrix).flatten()
            except:
                combined_content_sims = np.zeros(tfidf_matrix.shape[0])

            try:
                combined_title_sims = cosine_similarity(title_vectorizer.transform([query]), title_matrix).flatten()
            except:
                combined_title_sims = np.zeros(len(combined_content_sims) if 'combined_content_sims' in locals() else title_matrix.shape[0])

        # 4. 전체 내용 유사도와 제목 유사도의 가중평균 (사용자 설정 가중치 적용)
        # 제목 가중치가 0이면 제목 검색을 완전히 비활성화
        if title_weight == 0.0:
            combined_sims = combined_content_sims  # 내용만 사용
        else:
            combined_sims = (combined_content_sims * content_weight +
                            combined_title_sims * title_weight)

        # 5. 상위 결과 선택
        indices = combined_sims.argsort()[-top_k:][::-1]

        selected_chunks = []
        for i in indices:
            if combined_sims[i] > threshold:
                selected_chunks.append(text_chunks[i])

        # 임계값 이상인 청크가 없으면 상위 결과 반환
        if not selected_chunks:
            selected_chunks = [text_chunks[i] for i in indices[:top_k]]

        return "\n\n".join(selected_chunks)

    except Exception as e:
        raise Exception(f"검색 중 오류 발생: {str(e)}")
