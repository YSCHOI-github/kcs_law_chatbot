import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import os
import asyncio
from utils import (
    LAW_CATEGORIES,
    load_law_data,
    classify_question_category,
    gather_agent_responses,
    get_head_agent_response
)
from law_article_search import render_law_search_ui

# --- 환경 변수 및 Gemini API 설정 ---
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)

# Streamlit 페이지 설정
st.set_page_config(
    page_title="법령 통합 챗봇",
    page_icon="📚",
    layout="wide"
)

# --- 세션 상태 초기화 ---
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'law_data' not in st.session_state:
    st.session_state.law_data = {}
if 'selected_category' not in st.session_state:
    st.session_state.selected_category = None
if 'last_used_category' not in st.session_state:
    st.session_state.last_used_category = None
# 임베딩 캐싱용 상태
if 'embedding_data' not in st.session_state:
    st.session_state.embedding_data = {}
# 재사용 가능한 asyncio 이벤트 루프
if 'event_loop' not in st.session_state:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    st.session_state.event_loop = loop

# --- UI: 카테고리 선택 ---
with st.expander("카테고리 선택 (선택사항)", expanded=True):
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
    with c1:
        if st.button("관세조사", use_container_width=True):
            st.session_state.selected_category = "관세조사"
            st.session_state.law_data = load_law_data("관세조사")
            st.session_state.last_used_category = "관세조사"
            st.rerun()
    with c2:
        if st.button("관세평가", use_container_width=True):
            st.session_state.selected_category = "관세평가"
            st.session_state.law_data = load_law_data("관세평가")
            st.session_state.last_used_category = "관세평가"
            st.rerun()
    with c3:
        if st.button("자유무역협정", use_container_width=True):
            st.session_state.selected_category = "자유무역협정"
            st.session_state.law_data = load_law_data("자유무역협정")
            st.session_state.last_used_category = "자유무역협정"
            st.rerun()
    with c4:
        if st.button("외국환거래", use_container_width=True):
            st.session_state.selected_category = "외국환거래"
            st.session_state.law_data = load_law_data("외국환거래")
            st.session_state.last_used_category = "외국환거래"
            st.rerun()
    with c5:
        if st.button("대외무역거래", use_container_width=True):
            st.session_state.selected_category = "대외무역거래"
            st.session_state.law_data = load_law_data("대외무역거래")
            st.session_state.last_used_category = "대외무역거래"
            st.rerun()
    with c6:
        if st.button("환급", use_container_width=True):
            st.session_state.selected_category = "환급"
            st.session_state.law_data = load_law_data("환급")
            st.session_state.last_used_category = "환급"
            st.rerun()
    with c7:
        if st.button("AI 자동 분류", use_container_width=True):
            st.session_state.selected_category = "auto_classify"
            st.session_state.last_used_category = "auto_classify"
            st.rerun()

# 선택된 카테고리 상태 표시
if st.session_state.selected_category:
    if st.session_state.selected_category == "auto_classify":
        st.info("AI가 질문을 분석하여 자동으로 관련 카테고리를 선택합니다.")
    else:
        st.info(f"선택된 카테고리: {st.session_state.selected_category}")
else:
    st.info("카테고리를 선택하거나 AI 자동 분류를 이용해주세요.")

# --- UI: 메인 (탭으로 기능 분리) ---
tab1, tab2 = st.tabs(["💬 AI 법률 챗봇", "🔍 법령 원문 검색"])

# 챗봇 탭
with tab1:
    # 대화 기록 렌더링
    for msg in st.session_state.chat_history:
        with st.chat_message(msg['role']):
            st.markdown(msg['content'])

    # 사용자 입력 및 응답 처리
    if user_input := st.chat_input("질문을 입력하세요"):
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                # 자동 분류 모드이거나 카테고리 선택이 안된 경우
                if st.session_state.get('selected_category') == "auto_classify" or not st.session_state.get('selected_category'):
                    category = classify_question_category(user_input)
                    st.session_state.law_data = load_law_data(category)
                    st.write(f"🔍 AI 분석 결과: '{category}' 카테고리와 관련된 질문으로 판단되어 해당 법령을 참조합니다.")

                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history])
                
                # 1. 각 법령 에이전트로부터 답변 수집
                responses = st.session_state.event_loop.run_until_complete(
                    gather_agent_responses(user_input, history)
                )

                # 2. 헤드 에이전트가 답변 통합 및 최종 답변 생성
                answer = get_head_agent_response(responses, user_input, history)
                
                # 3. 최종 답변 출력
                st.markdown(answer)
                st.session_state.chat_history.append({"role": "assistant", "content": answer})

                # 4. 각 에이전트의 개별 답변을 expander로 제공
                with st.expander("🤖 각 AI 에이전트 답변 보기"):
                    if responses:
                        for law_name, response_text in responses:
                            st.markdown(f"**📚 {law_name}**")
                            st.markdown(response_text)
                            st.markdown("---")

# 법령 검색 탭
with tab2:
    # law_article_search.py에서 만든 UI 렌더링 함수 호출
    # st.session_state.law_data를 인자로 전달합니다.
    render_law_search_ui(st.session_state.law_data)

# 사이드바 안내
with st.sidebar:
    st.markdown("""
### ℹ️ 사용 안내

다음 법령들을 기반으로 답변을 제공합니다:

**관세조사 관련:**
- 관세법, 시행령, 시행규칙
- 관세평가 운영에 관한 고시
- 관세조사 운영에 관한 훈령
                
**관세평가 관련:**
- 관세와무역에관한일반협정제7조, 
- WTO관세평가협정, TCCV기술문서, 권고의견, 사례연구, 연구, 해설
- WCO Customs Valuation Archer

**자유무역협정 관련:**
- 원산지조사 운영에 관한 훈령
- 자유무역협정 원산지인증수출자 운영에 관한 고시
- 자유무역협정의 이행을 위한 관세법의 특례에 관한 법률, 시행령, 시행규칙, 사무처리에 관한 고시

**외국환거래 관련:**
- 외국환거래법, 시행령, 규정
                
**대외무역거래 관련:**
- 대외무역법, 시행령, 관리규정
- 원산지표시제도 운영에 관한 고시
                
**환급 관련:**
- 수출용 원재료에 대한 관세 등 환급에 관한 특례법, 시행령, 시행규칙
- 수입물품에 대한 개별소비세와 주세 등의 환급에 관한 고시
- 대체수출물품 관세환급에 따른 수출입통관절차 및 환급처리에 관한 예규
- 수입원재료에 대한 환급방법 조정에 관한 고시
- 수출용 원재료에 대한 관세 등 환급사무에 관한 훈령
- 수출용 원재료에 대한 관세 등 환급사무처리에 관한 고시
- 위탁가공 수출물품에 대한 관세 등 환급처리에 관한 예규
""")
    
    if st.button("새 채팅 시작", type="primary"):
        st.session_state.chat_history = []
        st.rerun()