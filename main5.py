import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
from utils_keyinput import HSDataManager, extract_hs_codes, clean_text, web_search_answer, classify_question
from utils_keyinput import handle_web_search, handle_hs_classification_cases, handle_hs_manual, handle_overseas_hs

# 환경 변수 로드 (.env 파일에서 기타 설정값 로드)
load_dotenv()

# Streamlit 페이지 설정
st.set_page_config(
    page_title="HS 품목분류 챗봇",  # 브라우저 탭 제목
    page_icon="📊",  # 브라우저 탭 아이콘
    layout="wide"  # 페이지 레이아웃을 넓게 설정
)

# 사용자 정의 CSS 스타일 추가
st.markdown("""
<style>
.main > div {
    display: flex;
    flex-direction: column;
    height: 85vh;  # 메인 컨테이너 높이 설정
}
.main > div > div:last-child {
    margin-top: auto;  # 마지막 요소를 하단에 고정
}
.element-container:has(button) {
    background-color: #f0f2f6;  # 버튼 컨테이너 배경색
    padding: 10px;
    border-radius: 10px;
}
.stTextArea textarea {
    border-radius: 20px;  # 입력창 모서리 둥글게
    padding: 10px 15px;
    font-size: 16px;
    min-height: 50px !important;  # 최소 높이
    max-height: 300px !important;  # 최대 높이
    height: auto !important;  # 자동 높이 조절
    resize: vertical !important;  # 수직 방향으로만 크기 조절 가능
    overflow-y: auto !important;  # 내용이 많을 때 스크롤 표시
}
</style>
""", unsafe_allow_html=True)

# HS 데이터 매니저 초기화 (캐싱을 통해 성능 최적화)
@st.cache_resource
def get_hs_manager():
    return HSDataManager()

# 세션 상태 초기화
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []  # 채팅 기록 저장

if 'context' not in st.session_state:
    # 초기 컨텍스트 설정 (카테고리 분류 안내 추가)
    st.session_state.context = """당신은 HS 품목분류 전문가로서 관세청에서 오랜 경력을 가진 전문가입니다. 사용자가 물어보는 품목에 대해 아래 네 가지 유형 중 하나로 질문을 분류하여 답변해주세요.

질문 유형:
1. 웹 검색(Web Search): 물품개요, 용도, 기술개발, 무역동향 등 일반 정보 탐색이 필요한 경우.
2. HS 분류 검색(HS Classification Search): HS 코드, 품목분류, 관세, 세율 등 HS 코드 관련 정보가 필요한 경우.
3. HS 해설서 분석(HS Manual Analysis): HS 해설서 본문 심층 분석이 필요한 경우.
4. 해외 HS 분류(Overseas HS Classification): 해외(미국/EU) HS 분류 사례가 필요한 경우.

중요 지침:
1. 사용자가 질문하는 물품에 대해 관련어, 유사품목, 대체품목도 함께 고려하여 가장 적합한 HS 코드를 찾아주세요.
2. 품목의 성분, 용도, 가공상태 등을 고려하여 상세히 설명해주세요.
3. 사용자가 특정 HS code를 언급하며 질문하는 경우, 답변에 해당 HS code 해설서 분석 내용을 포함하여 답변해주세요.
4. 관련 규정이나 판례가 있다면 함께 제시해주세요.
5. 답변은 간결하면서도 전문적으로 제공해주세요.

지금까지의 대화:
"""

# --- API 키 초기화 ---
if 'gemini_api_key' not in st.session_state:
    st.session_state.gemini_api_key = ""
    
if 'serper_api_key' not in st.session_state:
    st.session_state.serper_api_key = ""

def process_input():
    ui = st.session_state.user_input
    if not ui: 
        return

    st.session_state.chat_history.append({"role": "user", "content": ui})
    hs_manager = get_hs_manager()
    
    # 사용자 입력 API 키 전달
    user_gemini_api_key = st.session_state.gemini_api_key
    user_serper_api_key = st.session_state.serper_api_key
    
    # 임시로 환경 변수에 Serper API 키 설정 (web_search_answer 함수에서 사용)
    os.environ['SERPER_API_KEY'] = user_serper_api_key
    
    q_type = classify_question(ui, api_key=user_gemini_api_key)

    # 질문 유형별 분기
    if q_type == "web_search":
        answer = "\n\n +++ 웹검색 실시 +++\n\n" + handle_web_search(ui, st.session_state.context, hs_manager, api_key=user_gemini_api_key)
    elif q_type == "hs_classification":
        answer = "\n\n +++ HS 분류사례 검색 실시 +++ \n\n" + handle_hs_classification_cases(ui, st.session_state.context, hs_manager, api_key=user_gemini_api_key)
    elif q_type == "hs_manual":
        answer = "\n\n +++ HS 해설서 분석 실시 +++ \n\n" + handle_hs_manual(ui, st.session_state.context, hs_manager, api_key=user_gemini_api_key)
    elif q_type == "overseas_hs":
        answer = "\n\n +++ 해외 HS 분류 검색 실시 +++ \n\n" + handle_overseas_hs(ui, st.session_state.context, hs_manager, api_key=user_gemini_api_key)
    else:
        # 예외 처리: 기본 HS 분류
        answer = handle_hs_classification_cases(ui, st.session_state.context, hs_manager, api_key=user_gemini_api_key)

    st.session_state.chat_history.append({"role": "assistant", "content": answer})
    st.session_state.context += f"\n사용자: {ui}\n품목분류 전문가: {answer}\n"
    st.session_state.user_input = ""


# 사이드바 설정
with st.sidebar:
    st.title("HS Chatbot")
    
    # API Key 입력 섹션
    with st.expander("🔑 API Key 설정", expanded=True):
        # Google Gemini API Key 입력
        gemini_key_input = st.text_input(
            label="Google Gemini API Key 입력",
            type="password",
            placeholder="여기에 Gemini API Key를 입력하세요",
            value=st.session_state.gemini_api_key,
        )
        if gemini_key_input:
            st.session_state.gemini_api_key = gemini_key_input
            
        # Serper API Key 입력 추가
        serper_key_input = st.text_input(
            label="Serper API Key 입력",
            type="password",
            placeholder="여기에 Serper API Key를 입력하세요 (웹 검색용)",
            value=st.session_state.serper_api_key,
        )
        if serper_key_input:
            st.session_state.serper_api_key = serper_key_input
    
    # API Key 경고 메시지
    if not st.session_state.gemini_api_key:
        st.warning("챗봇을 이용하려면 Gemini API Key를 입력해주세요.")
        st.stop()
        
    if not st.session_state.serper_api_key:
        st.warning("웹 검색 기능을 이용하려면 Serper API Key를 입력해주세요.")
    
    # Gemini API 설정 (유저가 입력한 키 사용)
    genai.configure(api_key=st.session_state.gemini_api_key)
    
    st.markdown("""
    ### 이것은 HS Chatbot입니다.

    이 챗봇은 다음과 같은 방식으로 사용자의 질문에 답변합니다:

    - **웹 검색(Web Search)**: 물품개요, 용도, 뉴스, 무역동향, 산업동향 등 일반 정보 탐색이 필요한 경우 Serper API를 통해 최신 정보를 제공합니다.
    - **HS 분류 검색(HS Classification Search)**: 관세청의 품목분류 사례 약 1000개의 데이터베이스를 활용하여 HS 코드, 품목분류, 관세, 세율 등 정보를 제공합니다.
    - **HS 해설서 분석(HS Manual Analysis)**: HS 해설서 본문 심층 분석이 필요한 경우 관련 해설서와 규정을 바탄으로 답변합니다.
    - **해외 HS 분류(Overseas HS Classification)**: 미국 및 EU 관세청의 품목분류 사례를 활용하여 해외 HS 분류 정보를 제공합니다.

    사용자는 HS 코드, 품목 분류, 시장 동향, 규정 해설, 해외 분류 사례 등 다양한 질문을 할 수 있습니다.
    """)
    
    # 새로운 채팅 시작 버튼
    if st.button("새로운 채팅 시작하기", type="primary"):
        st.session_state.chat_history = []  # 채팅 기록 초기화
        st.session_state.context = """당신은 HS 품목분류 전문가로서 관세청에서 오랜 경력을 가진 전문가입니다. 사용자가 물어보는 품목에 대해 아래 네 가지 유형 중 하나로 질문을 분류하여 답변해주세요.

질문 유형:
1. 웹 검색(Web Search): 물품개요, 용도, 기술개발, 무역동향 등 일반 정보 탐색이 필요한 경우.
2. HS 분류 검색(HS Classification Search): HS 코드, 품목분류, 관세, 세율 등 HS 코드 관련 정보가 필요한 경우.
3. HS 해설서 분석(HS Manual Analysis): HS 해설서 본문문 심층 분석이 필요한 경우.
4. 해외 HS 분류(Overseas HS Classification): 해외(미국/EU) HS 분류 사례가 필요한 경우.

중요 지침:
1. 사용자가 질문하는 물품에 대해 관련어, 유사품목, 대체품목도 함께 고려하여 가장 적합한 HS 코드를 찾아주세요.
2. 품목의 성분, 용도, 가공상태 등을 고려하여 상세히 설명해주세요.
3. 사용자가 특정 HS code를 언급하며 질문하는 경우, 답변에 해당 HS code 해설서 분석 내용을 포함하여 답변해주세요.
4. 관련 규정이나 판례가 있다면 함께 제시해주세요.
5. 답변은 간결하면서도 전문적으로 제공해주세요.

지금까지의 대화:
"""
        st.rerun()  # 페이지 새로고침

# 메인 페이지 설정
st.title("HS 품목분류 챗봇")
st.write("HS 품목분류에 대해 질문해주세요!")

# 채팅 기록 표시
for message in st.session_state.chat_history:
    if message["role"] == "user":
        st.markdown(f"""<div style='background-color: #e6f7ff; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                   <strong>사용자:</strong> {message['content']}
                   </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""<div style='background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin-bottom: 10px;'>
                   <strong>품목분류 전문가:</strong> {message['content']}
                   </div>""", unsafe_allow_html=True)


# 하단 입력 영역 (Enter 키로만 전송)
input_container = st.container()
st.markdown("<div style='flex: 1;'></div>", unsafe_allow_html=True)

with input_container:
    # on_change 콜백으로 Enter 누를 때 process_input() 호출
    st.text_input(
        "품목에 대해 질문하세요:", 
        key="user_input", 
        on_change=process_input, 
        placeholder="여기에 입력 후 Enter"
    )