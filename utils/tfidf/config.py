"""TF-IDF 벡터화 설정

이 파일은 TF-IDF 관련 모든 설정을 중앙 관리합니다.
TF-IDF 파라미터 변경 시 이 파일만 수정하면 됩니다.
"""

# 법령 전용 불용어 정의
LEGAL_STOPWORDS = [
    # 기본 불용어
    '것', '등', '때', '경우', '바', '수', '점', '면', '이', '그', '저', '은', '는', '을', '를', '에', '으로', '의',
    '따라', '또는', '및', '있다', '한다', '되어', '인한', '대한', '관한', '위한', '통한', '같은', '다른',

    # 법령 구조 불용어
    '조항', '규정', '법률', '법령', '조문', '항목', '세부', '내용', '사항', '요건', '기준', '방법', '절차',

    # 일반적인 동사/형용사
    '해당', '관련', '포함', '제외', '적용', '시행', '준용', '의하다', '하다', '되다', '있다', '없다', '같다'
]

# TF-IDF 벡터화 기본 파라미터
# 변경 이력: 2025-10-06 - Word-based에서 Character n-gram으로 전환
# 이유: 테스트 결과 Character n-gram이 부분 매칭, 오타 허용, 복합어 처리에서 우수
# 성능: Top-1 평균 유사도 0.097 → 0.179 (약 85% 향상)
TFIDF_CONFIG = {
    'ngram_range': (2, 4),           # 2~4 글자 조합 (Character n-gram)
    'analyzer': 'char',              # 문자 기반 분석
    'min_df': 1,                     # 최소 1개 문서
    'max_df': 0.85,                  # 최대 85% 문서
    'sublinear_tf': True,            # log 스케일링 적용
    'use_idf': True,                 # IDF 가중치 사용
    'smooth_idf': True,              # IDF 평활화
    'norm': 'l2',                    # L2 정규화
    'lowercase': True                # 소문자 변환
}

# 이전 Word-based 설정 (백업용 참고)
# TFIDF_CONFIG_WORD_BACKUP = {
#     'ngram_range': (1, 2),
#     'analyzer': 'word',
#     'stop_words': LEGAL_STOPWORDS,
#     'min_df': 1,
#     'max_df': 0.8,
#     'sublinear_tf': True,
#     'use_idf': True,
#     'smooth_idf': True,
#     'norm': 'l2'
# }

# 검색 기본 설정
SEARCH_CONFIG = {
    'top_k': 3,                      # 반환할 상위 결과 수
    'threshold': 0.01,               # 최소 유사도 임계값
    'default_content_weight': 1.0,   # 내용 가중치 (기본값)
    'default_title_weight': 0.0      # 제목 가중치 (기본값)
}
