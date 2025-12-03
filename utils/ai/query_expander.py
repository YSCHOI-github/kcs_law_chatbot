"""AI 기반 쿼리 확장 (Gemini)

사용자 쿼리를 분석하여 유사 질문 생성 및 키워드 확장을 수행합니다.
"""
from google import genai
import os
import re
from typing import List


class QueryExpander:
    """Gemini를 사용한 쿼리 확장 (키워드 추출, 유사질문 생성)"""

    def __init__(self, title_terms: List[str] = None):
        """QueryExpander 초기화

        Args:
            title_terms: 법령 제목 용어 리스트
        """
        api_key = os.getenv('GOOGLE_API_KEY')
        self.client = genai.Client(api_key=api_key)
        self.title_terms = title_terms or []

    def extract_keywords_and_synonyms(self, query: str, search_weights: dict = None) -> str:
        """키워드 추출 및 유사어 생성 - 제목 가중치 설정에 따라 다른 전략 사용

        Args:
            query: 사용자 쿼리
            search_weights: {'content': 1.0, 'title': 0.0} 형태의 가중치

        Returns:
            확장된 키워드 문자열
        """
        # 제목 가중치 확인
        title_weight = search_weights.get('title', 0.5) if search_weights else 0.5
        title_terms_text = ', '.join(self.title_terms) if self.title_terms else '없음'

        if title_weight > 0.0:
            # 제목을 활용하는 경우: 기존 방식
            prompt = f"""
당신은 대한민국 법령 전문가입니다. 다음 질문을 분석하여 법령에서 참고조문 검색에 도움이 되는 키워드를 생성해주세요.

질문: "{query}"

다음 작업을 수행해주세요:
1. 질문에서 핵심 키워드 및 유사어, 동의어, 관련어 추출
2. 반드시 아래 법령 제목 용어들 중에서 핵심 키워드, 유사어, 동의어, 관련어를 우선적으로 선택

우선적으로 참고할 법령 제목 용어들:
{title_terms_text}

응답 형식: 키워드와 유사어들을 공백으로 구분하여 한 줄로 나열해주세요.
예시: 관세조사 세액심사 관세법 세관장 세액 통관 사후심사

단어들만 나열하고 다른 설명은 하지 마세요.
"""
        else:
            # 제목을 무시하는 경우: 내용 중심 키워드 추출
            prompt = f"""
당신은 대한민국 법령 전문가입니다. 다음 질문을 분석하여 법령에서 참고조문 검색에 도움이 되는 키워드와 유사어를 생성해주세요.

질문: "{query}"

다음 작업을 수행해주세요:
1. 질문에서 핵심 키워드 및 유사어, 동의어, 관련어 추출
2. 반드시 아래 법령 제목 용어들 중에서 핵심 키워드, 유사어, 동의어, 관련어를 우선적으로 선택
3. 복합어의 경우 단어 분리도 포함하고, 검색에 유용한 관련 단어들을 추가

우선적으로 참고할 법령 제목 용어들:
{title_terms_text}

응답 형식: 키워드와 유사어들을 공백으로 구분하여 한 줄로 나열해주세요.
예시: 관세조사 세액심사 관세법 세관장 세액 통관 사후심사

단어들만 나열하고 다른 설명은 하지 마세요.
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )
            # 응답에서 키워드들만 추출
            keywords_text = response.text.strip()
            # 불필요한 문자 제거하고 단어들만 추출
            keywords = re.findall(r'[가-힣]{2,}', keywords_text)

            # 중복 제거하여 반환
            return ' '.join(list(set(keywords)))

        except Exception as e:
            print(f"키워드 추출 오류: {e}")
            # 폴백: 원본 쿼리에서 한글 단어 추출
            fallback_keywords = re.findall(r'[가-힣]{2,}', query)
            return ' '.join(list(set(fallback_keywords)))

    def generate_similar_questions(self, original_query: str, search_weights: dict = None) -> List[str]:
        """유사한 질문 생성 - 제목 가중치 설정에 따라 다른 전략 사용

        Args:
            original_query: 원본 쿼리
            search_weights: {'content': 1.0, 'title': 0.0} 형태의 가중치

        Returns:
            유사 질문 리스트 (최대 3개)
        """
        # 제목 가중치 확인
        title_weight = search_weights.get('title', 0.5) if search_weights else 0.5
        title_terms_text = ', '.join(self.title_terms) if self.title_terms else '없음'

        if title_weight > 0.0:
            prompt = f"""
원본 질문: "{original_query}"

[법령 제목 용어]: {title_terms_text}

위 [법령 제목 용어]들을 최대한 활용하여 짧고 간결한 유사 질문 3개를 생성하세요.

생성 규칙:
1. [법령 제목 용어] 최우선 사용 (일반 용어 → [법령 제목 용어]로 교체)
2. 15단어 이내의 간결한 질문
3. 핵심 내용만 포함, 부연설명 제거
4. "~인가?", "~은?", "~기준은?" 등 단순 형태

예시1:
- 원본 질문 : "수입 원재료로 생산한 국내물품의 원산지 판정 기준은?"
- 법령 용어 : "국내생산물품등의 원산지 판정 기준"
- 유사 질문 : "국내생산물품등의 원산지 판정 기준은?"

예시2:
- 원본 질문 : "수입물품에 대한 FTA 특혜관세를 사후에 신청하는 절차 및 기한은?"
- 법령 용어 : "협정관세 사후적용"
- 유사 질문 : "협정관세 사후적용 신청 절차 및 기한은?"

형식:
1. (간결한 유사질문)
2. (간결한 유사질문)
3. (간결한 유사질문)

"""
        else:
            # 제목을 무시하는 경우: 내용 중심 유사질문 생성
            prompt = f"""

원본 질문: "{original_query}"

[법령 제목 용어]: {title_terms_text}

위 원본 질문과 유사한 의미를 가진 질문들을 3개 생성해주세요.

생성 규칙:
1. [법령 제목 용어] 최우선 사용 (일반 용어 → [법령 제목 용어]로 교체)
2. 그외에 법령 검색에 도움이 되도록 다양한 표현과 용어를 사용해주세요.

유사 질문 3개를 다음 형식으로 생성해주세요:
1. (첫 번째 유사 질문)
2. (두 번째 유사 질문)
3. (세 번째 유사 질문)

각 질문은 원본과 의미는 같지만 다른 표현이나 용어를 사용해주세요.
"""

        try:
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                print("⚠ 유사 질문 생성: API 한도 도달. Flash-Lite로 재시도 중...")
                try:
                    response = self.client.models.generate_content(
                        model="gemini-2.5-flash-lite",
                        contents=prompt
                    )
                except Exception as e2:
                    print(f"유사 질문 생성 오류 (Flash-Lite): {e2}")
                    return [original_query]
            else:
                print(f"유사 질문 생성 오류: {e}")
                return [original_query]

        try:
            # 응답에서 질문들 추출
            questions = []
            lines = response.text.strip().split('\n')
            for line in lines:
                # 숫자와 점으로 시작하는 줄에서 질문 추출
                match = re.search(r'^\d+\.\s*(.+)', line.strip())
                if match:
                    questions.append(match.group(1))

            # 최대 3개까지만 반환
            return questions[:3]

        except Exception as e:
            print(f"유사 질문 파싱 오류: {e}")
            # 폴백: 원본 질문만 반환
            return [original_query]


# 하위 호환성: 기존 클래스명
QueryPreprocessor = QueryExpander
