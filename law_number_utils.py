import re
from typing import Optional


def normalize_article_number(article_str: str) -> Optional[str]:
    """
    조문번호를 정규 숫자 형식으로 변환

    "제"와 "조" 사이의 번호만 추출 ("의X" 부분 제거):
    - "10" -> "10"
    - "0010" -> "10" (제로패딩 제거)
    - "제10조" -> "10"
    - "제42조의2" -> "42"
    - "제1-5조" -> "1-5"
    - "제10-5조의2" -> "10-5"

    Args:
        article_str: 임의 형식의 조문번호

    Returns:
        정규화된 조문번호 (숫자만, "의X" 제거) 또는 None (유효하지 않을 경우)
    """
    if not article_str or not isinstance(article_str, str):
        return None

    if len(article_str) > 50:
        return None

    article_str = article_str.strip()

    # 빈칸 제거
    article_str = re.sub(r'\s+', '', article_str)

    # "제"와 "조" 사이의 번호 추출 (패턴: 숫자[-숫자][의숫자])
    # "조" 앞까지만 추출하여 "의X" 부분 자동 제거
    pattern = r'제?(\d+(?:-\d+)?)조'
    match = re.search(pattern, article_str)

    if match:
        number_part = match.group(1)
        # 제로패딩 제거: "0010" -> "10", "10-05" -> "10-5"
        parts = number_part.split('-')
        normalized_parts = [str(int(p)) for p in parts]
        return '-'.join(normalized_parts)

    # "제"와 "조" 없이 숫자만 있는 경우 (데이터에 "42"로만 저장된 경우)
    if re.match(r'^\d+(?:-\d+)?$', article_str):
        parts = article_str.split('-')
        normalized_parts = [str(int(p)) for p in parts]
        return '-'.join(normalized_parts)

    return None
