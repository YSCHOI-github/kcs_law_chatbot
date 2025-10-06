"""데이터 전처리 유틸리티

법령 데이터 전처리 및 용어 추출 기능을 제공합니다.
"""
import re


def extract_title_terms_from_laws(collected_laws: dict) -> list:
    """수집된 법령들에서 제목 용어들을 추출하여 리스트로 반환

    Args:
        collected_laws: {law_name: {'type': ..., 'data': [...]}} 형태의 딕셔너리

    Returns:
        제목 용어 리스트 (정렬됨)

    Note:
        불용어 제거를 하지 않습니다. 법령 제목에서는 "방법", "기준", "절차" 등
        모든 단어가 법적 의미를 가질 수 있기 때문입니다.
    """
    title_terms = set()

    for law_name, law_info in collected_laws.items():
        law_data = law_info.get('data', [])
        for article in law_data:
            title = article.get('제목', '')
            if title:
                # 제목에서 의미있는 용어들 추출
                # 괄호 제거 및 특수문자 정리
                cleaned_title = re.sub(r'[()\[\]{}]', '', title)
                # 2글자 이상의 한글 단어들 추출
                terms = re.findall(r'[가-힣]{2,}', cleaned_title)
                title_terms.update(terms)

    return sorted(list(title_terms))
