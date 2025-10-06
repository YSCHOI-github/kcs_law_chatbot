"""멀티에이전트 시스템

개별 법령 전문가 에이전트와 헤드 에이전트로 구성됩니다.
"""
from typing import Dict, List, Tuple
from ..tfidf.search import search_relevant_chunks
from .models import get_model, get_model_head


def get_agent_response(law_name: str, question: str, history: str,
                      embedding_data: Dict, expanded_keywords: str,
                      search_weights: dict = None) -> Tuple[str, str]:
    """개별 법령 전문가 에이전트 응답 생성

    Args:
        law_name: 법령명
        question: 사용자 질문
        history: 대화 히스토리
        embedding_data: 벡터화 데이터 딕셔너리
        expanded_keywords: AI 확장 키워드
        search_weights: 검색 가중치

    Returns:
        (law_name, response_text) 튜플
    """
    if law_name not in embedding_data:
        return law_name, "해당 법령 데이터를 찾을 수 없습니다."

    vec, title_vec, mat, title_mat, chunks = embedding_data[law_name]
    if vec is None:
        return law_name, "해당 법령 데이터를 처리할 수 없습니다."

    try:
        # TF-IDF 검색으로 관련 조문 찾기
        final_context = search_relevant_chunks(
            question, expanded_keywords,
            vec, title_vec, mat, title_mat, chunks,
            search_weights=search_weights
        )

        if not final_context:
            return law_name, "관련 법령 조항을 찾을 수 없습니다."

        # AI 답변 생성
        prompt = f"""
        당신은 대한민국 {law_name} 법률 전문가입니다.

        아래는 질문과 관련된 법령 조항들입니다:
        {final_context}

        이전 대화:
        {history}

        질문: {question}

        # 응답 지침
        1. 제공된 법령 조항에 기반하여 정확하게 답변해주세요.
        2. 답변에 사용한 법령 조항(조번호, 제목)을 명확히 인용해주세요.
        3. 관련된 조항이 여러 개인 경우 모두 참고하여 종합적으로 답변해주세요.
        4. 법령에 명시되지 않은 내용은 추측하지 말고, 알 수 없다고 답변해주세요.
        5. 법령 조항 번호와 제목을 정확히 인용하여 신뢰성을 높여주세요.
        """

        client = get_model()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return law_name, response.text

    except Exception as e:
        return law_name, f"답변 생성 중 오류: {str(e)}"


def get_head_agent_response(responses: List[Tuple[str, str]],
                           question: str, history: str) -> str:
    """헤드 에이전트 통합 답변 생성 (non-streaming)

    Args:
        responses: [(law_name, response), ...] 개별 에이전트 응답 리스트
        question: 사용자 질문
        history: 대화 히스토리

    Returns:
        통합 답변 (문자열)
    """
    successful_responses = []
    error_messages = []

    for r in responses:
        if isinstance(r, Exception):
            error_messages.append(f"- 답변 생성 중 오류 발생: {r}")
        elif isinstance(r, tuple) and len(r) == 2:
            name, result = r
            if isinstance(result, Exception):
                error_messages.append(f"- {name} 전문가 답변 생성 오류: {result}")
            else:
                successful_responses.append((name, result))
        else:
            error_messages.append(f"- 알 수 없는 형식의 응답: {r}")

    # 성공적인 응답만 결합
    combined = "\n\n".join([f"=== {n} 전문가 답변 ===\n{r}" for n, r in successful_responses])

    # 오류 메시지가 있는 경우 프롬프트에 포함
    if error_messages:
        error_info = "\n".join(error_messages)
        combined += f"\n\n--- 일부 답변 생성 실패 ---\n{error_info}"

    # 모든 답변이 실패한 경우
    if not successful_responses:
        return f"모든 법률 전문가의 답변을 가져오는 데 실패했습니다.\n{combined}"

    prompt = f"""
당신은 법률 전문가로서 여러 법령 자료를 통합하여 종합적인 답변을 제공하는 전문가입니다.

{combined}

이전 대화:
{history}

질문: {question}

# 응답 지침
1. 여러 전문가 답변을 분석하고 통합하여 최종 답변을 제공합니다.
2. 제공된 법령 조항들에 기반하여 정확하게 답변해주세요.
3. 답변에 사용한 법령 조항(조번호, 제목)을 명확히 인용해주세요.
4. 관련 조항이 여러 법령에 걸쳐 있는 경우 모두 참고하여 종합적으로 답변해주세요.
5. 법령에 명시되지 않은 내용은 추측하지 말고, 알 수 없다고 답변해주세요.
6. 답변은 두괄식으로 작성하며, 결론을 먼저 제시합니다.
7. 상충되는 내용이 있는 경우 이를 명확히 구분하여 설명합니다.
8. 일부 답변 생성에 실패한 경우, 해당 사실을 언급하고 성공한 답변만으로 종합적인 결론을 내립니다.
"""

    try:
        client = get_model_head()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"최종 답변 생성 중 오류가 발생했습니다: {str(e)}"


def get_head_agent_response_stream(responses: List[Tuple[str, str]],
                                   question: str, history: str):
    """헤드 에이전트 통합 답변을 스트리밍으로 생성

    Args:
        responses: [(law_name, response), ...] 개별 에이전트 응답 리스트
        question: 사용자 질문
        history: 대화 히스토리

    Yields:
        답변 청크 (문자열)
    """
    successful_responses = []
    error_messages = []

    for r in responses:
        if isinstance(r, Exception):
            error_messages.append(f"- 답변 생성 중 오류 발생: {r}")
        elif isinstance(r, tuple) and len(r) == 2:
            name, result = r
            if isinstance(result, Exception):
                error_messages.append(f"- {name} 전문가 답변 생성 오류: {result}")
            else:
                successful_responses.append((name, result))
        else:
            error_messages.append(f"- 알 수 없는 형식의 응답: {r}")

    # 성공적인 응답만 결합
    combined = "\n\n".join([f"=== {n} 전문가 답변 ===\n{r}" for n, r in successful_responses])

    # 오류 메시지가 있는 경우 프롬프트에 포함
    if error_messages:
        error_info = "\n".join(error_messages)
        combined += f"\n\n--- 일부 답변 생성 실패 ---\n{error_info}"

    # 모든 답변이 실패한 경우
    if not successful_responses:
        yield f"모든 법률 전문가의 답변을 가져오는 데 실패했습니다.\n{combined}"
        return

    prompt = f"""
당신은 법률 전문가로서 여러 법령 자료를 통합하여 종합적인 답변을 제공하는 전문가입니다.

{combined}

이전 대화:
{history}

질문: {question}

# 응답 지침
1. 여러 전문가 답변을 분석하고 통합하여 최종 답변을 제공합니다.
2. 제공된 법령 조항들에 기반하여 정확하게 답변해주세요.
3. 답변에 사용한 법령 조항(조번호, 제목)을 명확히 인용해주세요.
4. 관련 조항이 여러 법령에 걸쳐 있는 경우 모두 참고하여 종합적으로 답변해주세요.
5. 법령에 명시되지 않은 내용은 추측하지 말고, 알 수 없다고 답변해주세요.
6. 답변은 두괄식으로 작성하며, 결론을 먼저 제시합니다.
7. 상충되는 내용이 있는 경우 이를 명확히 구분하여 설명합니다.
8. 일부 답변 생성에 실패한 경우, 해당 사실을 언급하고 성공한 답변만으로 종합적인 결론을 내립니다.
"""

    try:
        client = get_model_head()
        response_stream = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt
        )

        for chunk in response_stream:
            if chunk.text:
                yield chunk.text

    except Exception as e:
        yield f"최종 답변 생성 중 오류가 발생했습니다: {str(e)}"
