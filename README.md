# 법령 통합 챗봇

관세법, 자유무역협정, 외국환거래 관련 법령을 기반으로 사용자의 질문에 답변하는 AI 챗봇입니다. Streamlit을 사용한 웹 인터페이스와 Google Gemini AI API를 활용하여 법령 내용을 자동 분석하고, 사용자 질문에 근거와 법조항 출처를 명확히 제시하는 답변을 제공합니다.

## 주요 기능

- **법령 기반 답변**: 관세법, 자유무역협정, 외국환거래법 등 다양한 법령 문서를 자동 로드
- **Multi Agents + Head Agents**: 각 법령별 agent가 ai 답변 생성, Head agent가 답변들을 취합하여 최종 답변 생성 
- **법령 조항 인용**: 답변에 관련 법령 조항 번호와 원문 출처를 명시
- **PDF 텍스트 추출 및 임베딩**: `pdf_utils.extract_text_from_pdf`로 텍스트 추출 후 TF-IDF 임베딩 생성
- **유사도 검색**: 청크 단위 TF-IDF 및 코사인 유사도 기반 유사 법령 구간 검색
- **병렬 처리 및 비동기 응답**: `asyncio.to_thread`(또는 ThreadPoolExecutor)로 여러 법령 카테고리 동시 질의 처리
- **대화 기록 저장**: `st.session_state`를 활용해 사용자와의 채팅 이력 관리
- **직관적 UI/UX**: expander, spinner, 버튼, selectbox 등을 활용한 사용자 친화적 인터페이스
- **결과 검증 경고**: 누락된 PDF 파일이나 API 오류 시 명확한 경고 메시지 표시

## 설치 방법

1. 리포지토리 클론 및 이동
   ```bash
   git clone https://github.com/YSCHOI-github/kcs_law_chatbot.git
   cd kcs_law_chatbot
   ```

2. 가상환경 생성 및 활성화
   ```bash
   python -m venv venv
   source venv/bin/activate   # macOS/Linux
   venv\Scripts\activate    # Windows
   ```

3. 의존성 설치
   ```bash
   pip install -r requirements.txt
   ```

4. 환경 변수 설정
   - 프로젝트 루트에 `.env` 파일 생성
   - 다음 내용 추가:
     ```ini
     GOOGLE_API_KEY=your_google_api_key_here
     ```

5. 법령 PDF 파일 준비
   - `laws/` 폴더 생성 후 PDF 파일 저장
   - `main.py`의 `LAW_CATEGORIES` 경로와 일치시킬 것

## 실행 방법

```bash
streamlit run main.py
```

실행 후 제공되는 로컬 URL(기본: http://localhost:8501)에서 웹 챗봇 사용 가능

## 사용 방법

1. 브라우저에서 `http://localhost:8501`에 접속
2. **카테고리 선택**: 관세법, 자유무역협정, 외국환거래법 중 선택하거나 자동 분석 모드
3. 질문 입력창에 법령 관련 질문 입력 후 전송
4. AI가 법령 근거와 조항을 포함한 단계별 답변 제공

## 법령 카테고리 및 파일 경로

- **관세법**:
  - 관세법 (`laws/관세법.pdf`)
  - 관세법 시행령 (`laws/관세법 시행령.pdf`)
  - 관세법 시행규칙 (`laws/관세법 시행규칙.pdf`)
  - 관세평가 운영에 관한 고시 (`laws/관세평가 운영에 관한 고시.pdf`)
  - 관세조사 운영에 관한 훈령 (`laws/관세조사 운영에 관한 훈령.pdf`)

- **관세평가**:
  - WTO관세평가협정 (`laws/WTO관세평가협정_영문판.pdf`)
  - TCCV기술문서_영문판 (`laws/TCCV기술문서_영문판.pdf`)
  - 관세와무역에관한일반협정제7조 (`laws/관세와무역에관한일반협정제7조_영문판.pdf`)
  - 권고의견 (`laws/권고의견_영문판.pdf`)
  - 사례연구_영문판 (`laws/사례연구_영문판.pdf`)
  - 연구_영문판 (`laws/연구_영문판.pdf`)
  - 해설_영문판 (`laws/해설_영문판.pdf`)
  - WCO Customs_Valuation_Archer (`laws/customs_valuation_archer.pdf`)

- **자유무역협정**:
  - 원산지조사 운영에 관한 훈령 (`laws/원산지조사 운영에 관한 훈령.pdf`)
  - 자유무역협정 원산지인증수출자 운영에 관한 고시 (`laws/자유무역협정 원산지인증수출자 운영에 관한 고시.pdf`)
  - 특례법 (`laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률.pdf`)
  - 특례법 시행령 (`laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 시행령.pdf`)
  - 특례법 시행규칙 (`laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 시행규칙.pdf`)
  - 특례법 사무처리 고시 (`laws/자유무역협정의 이행을 위한 관세법의 특례에 관한 법률 사무처리에 관한 고시.pdf`)

- **외국환거래**:
  - 외국환거래법 (`laws/외국환거래법.pdf`)
  - 외국환거래법 시행령 (`laws/외국환거래법 시행령.pdf`)
  - 외국환거래규정 (`laws/외국환거래규정.pdf`)

## 참고 사항

- PDF 파일이 누락되면 실행 시 경고 메시지가 표시됩니다.
- 명확하고 구체적인 질문이 더 정확한 답변을 이끌어냅니다.
- 법령 문서는 주기적으로 갱신하여 최신 내용을 유지하세요.

## 파일 구조 (예시)

```
law-chatbot/
├─ main.py                # Streamlit 메인 스크립트
├─ pdf_utils.py          # PDF 텍스트 추출 유틸리티
├─ requirements.txt      # 의존성 목록
├─ .env                  # 환경 변수 파일 (API 키)
├─ venv                  # 가상 환경
├─ laws/                 # 법령 PDF 파일 디렉토리
│  ├─ 관세법.pdf
│  └─ ...
└─ README.md             # 프로젝트 설명
```
