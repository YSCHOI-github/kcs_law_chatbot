# 법령 통합 챗봇 - ./laws 폴더에서 사전 다운로드된 패키지 로드
import streamlit as st
from google import genai
import os
import json
import asyncio
import concurrent.futures
from pathlib import Path
import glob

# 분리된 핵심 로직 함수들을 utils.py에서 가져옵니다.
from utils import (
    process_json_data,
    analyze_query,
    get_agent_response,
    get_head_agent_response
)
from law_article_search import render_law_search_ui

# --- 환경 변수 및 Gemini API 설정 ---
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
client = genai.Client(api_key=GOOGLE_API_KEY)

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
if 'embedding_data' not in st.session_state:
    st.session_state.embedding_data = {}
if 'event_loop' not in st.session_state:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    st.session_state.event_loop = loop
if 'collected_laws' not in st.session_state:
    st.session_state.collected_laws = {}
if 'search_weights' not in st.session_state:
    st.session_state.search_weights = {'content': 1.0, 'title': 0.0}
if 'packages_loaded' not in st.session_state:
    st.session_state.packages_loaded = False
if 'selected_packages' not in st.session_state:
    st.session_state.selected_packages = []
if 'package_cache' not in st.session_state:
    st.session_state.package_cache = {}
if 'current_selected_packages' not in st.session_state:
    st.session_state.current_selected_packages = []
if 'uploaded_laws' not in st.session_state:
    st.session_state.uploaded_laws = {}
if 'show_upload_ui' not in st.session_state:
    st.session_state.show_upload_ui = False

# --- 함수 정의 ---
def get_available_packages():
    """사용 가능한 패키지 목록 조회"""
    laws_dir = Path("./laws")
    if not laws_dir.exists():
        return {}
    
    json_files = list(laws_dir.glob("*.json"))
    package_names = {
        "customs_investigation": "관세조사",
        "foreign_exchange_investigation": "외환조사", 
        "foreign_trade": "대외무역",
        "free_trade_agreement": "자유무역협정",
        "refund": "환급"
    }
    
    available_packages = {}
    for json_file in json_files:
        package_id = json_file.stem
        package_name = package_names.get(package_id, package_id)
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
            
            law_count = len(package_data)
            article_count = sum(len(law_info['data']) for law_info in package_data.values())
            
            available_packages[package_id] = {
                'name': package_name,
                'law_count': law_count,
                'article_count': article_count,
                'laws': list(package_data.keys())
            }
        except Exception as e:
            st.error(f"❌ {package_name} 패키지 정보 읽기 실패: {str(e)}")
    
    return available_packages

def load_selected_packages(selected_package_ids, auto_process=False):
    """선택된 패키지들만 로드 (캐시 지원) - 이전 패키지는 캐시에만 저장"""
    if not selected_package_ids:
        st.warning("선택된 패키지가 없습니다.")
        return

    laws_dir = Path("./laws")
    package_names = {
        "customs_investigation": "관세조사",
        "foreign_exchange_investigation": "외환조사",
        "foreign_trade": "대외무역",
        "free_trade_agreement": "자유무역협정",
        "refund": "환급",
        "user_upload": "사용자 업로드"
    }
    
    # 현재 로드된 데이터를 캐시에 저장 (이전 선택이 있었다면)
    # user_upload 제외한 패키지만 캐시 저장
    if st.session_state.selected_packages and st.session_state.collected_laws:
        previous_cache_packages = [pid for pid in st.session_state.selected_packages if pid != 'user_upload']
        if previous_cache_packages:
            previous_cache_key = "_".join(sorted(previous_cache_packages))
            st.session_state.package_cache[previous_cache_key] = {
                'collected_laws': st.session_state.collected_laws.copy(),
                'law_data': st.session_state.law_data.copy(),
                'embedding_data': st.session_state.embedding_data.copy()
            }
    
    # 기존 데이터 초기화 (새로 선택된 패키지만 사용)
    st.session_state.collected_laws = {}
    st.session_state.law_data = {}
    st.session_state.embedding_data = {}

    # 캐시 키 생성 (user_upload 제외)
    cache_packages = [pid for pid in selected_package_ids if pid != 'user_upload']
    cache_key = "_".join(sorted(cache_packages)) if cache_packages else None

    # 캐시에서 로드 시도 (cache_key가 있는 경우만)
    if cache_key and cache_key in st.session_state.package_cache:
        if not auto_process:
            with st.spinner("캐시에서 법령 패키지를 로드하는 중..."):
                st.session_state.collected_laws = st.session_state.package_cache[cache_key]['collected_laws'].copy()
                st.session_state.law_data = st.session_state.package_cache[cache_key]['law_data'].copy()
                st.session_state.embedding_data = st.session_state.package_cache[cache_key]['embedding_data'].copy()
                st.session_state.packages_loaded = True
                st.session_state.selected_packages = selected_package_ids

                total_laws = len(st.session_state.collected_laws)
                total_articles = sum(len(law_info['data']) for law_info in st.session_state.collected_laws.values())
                st.success(f"🚀 캐시에서 로드 완료: {total_laws}개 법령, {total_articles}개 조문")
        else:
            # 자동 처리 시에는 메시지 없이 로드
            st.session_state.collected_laws = st.session_state.package_cache[cache_key]['collected_laws'].copy()
            st.session_state.law_data = st.session_state.package_cache[cache_key]['law_data'].copy()
            st.session_state.embedding_data = st.session_state.package_cache[cache_key]['embedding_data'].copy()
            st.session_state.packages_loaded = True
            st.session_state.selected_packages = selected_package_ids

        # user_upload가 있으면 추가로 로드
        if 'user_upload' in selected_package_ids:
            if st.session_state.uploaded_laws:
                for law_name, law_info in st.session_state.uploaded_laws.items():
                    st.session_state.collected_laws[law_name] = {
                        'type': law_info['type'],
                        'data': law_info['data'],
                        'package': '사용자 업로드'
                    }
                # 추가된 법령 처리 (TF-IDF 벡터화)
                process_all_loaded_laws(silent=True)

        return
    
    # 캐시에 없으면 파일에서 로드
    if not auto_process:
        loading_msg = "선택된 법령 패키지를 로드하는 중..."
    else:
        loading_msg = "선택된 법령 패키지를 자동 로드하는 중..."
        
    with st.spinner(loading_msg):
        total_laws = 0
        total_articles = 0

        for package_id in selected_package_ids:
            package_name = package_names.get(package_id, package_id)

            # "사용자 업로드" 패키지 처리
            if package_id == "user_upload":
                if not st.session_state.uploaded_laws:
                    if not auto_process:
                        st.warning("업로드된 법령이 없습니다.")
                    continue

                # uploaded_laws를 collected_laws로 복사
                for law_name, law_info in st.session_state.uploaded_laws.items():
                    st.session_state.collected_laws[law_name] = {
                        'type': law_info['type'],
                        'data': law_info['data'],
                        'package': package_name
                    }
                    total_laws += 1
                    total_articles += len(law_info['data'])

                if not auto_process:
                    st.success(f"✅ {package_name} 패키지 로드 완료")
                continue

            # 기존 JSON 파일 기반 패키지 로드
            json_file = laws_dir / f"{package_id}.json"

            if not json_file.exists():
                st.error(f"❌ {package_name} 패키지 파일이 없습니다: {json_file}")
                continue

            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)

                # 패키지 내 각 법령을 세션에 추가
                for law_name, law_info in package_data.items():
                    # 타입에 따른 분류
                    if law_info['type'] == 'law':
                        type_name = '법률 API'
                    elif law_info['type'] == 'admin':
                        type_name = '행정규칙 API'
                    elif law_info['type'] == 'three_stage':
                        type_name = '3단비교 API'
                    else:
                        type_name = '기타 API'

                    st.session_state.collected_laws[law_name] = {
                        'type': type_name,
                        'data': law_info['data'],
                        'package': package_name
                    }
                    total_laws += 1
                    total_articles += len(law_info['data'])

                if not auto_process:
                    st.success(f"✅ {package_name} 패키지 로드 완료")

            except Exception as e:
                st.error(f"❌ {package_name} 패키지 로드 실패: {str(e)}")
        
        st.session_state.packages_loaded = True
        st.session_state.selected_packages = selected_package_ids
        
        if auto_process:
            # 자동 처리인 경우 바로 데이터 변환까지 수행
            process_all_loaded_laws(silent=True)

            # 캐시에 저장 (cache_key가 있는 경우만 - user_upload 단독 선택 시 제외)
            if cache_key:
                st.session_state.package_cache[cache_key] = {
                    'collected_laws': st.session_state.collected_laws.copy(),
                    'law_data': st.session_state.law_data.copy(),
                    'embedding_data': st.session_state.embedding_data.copy()
                }
        else:
            st.success(f"🎉 선택된 패키지 로드 완료: {total_laws}개 법령, {total_articles}개 조문")

def process_all_loaded_laws(silent=False):
    """로드된 모든 법령 데이터를 처리"""
    if not st.session_state.collected_laws:
        if not silent:
            st.warning("로드된 법령 데이터가 없습니다.")
        return
    
    if not silent:
        spinner_msg = "법령 데이터를 처리하고 있습니다..."
    else:
        spinner_msg = "법령 데이터를 자동 처리하고 있습니다..."
        
    with st.spinner(spinner_msg):
        st.session_state.law_data = {}
        st.session_state.embedding_data = {}
        
        for name, law_info in st.session_state.collected_laws.items():
            json_data = law_info['data']
            result = process_json_data(name, json_data)
            processed_name, vec, title_vec, mat, title_mat, chunks, chunk_count = result
            
            if vec is not None:
                st.session_state.law_data[processed_name] = "processed"
                st.session_state.embedding_data[processed_name] = (vec, title_vec, mat, title_mat, chunks)
                if not silent:
                    st.success(f"✅ {processed_name} 처리 완료 ({chunk_count}개 조항)")
            else:
                if not silent:
                    st.error(f"❌ {processed_name} 처리 실패")
        
        if not silent:
            st.success("모든 법령 데이터 처리가 완료되었습니다!")

def start_new_chat():
    """새 대화를 시작하는 함수"""
    st.session_state.chat_history = []
    st.success("새 대화가 시작되었습니다!")
    st.rerun()

# --- UI: 메인 ---
st.title("📚 법령 통합 챗봇")

# 메인 화면 상단에 패키지 선택 박스 (간단하게, main_ref.py 스타일)
available_packages = get_available_packages()

if available_packages:
    st.markdown("---")

    # 패키지 선택 박스들을 횡으로 나열 (라디오 버튼으로 단일 선택)
    # "사용자 업로드" 버튼 추가를 위해 +2
    cols = st.columns(len(available_packages) + 2)
    
    # 선택 옵션 생성 (선택 안함 포함)
    package_options = ["선택 안함"] + [f"📂 {info['name']}" for info in available_packages.values()]
    package_ids = [None] + list(available_packages.keys())
    
    # 현재 선택된 패키지의 인덱스 찾기
    current_index = 0
    if st.session_state.current_selected_packages:
        for i, pkg_id in enumerate(package_ids[1:], 1):
            if pkg_id in st.session_state.current_selected_packages:
                current_index = i
                break
    
    # 라디오 버튼으로 단일 선택
    with cols[0]:
        if st.button("🚫 선택 안함", type="secondary" if current_index != 0 else "primary"):
            current_selection = []
            st.session_state.current_selected_packages = []
            st.session_state.packages_loaded = False
            st.session_state.selected_packages = []
            st.session_state.collected_laws = {}
            st.session_state.law_data = {}
            st.session_state.embedding_data = {}
            st.rerun()
    
    current_selection = []
    for i, (package_id, package_info) in enumerate(available_packages.items(), 1):
        with cols[i]:
            is_selected = package_id in st.session_state.current_selected_packages
            button_type = "primary" if is_selected else "secondary"

            if st.button(f"📂 {package_info['name']}", type=button_type):
                current_selection = [package_id]
                st.session_state.show_upload_ui = False

    # "사용자 업로드" 버튼 추가 (마지막 컬럼)
    with cols[len(available_packages) + 1]:
        is_upload_selected = 'user_upload' in st.session_state.current_selected_packages
        button_type = "primary" if is_upload_selected else "secondary"

        if st.button("📤 사용자 업로드", type=button_type):
            current_selection = ['user_upload']
            st.session_state.show_upload_ui = True

    # 버튼 클릭으로 선택이 변경된 경우 처리
    if current_selection and set(current_selection) != set(st.session_state.current_selected_packages):
        st.session_state.current_selected_packages = current_selection

        # "사용자 업로드"가 아닌 경우에만 자동 로드
        if 'user_upload' not in current_selection:
            # 선택된 패키지가 있으면 자동으로 로드하고 처리 (캐시 포함)
            # auto_process=True로 설정하여 챗봇용 데이터로 완전히 변환까지 수행
            load_selected_packages(current_selection, auto_process=True)

        st.rerun()

# 사이드바 (항상 표시)
with st.sidebar:
    # 조건부: 사용자 업로드 UI 표시
    if st.session_state.show_upload_ui:
        st.header("📤 법령 파일 업로드")

        # 파일 업로더 (PDF/TXT, 다중 선택)
        uploaded_files = st.file_uploader(
            "법령 파일 선택 (PDF/TXT)",
            type=['pdf', 'txt'],
            accept_multiple_files=True,
            help="최대 200MB까지 업로드 가능 (Streamlit 기본 제한)"
        )

        # 업로드 버튼
        if st.button("📥 업로드 및 처리", use_container_width=True):
            if uploaded_files:
                from utils import process_uploaded_files

                with st.spinner("파일 처리 중..."):
                    # 파일 처리 (JSON 변환)
                    new_laws = process_uploaded_files(uploaded_files)

                    # 세션 스테이트에 저장
                    st.session_state.uploaded_laws.update(new_laws)

                    # 자동으로 패키지 로드 및 처리
                    if new_laws:
                        load_selected_packages(['user_upload'], auto_process=True)
                        st.success(f"{len(new_laws)}개 법령 업로드 완료!")
                        st.rerun()
            else:
                st.warning("업로드할 파일을 선택해주세요.")

        # 업로드된 법령 목록 표시
        if st.session_state.uploaded_laws:
            st.markdown("---")
            st.subheader("업로드된 법령")

            for law_name in list(st.session_state.uploaded_laws.keys()):
                cols = st.columns([3, 1, 1])
                article_count = len(st.session_state.uploaded_laws[law_name]['data'])
                cols[0].write(f"📄 {law_name} ({article_count}개 조문)")

                # JSON 다운로드 버튼
                law_data = st.session_state.uploaded_laws[law_name]['data']
                json_str = json.dumps(law_data, ensure_ascii=False, indent=2)

                cols[1].download_button(
                    label="📥",
                    data=json_str,
                    file_name=f"{law_name}.json",
                    mime="application/json",
                    key=f"download_{law_name}",
                    help="JSON 다운로드"
                )

                # 삭제 버튼
                if cols[2].button("🗑️", key=f"del_{law_name}", help="삭제"):
                    # 해당 법령 삭제
                    del st.session_state.uploaded_laws[law_name]

                    # collected_laws에서도 삭제 (있는 경우)
                    if law_name in st.session_state.collected_laws:
                        del st.session_state.collected_laws[law_name]

                    # embedding_data에서도 삭제 (있는 경우)
                    if law_name in st.session_state.embedding_data:
                        del st.session_state.embedding_data[law_name]

                    # law_data에서도 삭제 (있는 경우)
                    if law_name in st.session_state.law_data:
                        del st.session_state.law_data[law_name]

                    st.success(f"{law_name} 삭제 완료")
                    st.rerun()

        st.markdown("---")

    # 기존 "법령 패키지 정보" 섹션 (조건부 expanded 설정)
    st.header("📦 법령 패키지 정보")

    # 패키지 상세 설명 (고정 내용)
    # show_upload_ui가 True면 닫힘, False면 열림
    with st.expander("📖 패키지 상세 설명", expanded=not st.session_state.show_upload_ui):
        st.markdown("""
        **🏛️ 관세조사 패키지**
        - 관세법, 관세법 시행령, 관세법 시행규칙
        - 관세평가 운영에 관한 고시, 관세조사 운영에 관한 훈령
        
        **💱 외환조사 패키지**
        - 외국환거래법, 외국환거래법 시행령
        - 외국환거래규정
        
        **🌍 대외무역 패키지**
        - 대외무역법, 대외무역법 시행령
        - 대외무역관리규정
        
        **🤝 자유무역협정 패키지**
        - 자유무역협정 이행을 위한 관세법의 특례에 관한 법률, 시행령, 시행규칙
        - 사무처리 고시, 원산지 조사 운영 훈령, 원산지인증수출자 운영 고시
        
        **💰 환급 패키지**
        - 수출용 원재료에 대한 관세 등 환급에 관한 특례법, 시행령, 시행규칙
        - 환급사무처리 고시, 위탁가공 환급처리 예규, 환급사무 훈령 등
        """)
    
    st.markdown("---")

# 패키지가 로드되지 않은 경우 안내 메시지
if not st.session_state.packages_loaded:
    if not available_packages:
        st.error("📁 ./laws 폴더에 패키지가 없습니다.")
        st.info("💡 download_packages.py를 먼저 실행하여 법령 패키지를 다운로드하세요.")
        st.code("python download_packages.py", language="bash")
        st.stop()
    
    st.info("💡 위에서 사용할 법령 패키지를 선택하면 자동으로 로드됩니다.")

else:
    # 패키지가 로드된 경우 사이드바에 추가 정보 표시
    with st.sidebar:
        st.header("📊 로드된 데이터 현황")
        
        # 로드된 패키지 정보 표시
        if st.session_state.collected_laws:
            # 패키지별 그룹화
            packages = {}
            for law_name, law_info in st.session_state.collected_laws.items():
                package = law_info.get('package', '기타')
                if package not in packages:
                    packages[package] = []
                packages[package].append((law_name, len(law_info['data'])))
            
            # 현재 로드된 패키지 정보 표시
            with st.expander("📋 현재 로드된 법령", expanded=True):
                for package_name, laws in packages.items():
                    st.subheader(f"📂 {package_name}")
                    total_articles = sum(article_count for _, article_count in laws)
                    st.caption(f"{len(laws)}개 법령, {total_articles}개 조문")
                    
                    for law_name, article_count in laws:
                        st.markdown(f"• **{law_name}** ({article_count}개 조문)")
        
        st.markdown("---")
        
        # 데이터 처리 상태 표시
        if st.session_state.law_data:
            st.success("✅ 챗봇 사용 준비 완료")
            st.info(f"현재 {len(st.session_state.law_data)}개 법령 사용 가능")
        
        st.markdown("---")
        st.header("💬 대화 관리")
        if st.button("🔄 새 대화 시작", use_container_width=True):
            start_new_chat()
        
        if st.session_state.chat_history:
            st.info(f"현재 대화 수: {len([msg for msg in st.session_state.chat_history if msg['role'] == 'user'])}개")

    # 검색 설정 패널 (패키지 로드된 경우에만 표시)
    if st.session_state.packages_loaded:
        with st.expander("⚙️ 검색 설정", expanded=True):
            search_mode = st.radio(
                "🔍 답변 참고 조문 검색 모드 선택",
                options=["📄 내용 전용 모드(일반적인 경우)", "🤝 조문 제목+내용 균형 모드(각 조문 제목이 상세한 법령 검색에 적합)"],
                index=0 if st.session_state.search_weights['title'] == 0.0 else 1,
                help="균형 모드: 제목과 내용을 50:50으로 검색 | 내용 전용: 제목을 무시하고 내용만 검색"
            )
            
            # 선택에 따라 가중치 설정
            if "내용 전용 모드" in search_mode:
                title_weight = 0.0
                content_weight = 1.0
            elif "균형 모드" in search_mode:
                title_weight = 0.5
                content_weight = 0.5
            else:
                title_weight = 0.0
                content_weight = 1.0
            
            # 세션 상태 업데이트
            if st.session_state.search_weights['title'] != title_weight:
                st.session_state.search_weights = {
                    'content': content_weight,
                    'title': title_weight
                }
                st.success(f"검색 모드가 변경되었습니다: {search_mode}")
        
        st.markdown("---")
        
        # 탭으로 챗봇과 검색 기능 분리
        tab1, tab2 = st.tabs(["💬 AI 챗봇", "🔍 법령 검색"])

        with tab1:
            if st.session_state.law_data:
                st.info(f"현재 {len(st.session_state.law_data)}개의 법령이 처리되어 사용 가능합니다: {', '.join(st.session_state.law_data.keys())}")
            
            # 채팅 컨테이너
            chat_container = st.container()
            
            with chat_container:
                # 대화 히스토리 표시
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg['role']):
                        st.markdown(msg['content'])

            # 질문 입력창
            if user_input := st.chat_input("질문을 입력하세요"):
                if not st.session_state.law_data:
                    st.warning("먼저 사이드바에서 법령 패키지를 로드하고 처리해주세요.")
                    st.stop()
                
                # 사용자 메시지를 히스토리에 추가하고 즉시 표시
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                
                # 채팅 컨테이너 내에서 새 메시지들을 렌더링
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(user_input)
                    
                    # 챗봇 답변 생성 로직
                    with st.chat_message("assistant"):
                        full_answer = ""

                        try:
                            with st.status("답변 생성 중...", expanded=True) as status:
                                history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.chat_history])
                                search_weights = st.session_state.search_weights

                                # 1. 질문 분석
                                status.update(label="1/3: 질문 분석 중...", state="running")
                                original_query, similar_queries, expanded_keywords = analyze_query(user_input, st.session_state.collected_laws, search_weights)

                                with st.expander("🔍 쿼리 분석 결과", expanded=False):
                                    st.markdown(f"**원본 질문:** {original_query}")
                                    st.markdown("**유사 질문:**")
                                    st.markdown('\n'.join([f'- {q}' for q in similar_queries]))
                                    st.markdown(f"**확장 키워드:** {expanded_keywords}")

                                # 2. 법령별 답변 생성
                                status.update(label="2/3: 법령별 답변 생성 중...", state="running")
                                status.update(label="✅ 질문 분석 완료", state="complete", expanded=False)

                            # 각 AI 답변을 status 위젯에 실시간 표시
                            agent_status = st.status("📚 각 법령별 상세 답변 생성 중...", expanded=True)

                            law_names = list(st.session_state.law_data.keys())

                            # 각 법령별로 플레이스홀더 생성 (실시간 업데이트용)
                            placeholders = {}
                            with agent_status:
                                for law_name in law_names:
                                    placeholders[law_name] = st.empty()

                            # ThreadPoolExecutor로 병렬 처리 (최대 5개)
                            with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(law_names), 5)) as executor:
                                futures = {
                                    executor.submit(
                                        get_agent_response,
                                        law_name, user_input, history, st.session_state.embedding_data, expanded_keywords, search_weights
                                    ): law_name for law_name in law_names
                                }

                                agent_responses = []
                                for future in concurrent.futures.as_completed(futures):
                                    law_name, response = future.result()
                                    agent_responses.append((law_name, response))

                                    # 완료되는 순서대로 즉시 해당 플레이스홀더에 출력
                                    with placeholders[law_name].container():
                                        st.markdown(f"**📚 {law_name}**")
                                        st.markdown(response)
                                        st.markdown("---")

                            # 모든 답변 수집 완료 후 status 닫기
                            agent_status.update(label="✅ 각 법령별 상세 답변 생성 완료", state="complete", expanded=False)

                            # 최종 답변 표시
                            st.markdown("---")
                            st.markdown("## 🎯 최종 통합 답변")

                            # 답변 생성
                            with st.spinner("최종 통합 답변 생성 중..."):
                                full_answer = get_head_agent_response(agent_responses, user_input, history)

                            # 답변 표시
                            st.markdown(full_answer)

                            # 세션 히스토리에 저장
                            if full_answer:
                                st.session_state.chat_history.append({"role": "assistant", "content": full_answer})

                        except Exception as e:
                            error_msg = f"답변 생성 중 오류가 발생했습니다: {str(e)}"
                            st.error(error_msg)
                            st.session_state.chat_history.append({"role": "assistant", "content": error_msg})
        
        with tab2:
            render_law_search_ui(st.session_state.collected_laws)

# 초기 설정은 사용자 선택에 맡김