import re
import json
from pdfminer.high_level import extract_text
import streamlit as st
from typing import List, Dict, Any
import tempfile
import os

def filter_empty_titles_from_json(json_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """제목이 빈 문자열이거나 null인 항목들을 제거하는 함수
    
    Args:
        json_data: JSON 데이터 리스트
        
    Returns:
        제목이 빈 문자열이나 null이 아닌 항목들만 포함한 리스트
    """
    filtered_data = []
    removed_count = 0
    
    for item in json_data:
        title = item.get("제목")
        # None, 빈 문자열, 공백만 있는 경우 모두 제외
        if title is not None and str(title).strip():
            filtered_data.append(item)
        else:
            removed_count += 1
    
    if removed_count > 0:
        st.info(f"📝 업로드된 파일에서 제목이 없는 {removed_count}개 항목을 제거했습니다.")
    
    return filtered_data

def extract_text_from_pdf(pdf_file) -> str:
    """
    업로드된 PDF 파일에서 텍스트를 추출하는 함수
    
    Args:
        pdf_file: Streamlit 업로드 파일 객체
    
    Returns:
        str: 추출된 텍스트
    """
    try:
        # 임시 파일로 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_file_path = tmp_file.name
        
        # PDF에서 텍스트 추출
        text = extract_text(tmp_file_path)
        
        # 임시 파일 삭제
        os.unlink(tmp_file_path)
        
        return text
    
    except Exception as e:
        st.error(f"PDF 텍스트 추출 중 오류 발생: {str(e)}")
        return ""

def parse_text_to_json(text: str) -> List[Dict[str, Any]]:
    """
    PDF에서 추출한 텍스트를 조문별로 파싱하여 JSON 구조로 변환하는 함수
    
    Args:
        text (str): PDF에서 추출한 전체 텍스트
    
    Returns:
        list: 파싱된 조문들의 리스트
    """
    # 텍스트를 줄 단위로 분할하여 처리하기 쉽게 만듦
    lines = text.splitlines()
    
    조문들 = []  # 파싱된 모든 조문을 저장할 리스트
    
    # 조문 패턴을 정규식으로 정의 (예: "제1조(목적)", "제1조의2(정의)" 등)
    조문_패턴 = re.compile(r"(제\d+(?:-\d+)?조(?:의\d+)?)\((.*?)\)")

    for line in lines:
        # 각 줄이 조문 패턴과 일치하는지 확인
        매치 = 조문_패턴.match(line.strip())
        if 매치:
            # 조문 패턴이 발견되면 조번호와 제목을 추출
            조번호 = 매치.group(1)  # 조번호 추출 (예: "제1조")
            제목 = 매치.group(2)    # 제목 추출 (예: "목적")
            내용 = line.replace(매치.group(0), "").strip()  # 조문 제목 부분을 제거하고 나머지 내용 추출
            
            조문들.append({
                "조번호": 조번호,
                "제목": 제목,
                "내용": 내용
            })
        elif 조문들:
            # 기존 조문의 연속 내용인 경우, 마지막 조문의 내용에 추가
            조문들[-1]["내용"] += f" {line.strip()}"
    
    return 조문들

def refine_articles(조문들):
    """
    조문 내용에서 불필요한 구조 표시어(장/절/관)를 제거하는 함수
    
    Args:
        조문들 (list): 원본 조문 리스트
    
    Returns:
        list: 정제된 조문 리스트
    """
    정제된_조문들 = []
    
    # 구조 표시어 패턴 정의 (예: "제2절", "제3장", "제1관")
    구조_패턴 = re.compile(r"제\d+(절|장|관)")
    
    for 조문 in 조문들:
        내용 = 조문["내용"]
        매치 = 구조_패턴.search(내용)
        
        if 매치:
            # 구조 표시어가 발견되면 해당 부분을 제거
            분할된_내용 = 내용.split(매치.group(0))
            조문["내용"] = 분할된_내용[0].strip()
        
        정제된_조문들.append(조문)
    
    return 정제된_조문들

def remove_bracketed_text(내용):
    """
    내용에서 꺾쇠괄호(<>)나 대괄호([]) 안의 텍스트를 제거하는 함수
    
    Args:
        내용 (str): 원본 텍스트
    
    Returns:
        str: 괄호 내용이 제거된 텍스트
    """
    # 정규식을 사용하여 <...>와 [...] 패턴의 모든 텍스트 제거
    return re.sub(r"<.*?>|\[.*?\]", "", 내용)

def convert_pdf_to_json(pdf_file) -> List[Dict[str, Any]]:
    """
    PDF 파일을 JSON 형태로 변환하는 메인 함수
    
    Args:
        pdf_file: Streamlit 업로드 파일 객체
    
    Returns:
        list: 파싱된 조문들의 리스트
    """
    try:
        # 1. PDF에서 텍스트 추출
        text = extract_text_from_pdf(pdf_file)
        
        if not text:
            st.error("PDF에서 텍스트를 추출할 수 없습니다.")
            return []
        
        # 2. 텍스트를 조문별로 파싱
        조문들 = parse_text_to_json(text)
        
        if not 조문들:
            st.warning("조문을 찾을 수 없습니다. PDF 형식을 확인해주세요.")
            return []
        
        # 3. 조문 내용 정제
        정제된_조문들 = refine_articles(조문들)

        # 4. 조문 내용에서 괄호 안의 텍스트 제거
        for 조문 in 정제된_조문들:
            조문["내용"] = remove_bracketed_text(조문["내용"])

        return 정제된_조문들
    
    except Exception as e:
        st.error(f"PDF 변환 중 오류 발생: {str(e)}")
        return []
    


def validate_json_structure(json_data: List[Dict[str, Any]]) -> bool:
    """
    변환된 JSON 구조가 올바른지 검증하는 함수
    
    Args:
        json_data: 검증할 JSON 데이터
    
    Returns:
        bool: 구조가 올바른지 여부
    """
    if not isinstance(json_data, list):
        return False
    
    required_keys = {"조번호", "제목", "내용"}
    
    for item in json_data:
        if not isinstance(item, dict):
            return False
        if not required_keys.issubset(item.keys()):
            return False
    
    return True

def preview_json_data(json_data: List[Dict[str, Any]], max_items: int = 3) -> None:
    """
    변환된 JSON 데이터를 미리보기로 표시하는 함수
    
    Args:
        json_data: 표시할 JSON 데이터
        max_items: 표시할 최대 항목 수
    """
    if not json_data:
        st.warning("표시할 데이터가 없습니다.")
        return
    
    st.subheader("🔍 변환 결과 미리보기")
    st.info(f"총 {len(json_data)}개의 조문이 변환되었습니다.")
    
    for i, item in enumerate(json_data[:max_items]):
        with st.expander(f"📄 {item['조번호']} - {item['제목']}"):
            st.write(f"**조번호:** {item['조번호']}")
            st.write(f"**제목:** {item['제목']}")
            st.write(f"**내용:** {item['내용'][:200]}{'...' if len(item['내용']) > 200 else ''}")
    
    if len(json_data) > max_items:
        st.info(f"... 및 {len(json_data) - max_items}개 조문 더")

def download_json_file(json_data: List[Dict[str, Any]], filename: str) -> None:
    """
    JSON 데이터를 다운로드 가능한 파일로 제공하는 함수
    
    Args:
        json_data: 다운로드할 JSON 데이터
        filename: 파일명
    """
    if not json_data:
        return
    
    json_str = json.dumps(json_data, ensure_ascii=False, indent=2)
    
    st.download_button(
        label="📥 JSON 파일 다운로드",
        data=json_str,
        file_name=f"{filename}.json",
        mime="application/json",
        help="변환된 JSON 파일을 다운로드합니다."
    )