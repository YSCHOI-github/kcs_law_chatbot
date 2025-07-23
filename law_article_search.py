# law_article_search.py

import streamlit as st
import re

def highlight_search_term(content, search_term):
    """검색어를 찾아 <mark> 태그로 감싸 하이라이트하는 함수"""
    if not search_term.strip() or not content:
        return content
    
    # re.escape를 사용하여 검색어 내의 특수 문자가 정규식으로 해석되지 않도록 처리
    # re.IGNORECASE 플래그로 대소문자 구분 없이 검색
    try:
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        # 검색된 모든 부분을 찾아 하이라이트 처리
        return pattern.sub(f'<mark style="background-color: yellow; color: black;">\\g<0></mark>', content)
    except re.error:
        # 정규식 오류 발생 시 원본 반환
        return content


def search_laws(search_term, selected_laws, law_data_dict):
    """
    법령 데이터에서 검색어를 찾아 결과를 반환하는 함수.
    JSON 구조(조/항/목)와 일반 텍스트 구조를 모두 지원합니다.
    """
    if not search_term.strip():
        return []
    
    results = []
    search_term_lower = search_term.lower()

    for law_name in selected_laws:
        if law_name in law_data_dict:
            law_content = law_data_dict[law_name]

            # 1. 법령 데이터가 JSON 구조(조문 리스트)인 경우
            if isinstance(law_content, list):
                for article in law_content:
                    # 조번호, 제목, 내용을 합쳐서 검색 대상 텍스트 생성
                    searchable_text = f"{article.get('조번호', '')} {article.get('제목', '')} {article.get('내용', '')}"
                    if search_term_lower in searchable_text.lower():
                        # 내용 부분에만 하이라이트 적용
                        highlighted_content = highlight_search_term(article.get('내용', ''), search_term)
                        results.append({
                            'law_name': law_name,
                            'article': article, # 조문 전체 정보 저장
                            'matched_content': highlighted_content
                        })
            
            # 2. 법령 데이터가 일반 텍스트(str)인 경우
            elif isinstance(law_content, str):
                if search_term_lower in law_content.lower():
                    # 전체 텍스트에서 하이라이트 적용
                    highlighted_content = highlight_search_term(law_content, search_term)
                    # 결과를 조문 형식과 유사하게 맞춤
                    results.append({
                        'law_name': law_name,
                        'article': {'조번호': '전체', '제목': '본문', '내용': law_content},
                        'matched_content': highlighted_content
                    })
    return results


def display_search_results(results):
    """검색 결과를 UI에 표시하는 함수"""
    if not results:
        st.info("검색 결과가 없습니다.")
        return
    
    st.success(f"총 {len(results)}개의 검색 결과를 찾았습니다.")
    
    for result in results:
        article = result['article']
        # 카드 스타일을 위한 HTML/CSS
        st.markdown("""
        <div style="border: 1px solid #e1e4e8; border-radius: 6px; padding: 16px; margin-bottom: 16px;">
        """, unsafe_allow_html=True)
        
        st.markdown(f"##### 📚 {result['law_name']}")
        
        # 조번호와 제목이 있는 경우에만 표시
        if article.get('조번호') and article.get('조번호') != '전체':
            st.markdown(f"**{article['조번호']} ({article.get('제목', '제목 없음')})**")

        # 하이라이트된 내용 표시
        st.markdown(result['matched_content'], unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

def render_law_search_ui(law_data_dict):
    """법령 검색 전체 UI를 렌더링하는 메인 함수"""
    st.header("법령 원문 검색 (Ctrl+F)")
    
    if not law_data_dict:
        st.warning("먼저 카테고리를 선택하여 법령 데이터를 불러와주세요.")
        return

    all_law_names = list(law_data_dict.keys())
    
    # 검색할 법령 선택 (multiselect)
    selected_laws = st.multiselect(
        "검색 대상 법령",
        options=all_law_names,
        default=all_law_names
    )
    
    # 검색어 입력
    search_term = st.text_input("검색어", placeholder="찾고 싶은 단어를 입력하세요.")
    
    # 검색 실행
    if st.button("검색 실행", use_container_width=True) and search_term:
        if not selected_laws:
            st.error("검색할 법령을 하나 이상 선택해주세요.")
        else:
            with st.spinner("법령을 검색하고 있습니다..."):
                search_results = search_laws(search_term, selected_laws, law_data_dict)
                display_search_results(search_results)