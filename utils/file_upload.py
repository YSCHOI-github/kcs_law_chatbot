"""파일 업로드 처리 모듈

사용자가 업로드한 PDF/TXT 파일을 JSON 형식으로 변환합니다.
"""
import streamlit as st
from pathlib import Path
from typing import Dict, List, BinaryIO
import io

from pdf_txt_json import convert_file_to_json


def convert_uploaded_file_to_json(uploaded_file) -> tuple:
    """Streamlit UploadedFile 객체를 JSON 데이터로 변환

    Args:
        uploaded_file: Streamlit file_uploader가 반환한 UploadedFile 객체

    Returns:
        (law_name, json_data, error_msg) 튜플
        - law_name: 파일명에서 추출한 법령명 (확장자 제거)
        - json_data: [{"조번호": ..., "제목": ..., "내용": ...}, ...] 형식
        - error_msg: 에러 발생 시 메시지, 정상이면 None

    Raises:
        ValueError: 지원하지 않는 파일 형식
        RuntimeError: PDF 처리 모듈 없음
    """
    try:
        # 파일명에서 법령명 추출 (확장자 제거)
        law_name = Path(uploaded_file.name).stem

        # BinaryIO로 변환하여 convert_file_to_json에 전달
        file_buffer = io.BytesIO(uploaded_file.read())

        # pdf_txt_json의 convert_file_to_json 활용
        json_data = convert_file_to_json(file_buffer, uploaded_file.name)

        # 조문이 하나도 인식되지 않은 경우 폴백 처리
        if not json_data or len(json_data) == 0:
            # 전체 텍스트를 단일 조문으로 처리
            file_buffer.seek(0)  # 버퍼 재설정
            if uploaded_file.name.lower().endswith('.txt'):
                text_content = file_buffer.read().decode('utf-8', errors='ignore')
            else:
                # PDF는 전체 텍스트 추출 불가능하므로 에러 반환
                return law_name, None, "조문을 인식할 수 없습니다. 파일 형식을 확인해주세요."

            json_data = [{
                "조번호": "1",
                "제목": "전체 내용",
                "내용": text_content
            }]

        return law_name, json_data, None

    except ValueError as e:
        return None, None, f"지원하지 않는 파일 형식: {str(e)}"
    except RuntimeError as e:
        return None, None, f"PDF 처리 오류: {str(e)}"
    except Exception as e:
        return None, None, f"파일 처리 중 오류 발생: {str(e)}"


def process_uploaded_files(uploaded_files) -> Dict[str, dict]:
    """다중 파일 처리

    Args:
        uploaded_files: Streamlit file_uploader가 반환한 파일 리스트

    Returns:
        {
            "법령명1": {
                "type": "user_upload",
                "data": [{"조번호": ..., "제목": ..., "내용": ...}, ...]
            },
            "법령명2": {...}
        }

    Note:
        - 파싱 실패한 파일은 경고 메시지만 표시하고 스킵
        - 성공한 파일만 딕셔너리에 포함
    """
    result = {}
    success_count = 0
    fail_count = 0

    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"처리 중: {uploaded_file.name} ({idx + 1}/{len(uploaded_files)})")

        law_name, json_data, error_msg = convert_uploaded_file_to_json(uploaded_file)

        if error_msg:
            st.warning(f"{uploaded_file.name} 처리 실패: {error_msg}")
            fail_count += 1
        else:
            result[law_name] = {
                'type': 'user_upload',
                'data': json_data
            }
            success_count += 1
            st.success(f"{law_name} 처리 완료 ({len(json_data)}개 조문)")

        progress_bar.progress((idx + 1) / len(uploaded_files))

    progress_bar.empty()
    status_text.empty()

    if success_count > 0:
        st.info(f"총 {success_count}개 법령 업로드 성공, {fail_count}개 실패")

    return result
