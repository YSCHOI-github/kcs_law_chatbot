"""TF-IDF 벡터화 엔진

법령 JSON 데이터를 TF-IDF 벡터로 변환합니다.
임베딩(Embedding)이 아니라 통계 기반 TF-IDF 벡터화를 사용합니다.
"""
from sklearn.feature_extraction.text import TfidfVectorizer
import json
from .config import TFIDF_CONFIG
from .cache import get_file_hash, save_tfidf_cache, load_tfidf_cache


def create_tfidf_vectors_from_json(json_data: list, file_name: str):
    """JSON 법령 데이터를 TF-IDF 벡터로 변환

    Args:
        json_data: 법령 데이터 리스트
                   [{"조번호": "제1조", "제목": "목적", "내용": "..."}]
        file_name: 캐시 키로 사용할 파일명

    Returns:
        (content_vectorizer, title_vectorizer, content_matrix, title_matrix, chunks)
        - content_vectorizer: 내용용 TfidfVectorizer
        - title_vectorizer: 제목용 TfidfVectorizer
        - content_matrix: 내용 TF-IDF 행렬
        - title_matrix: 제목 TF-IDF 행렬
        - chunks: 원본 텍스트 청크 리스트

        실패 시: (None, None, None, None, [])
    """
    try:
        # JSON 데이터를 문자열로 변환하여 해시 생성
        json_str = json.dumps(json_data, ensure_ascii=False, sort_keys=True)
        file_hash = get_file_hash(json_str)

        # 캐시 확인
        cached = load_tfidf_cache(file_name, file_hash)
        if cached:
            return cached

        # 청크 생성
        chunks, titles = _prepare_text_chunks(json_data)
        if not chunks:
            return None, None, None, None, []

        # 내용 TF-IDF 벡터화
        content_vectorizer = TfidfVectorizer(**TFIDF_CONFIG)
        content_matrix = content_vectorizer.fit_transform(chunks)

        # 제목 TF-IDF 벡터화 (빈 제목 필터링)
        non_empty_titles = [title if title else " " for title in titles]
        title_vectorizer = TfidfVectorizer(**TFIDF_CONFIG)
        title_matrix = title_vectorizer.fit_transform(non_empty_titles)

        # 캐시 저장
        result = (content_vectorizer, title_vectorizer, content_matrix, title_matrix, chunks)
        save_tfidf_cache(
            file_name, file_hash,
            (content_vectorizer, title_vectorizer),
            (content_matrix, title_matrix),
            chunks
        )

        return result

    except Exception as e:
        raise Exception(f"TF-IDF 벡터화 중 오류: {str(e)}")


def create_tfidf_vectors_from_text(file_content: str, file_name: str):
    """텍스트 파일 내용을 JSON으로 파싱 후 TF-IDF 벡터 생성

    Args:
        file_content: JSON 문자열
        file_name: 캐시 키로 사용할 파일명

    Returns:
        create_tfidf_vectors_from_json()과 동일
    """
    try:
        # 캐시 확인 (중복 체크 방지)
        file_hash = get_file_hash(file_content)
        cached = load_tfidf_cache(file_name, file_hash)
        if cached:
            return cached

        # JSON 파싱
        data = json.loads(file_content)
        if not isinstance(data, list):
            return None, None, None, None, []

        return create_tfidf_vectors_from_json(data, file_name)

    except Exception as e:
        raise Exception(f"TF-IDF 벡터화 중 오류: {str(e)}")


def _prepare_text_chunks(json_data: list):
    """법령 JSON을 검색 가능한 텍스트 청크로 변환

    Args:
        json_data: 법령 데이터 리스트

    Returns:
        (chunks, titles)
        - chunks: "[조번호] (제목) 내용" 형태의 텍스트 리스트
        - titles: 제목 리스트 (제목이 없으면 빈 문자열)
    """
    chunks = []
    titles = []

    for item in json_data:
        if not isinstance(item, dict):
            continue

        # 청크 구성: [조번호] (제목) 내용
        chunk_parts = []
        title = ""

        if "조번호" in item:
            chunk_parts.append(f"[{item['조번호']}]")

        if "제목" in item:
            chunk_parts.append(f"({item['제목']})")
            title = item['제목']

        if "내용" in item:
            chunk_parts.append(item['내용'])

        if chunk_parts:
            chunks.append(" ".join(chunk_parts))
            titles.append(title)  # 빈 문자열이거나 실제 제목

    return chunks, titles


# 하위 호환성 유지 (기존 함수명)
def create_embeddings_for_json_data(json_data: list, file_name: str):
    """[DEPRECATED] create_tfidf_vectors_from_json 사용 권장

    기존 코드 호환성을 위한 래퍼 함수
    """
    return create_tfidf_vectors_from_json(json_data, file_name)


def create_embeddings_for_text_optimized(file_content: str, file_name: str):
    """[DEPRECATED] create_tfidf_vectors_from_text 사용 권장

    기존 코드 호환성을 위한 래퍼 함수
    """
    return create_tfidf_vectors_from_text(file_content, file_name)


def create_embeddings_for_text(file_content: str):
    """[DEPRECATED] create_tfidf_vectors_from_text 사용 권장

    기존 코드 호환성을 위한 래퍼 함수
    """
    return create_tfidf_vectors_from_text(file_content, "temp")
