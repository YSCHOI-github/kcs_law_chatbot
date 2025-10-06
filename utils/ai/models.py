"""Gemini AI 모델 클라이언트 관리"""
from google import genai
import os


def get_model():
    """Gemini 모델 클라이언트 생성 (일반 에이전트용)

    Returns:
        genai.Client 인스턴스
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    client = genai.Client(api_key=api_key)
    return client


def get_model_head():
    """Gemini 모델 클라이언트 생성 (헤드 에이전트용)

    Returns:
        genai.Client 인스턴스
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    client = genai.Client(api_key=api_key)
    return client
