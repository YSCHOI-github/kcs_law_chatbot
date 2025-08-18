import streamlit as st
import re


def search_laws(search_term, selected_laws, collected_laws):
    """
    법령에서 검색어를 찾아 결과를 반환하는 함수
    
    Args:
        search_term (str): 검색할 문자열
        selected_laws (list): 검색 대상 법령 리스트
        collected_laws (dict): 수집된 모든 법령 데이터
    
    Returns:
        list: 검색 결과 리스트 [{'law_name': str, 'article': dict, 'matched_content': str}]
    """
    if not search_term.strip():
        return []
    
    results = []
    search_term_lower = search_term.lower()
    
    for law_name in selected_laws:
        if law_name in collected_laws:
            law_data = collected_laws[law_name]['data']
            
            for article in law_data:
                # 조문의 모든 텍스트 필드에서 검색
                searchable_content = ""
                if '조번호' in article:
                    searchable_content += str(article['조번호']) + " "
                if '제목' in article:
                    searchable_content += str(article['제목']) + " "
                if '내용' in article:
                    searchable_content += str(article['내용']) + " "
                
                # 대소문자 구분 없이 검색
                if search_term_lower in searchable_content.lower():
                    # 매칭된 부분 하이라이트용 처리
                    highlighted_content = highlight_search_term(searchable_content, search_term)
                    
                    results.append({
                        'law_name': law_name,
                        'article': article,
                        'matched_content': highlighted_content
                    })
    
    return results


def highlight_search_term(content, search_term):
    """
    검색어를 하이라이트 처리하는 함수
    
    Args:
        content (str): 원본 텍스트
        search_term (str): 검색어
    
    Returns:
        str: 하이라이트 처리된 HTML 텍스트
    """
    if not search_term.strip():
        return content
    
    # 대소문자 구분 없이 검색어를 찾아서 하이라이트
    pattern = re.compile(re.escape(search_term), re.IGNORECASE)
    highlighted = pattern.sub(f'<mark style="background-color: yellow;">{search_term}</mark>', content)
    
    return highlighted


def display_search_results(results):
    """
    검색 결과를 카드 형태로 표시하는 함수
    
    Args:
        results (list): search_laws 함수의 반환값
    """
    if not results:
        st.info("검색 결과가 없습니다.")
        return
    
    st.success(f"총 {len(results)}개의 조문에서 검색어를 찾았습니다.")
    
    for i, result in enumerate(results):
        with st.container():
            # 카드 스타일의 컨테이너
            st.markdown(f"""
            <div style="
                border: 1px solid #ddd; 
                border-radius: 8px; 
                padding: 15px; 
                margin: 10px 0;
                background-color: #f9f9f9;
            ">
            """, unsafe_allow_html=True)
            
            # 법령명
            st.markdown(f"**📚 {result['law_name']}**")

            # 조문번호
            if '조번호' in result['article']:
                    st.markdown(f"**조번호:** {result['article']['조번호']}")
            
            # 조문 제목
            if '제목' in result['article'] and result['article']['제목']:
                st.markdown(f"**제목:** {result['article']['제목']}")
            
            # 조문 내용 (하이라이트 적용)
            if '내용' in result['article'] and result['article']['내용']:
                st.markdown("**내용:**")
                formatted = result['matched_content'].replace('\n', '<br>')
                st.markdown(
                    f"<div style='white-space: pre-wrap;'>{formatted}</div>",
                    unsafe_allow_html=True,
                )
            
            st.markdown("</div>", unsafe_allow_html=True)


def render_law_search_ui(collected_laws):
    """
    법령 검색 UI를 렌더링하는 함수
    
    Args:
        collected_laws (dict): 수집된 모든 법령 데이터
    """
    if not collected_laws:
        st.warning("검색할 법령 데이터가 없습니다. 먼저 법령을 수집해주세요.")
        return
    
    st.header("🔍 법령 원문 검색")
    
    # 검색 대상 법령 선택
    law_names = list(collected_laws.keys())
    selected_laws = st.multiselect(
        "검색할 법령을 선택하세요:",
        options=law_names,
        default=law_names,  # 기본값으로 모든 법령 선택
        key="law_search_selection"
    )
    
    # 검색어 입력
    search_term = st.text_input(
        "검색어를 입력하세요:",
        placeholder="예: 민법, 계약, 손해배상",
        key="law_search_term"
    )
    
    # 검색 실행
    if search_term and selected_laws:
        with st.spinner("검색 중..."):
            results = search_laws(search_term, selected_laws, collected_laws)
            display_search_results(results)
    elif search_term and not selected_laws:
        st.warning("검색할 법령을 선택해주세요.")