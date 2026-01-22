"""Gemini AI 모델 클라이언트 관리 및 에러 핸들링"""
from google import genai
import os
import logging
from typing import Generator, List, Union

# 모델 상수
MODEL_FLASH = "gemini-3-flash-preview"
MODEL_FLASH_LITE = "gemini-2.5-flash-lite"
MODEL_FLASH_2_0 = "gemini-2.0-flash"

class GeminiClientWrapper:
    """Gemini API 호출 래퍼 (재시도 및 에러 핸들링 포함)"""
    
    def __init__(self):
        self.api_key = os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            # API 키가 없으면 에러를 내지 않고 클라이언트 생성을 미룸 (실제 호출 시 에러 처리)
            self.client = None
        else:
            self.client = genai.Client(api_key=self.api_key)

    def _check_client(self):
        if not self.client:
            raise ValueError("API 키가 설정되지 않았습니다. .env 파일을 확인해주세요.")

    def _handle_error(self, e: Exception) -> str:
        """예외를 사용자 친화적인 메시지로 변환"""
        error_str = str(e)
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
            return "이용량이 많아 잠시 지연되고 있습니다. 잠시 후 다시 시도해주세요. (API 한도 초과)"
        elif "401" in error_str or "403" in error_str:
            return "API 키 오류입니다. .env 파일의 API 키를 확인해주세요."
        elif "ConnectTimeout" in error_str or "ReadTimeout" in error_str:
             return "인터넷 연결 상태가 좋지 않습니다. 연결을 확인해주세요."
        elif "ValueError" in error_str: # API Key missing case
            return str(e)
        else:
            logging.error(f"Gemini API Error: {error_str}")
            return f"일시적인 오류가 발생했습니다. ({error_str})"

    def generate_content(self, contents: str, model: str = MODEL_FLASH) -> str:
        """텍스트 생성 (재시도 로직 포함)"""
        self._check_client()
        try:
            response = self.client.models.generate_content(
                model=model,
                contents=contents
            )
            return response.text
        except Exception as e:
            error_str = str(e)
            # 429/Resource Exhausted 처리 (Flash -> Flash-Lite)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if model == MODEL_FLASH:
                    print(f"⚠ [{model}] API 한도 도달. {MODEL_FLASH_LITE}로 재시도 중...")
                    return self.generate_content(contents, model=MODEL_FLASH_LITE)
            
            # 에러 메시지 반환 (호출처에서 문자열로 받아서 처리)
            # 주의: 여기서 예외를 던지는 게 아니라, 에러 메시지를 예외로 감싸서 던짐
            # 그래야 호출처의 try-except 블록에서 잡아서 사용자에게 보여줄 수 있음
            user_msg = self._handle_error(e)
            raise Exception(user_msg)

    def generate_content_stream(self, contents: str, model: str = MODEL_FLASH) -> Generator[str, None, None]:
        """스트리밍 텍스트 생성 (재시도 로직 포함)"""
        self._check_client()
        try:
            response_stream = self.client.models.generate_content_stream(
                model=model,
                contents=contents
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if model == MODEL_FLASH:
                    print(f"⚠ [{model}] 스트리밍 API 한도 도달. {MODEL_FLASH_LITE}로 재시도 중...")
                    yield from self.generate_content_stream(contents, model=MODEL_FLASH_LITE)
                    return

            user_msg = self._handle_error(e)
            yield f"\n[오류 발생] {user_msg}"

# 싱글톤 인스턴스 사용을 권장하지만, 필요시 새로 생성
def get_client() -> GeminiClientWrapper:
    return GeminiClientWrapper()

# 기존 호환성을 위해 유지 (하지만 내부적으로는 래퍼 사용 권장, 필요 없다면 삭제 가능)
# 여기서는 리팩토링 대상이므로 삭제하고 get_client로 대체
