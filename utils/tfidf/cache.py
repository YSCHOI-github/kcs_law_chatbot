"""TF-IDF 벡터화 결과 캐싱 시스템

벡터화는 시간이 오래 걸리므로, 결과를 디스크에 캐싱합니다.
파일 내용이 변경되면 자동으로 재생성됩니다.
"""
import pickle
import hashlib
from pathlib import Path


def get_file_hash(file_content: str) -> str:
    """파일 내용의 MD5 해시 생성

    Args:
        file_content: 파일 내용 (문자열)

    Returns:
        MD5 해시 문자열
    """
    return hashlib.md5(file_content.encode()).hexdigest()


def save_tfidf_cache(file_name: str, file_hash: str, vectorizers: tuple, matrices: tuple, chunks: list):
    """TF-IDF 벡터화 결과를 캐시에 저장

    Args:
        file_name: 캐시 키로 사용할 파일명
        file_hash: 파일 내용 해시
        vectorizers: (content_vectorizer, title_vectorizer) 튜플
        matrices: (content_matrix, title_matrix) 튜플
        chunks: 원본 텍스트 청크 리스트
    """
    cache_dir = Path("cache")
    cache_dir.mkdir(exist_ok=True)

    cache_file = cache_dir / f"{file_name}_{file_hash}.pkl"

    # 5-tuple 형식으로 저장 (content_vec, title_vec, content_mat, title_mat, chunks)
    cache_data = (
        vectorizers[0],  # content_vectorizer
        vectorizers[1],  # title_vectorizer
        matrices[0],     # content_matrix
        matrices[1],     # title_matrix
        chunks
    )

    with open(cache_file, 'wb') as f:
        pickle.dump(cache_data, f)


def load_tfidf_cache(file_name: str, file_hash: str):
    """TF-IDF 캐시 로드 (하위 호환성 보장)

    Args:
        file_name: 캐시 키로 사용할 파일명
        file_hash: 파일 내용 해시

    Returns:
        (content_vectorizer, title_vectorizer, content_matrix, title_matrix, chunks)
        캐시가 없거나 버전이 다르면 None
    """
    cache_file = Path("cache") / f"{file_name}_{file_hash}.pkl"

    if not cache_file.exists():
        return None

    try:
        with open(cache_file, 'rb') as f:
            cached_data = pickle.load(f)

        # 버전 체크: 5-tuple만 유효 (이전 3-tuple 캐시 무효화)
        if isinstance(cached_data, tuple) and len(cached_data) == 5:
            return cached_data
        else:
            # 구버전 캐시 무효화
            return None

    except Exception as e:
        # 캐시 로드 실패 시 무효화
        print(f"캐시 로드 실패: {e}")
        return None
