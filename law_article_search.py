import streamlit as st
import re


def parse_article_query(search_term):
    """
    조문번호 검색 쿼리를 파싱하는 함수
    예: "관세법 제10조", "관세법10조", "관세법 10조" -> ("관세법", "제10조")

    Args:
        search_term (str): 검색어

    Returns:
        tuple: (법령명, 조번호) 또는 None (조문번호 쿼리가 아닌 경우)
    """
    # 띄어쓰기 무시하고 "법령명 + 제?숫자조" 패턴 매칭
    # 패턴: (법|령|규칙|규정|고시|훈령|예규 등으로 끝나는 문자열) + (제?숫자-?숫자?조의?숫자?)
    pattern = r'(.+?(?:법|령|규칙|규정|고시|훈령|예규|특례법))\s*(제?\s*[\d\-]+\s*조(?:의\s*\d+)?)'

    match = re.search(pattern, search_term, re.IGNORECASE)
    if match:
        law_name = match.group(1).strip()
        article_num_raw = match.group(2).strip()

        # 조번호 정규화: 띄어쓰기 제거, "제" 추가 (없으면)
        article_num = re.sub(r'\s+', '', article_num_raw)
        if not article_num.startswith('제'):
            article_num = '제' + article_num

        return (law_name, article_num)

    return None


def search_laws(search_term, selected_laws, collected_laws):
    """
    법령에서 검색어를 찾아 결과를 반환하는 함수
    조문번호 검색과 일반 키워드 검색을 모두 지원

    Args:
        search_term (str): 검색할 문자열
        selected_laws (list): 검색 대상 법령 리스트
        collected_laws (dict): 수집된 모든 법령 데이터

    Returns:
        list: 검색 결과 리스트 [{'law_name': str, 'article': dict, 'matched_content': str, 'search_mode': str}]
    """
    if not search_term.strip():
        return []

    results = []

    # 조문번호 검색 쿼리인지 확인
    article_query = parse_article_query(search_term)

    if article_query:
        # 조문번호 검색 모드
        target_law_name, target_article_num = article_query

        for law_name in selected_laws:
            if law_name in collected_laws:
                # 법령명 부분 매칭 (예: "관세법" 검색 시 "관세법 시행령"도 매칭)
                if target_law_name not in law_name:
                    continue

                law_data = collected_laws[law_name]['data']

                for article in law_data:
                    if '조번호' in article:
                        article_num = str(article['조번호']).strip()

                        # 조번호 정확 매칭
                        if article_num == target_article_num:
                            # 전체 내용 하이라이트 (조번호 강조)
                            searchable_content = ""
                            if '조번호' in article:
                                searchable_content += str(article['조번호']) + " "
                            if '제목' in article:
                                searchable_content += str(article['제목']) + " "
                            if '내용' in article:
                                searchable_content += str(article['내용']) + " "

                            highlighted_content = highlight_search_term(searchable_content, target_article_num)

                            results.append({
                                'law_name': law_name,
                                'article': article,
                                'matched_content': highlighted_content,
                                'search_mode': 'article_number',
                                'law_type': collected_laws[law_name].get('type', '기타')
                            })
    else:
        # 일반 키워드 검색 모드
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
                            'matched_content': highlighted_content,
                            'search_mode': 'keyword',
                            'law_type': collected_laws[law_name].get('type', '기타')
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


def get_law_type_icon_and_color(law_type):
    """
    법령 타입에 따른 아이콘과 색상을 반환하는 함수

    Args:
        law_type (str): 법령 타입

    Returns:
        tuple: (아이콘, 배경색, 테두리색)
    """
    type_styles = {
        '법률 API': ('⚖️', 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', '#5a67d8'),
        '행정규칙 API': ('📋', 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', '#e53e3e'),
        '3단비교 API': ('📊', 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', '#3182ce'),
        '사용자 업로드': ('📤', 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)', '#38a169'),
        '기타 API': ('📄', 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)', '#718096')
    }

    return type_styles.get(law_type, type_styles['기타 API'])


def display_search_results(results):
    """
    검색 결과를 접이식 expander로 표시하는 함수 (고급 디자인)

    Args:
        results (list): search_laws 함수의 반환값
    """
    if not results:
        st.info("검색 결과가 없습니다.")
        return

    # 검색 결과 헤더
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    ">
        <h2 style="margin: 0; font-size: 24px;">🔍 검색 결과</h2>
        <p style="margin: 10px 0 0 0; font-size: 16px;">총 <strong>{len(results)}개</strong>의 조문을 찾았습니다</p>
    </div>
    """, unsafe_allow_html=True)

    # 각 검색 결과를 expander로 표시
    for i, result in enumerate(results):
        article = result['article']
        law_name = result['law_name']
        law_type = result.get('law_type', '기타')

        # 법령 타입별 아이콘 및 색상
        icon, bg_gradient, border_color = get_law_type_icon_and_color(law_type)

        # 조문번호
        article_num = article.get('조번호', '조번호 없음')

        # 조문 제목 (없으면 내용 일부 표시)
        title = article.get('제목', '')
        if not title and '내용' in article:
            # 제목이 없으면 내용의 첫 50자
            title = article['내용'][:50] + '...' if len(article['내용']) > 50 else article['내용']

        # Expander 헤더 텍스트 (한 줄 요약)
        expander_label = f"{icon} **{law_name}** | {article_num} | {title}"

        # Expander로 조문 상세 내용 표시
        with st.expander(expander_label, expanded=False):
            # 카드 스타일 컨테이너
            st.markdown(f"""
            <div style="
                background: {bg_gradient};
                padding: 3px;
                border-radius: 12px;
                margin-bottom: 15px;
            ">
                <div style="
                    background: white;
                    padding: 20px;
                    border-radius: 10px;
                ">
            """, unsafe_allow_html=True)

            # 법령 정보 (컬럼 레이아웃)
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"**📚 법령명**")
                st.markdown(f"<p style='font-size: 16px; color: #2d3748;'>{law_name}</p>", unsafe_allow_html=True)

            with col2:
                st.markdown(f"**📌 조문번호**")
                st.markdown(f"<p style='font-size: 16px; color: #2d3748;'>{article_num}</p>", unsafe_allow_html=True)

            with col3:
                st.markdown(f"**🏷️ 타입**")
                st.markdown(f"<p style='font-size: 14px; color: #718096;'>{law_type}</p>", unsafe_allow_html=True)

            st.markdown("---")

            # 조문 제목
            if title:
                st.markdown(f"**📋 제목**")
                st.markdown(f"<p style='font-size: 15px; color: #4a5568; font-weight: 500;'>{title}</p>", unsafe_allow_html=True)
                st.markdown("")

            # 조문 내용 (하이라이트 적용)
            if '내용' in article and article['내용']:
                st.markdown(f"**📄 내용**")

                # 내용 박스 스타일
                st.markdown(f"""
                <div style="
                    background-color: #f7fafc;
                    border-left: 4px solid {border_color};
                    padding: 15px;
                    border-radius: 8px;
                    white-space: pre-line;
                    line-height: 1.8;
                    color: #2d3748;
                    font-size: 14px;
                ">
                {result['matched_content']}
                </div>
                """, unsafe_allow_html=True)

            # 닫는 div 태그
            st.markdown("</div></div>", unsafe_allow_html=True)


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
        placeholder="예: 관세법 제10조, 손해배상, 계약",
        key="law_search_term",
        help="💡 조문번호 검색: '법령명 + 조문번호' (예: 관세법 제10조) | 키워드 검색: 일반 단어 입력"
    )
    
    # 검색 실행
    if search_term and selected_laws:
        with st.spinner("검색 중..."):
            results = search_laws(search_term, selected_laws, collected_laws)
            display_search_results(results)
    elif search_term and not selected_laws:
        st.warning("검색할 법령을 선택해주세요.")