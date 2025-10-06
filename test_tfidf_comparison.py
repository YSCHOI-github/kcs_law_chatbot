"""
TF-IDF 비교 테스트 스크립트

Word-based TF-IDF vs Character-based TF-IDF 성능 비교
"""

import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
from datetime import datetime


# 법령 전용 불용어 (Word 방식에만 사용)
LEGAL_STOPWORDS = [
    '것', '등', '때', '경우', '바', '수', '점', '면', '이', '그', '저', '은', '는', '을', '를', '에', '으로', '의',
    '따라', '또는', '및', '있다', '한다', '되어', '인한', '대한', '관한', '위한', '통한', '같은', '다른',
    '조항', '규정', '법률', '법령', '조문', '항목', '세부', '내용', '사항', '요건', '기준', '방법', '절차',
    '해당', '관련', '포함', '제외', '적용', '시행', '준용', '의하다', '하다', '되다', '있다', '없다', '같다'
]

# Word-based TF-IDF 설정
TFIDF_CONFIG_WORD = {
    'ngram_range': (1, 2),
    'analyzer': 'word',
    'stop_words': LEGAL_STOPWORDS,
    'min_df': 1,
    'max_df': 0.8,
    'sublinear_tf': True,
    'use_idf': True,
    'smooth_idf': True,
    'norm': 'l2'
}

# Character-based TF-IDF 설정
TFIDF_CONFIG_CHAR = {
    'ngram_range': (2, 4),
    'analyzer': 'char',
    'min_df': 1,
    'max_df': 0.8,
    'sublinear_tf': True,
    'use_idf': True,
    'smooth_idf': True,
    'norm': 'l2'
}


def load_law_data(json_path):
    """법령 JSON 데이터 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chunks = []
    metadata = []

    for law_name, law_info in data.items():
        law_data = law_info.get('data', [])
        for article in law_data:
            # 청크 구성: [조번호] (제목) 내용
            chunk_parts = []

            if "조번호" in article:
                chunk_parts.append(f"[제{article['조번호']}조]")
            if "제목" in article:
                chunk_parts.append(f"({article['제목']})")
            if "내용" in article:
                chunk_parts.append(article['내용'])

            if chunk_parts:
                chunks.append(" ".join(chunk_parts))
                metadata.append({
                    'law_name': law_name,
                    'article_no': article.get('조번호', ''),
                    'title': article.get('제목', ''),
                })

    return chunks, metadata


def create_tfidf_vectorizer(config):
    """TF-IDF 벡터라이저 생성 및 학습"""
    vectorizer = TfidfVectorizer(**config)
    return vectorizer


def search_tfidf(query, vectorizer, tfidf_matrix, chunks, metadata, top_k=5):
    """TF-IDF 검색"""
    try:
        query_vec = vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()

        # 상위 K개 인덱스
        top_indices = similarities.argsort()[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append({
                'rank': len(results) + 1,
                'similarity': float(similarities[idx]),
                'chunk': chunks[idx],
                'metadata': metadata[idx]
            })

        return results
    except Exception as e:
        return []


def load_test_queries(json_path):
    """테스트 쿼리 로드"""
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data


def calculate_metrics(results, top_k_values=[1, 3, 5]):
    """성능 지표 계산"""
    metrics = {
        'total_queries': len(results),
        'avg_similarity_top1': 0,
        'avg_similarity_top3': 0,
        'avg_similarity_top5': 0,
        'coverage': 0,
    }

    if len(results) == 0:
        return metrics

    # 평균 유사도 계산
    top1_sims = []
    top3_sims = []
    top5_sims = []

    for result in results:
        search_results = result.get('search_results', [])
        if len(search_results) > 0:
            top1_sims.append(search_results[0]['similarity'])
        if len(search_results) >= 3:
            top3_sims.append(np.mean([r['similarity'] for r in search_results[:3]]))
        if len(search_results) >= 5:
            top5_sims.append(np.mean([r['similarity'] for r in search_results[:5]]))

    if top1_sims:
        metrics['avg_similarity_top1'] = np.mean(top1_sims)
    if top3_sims:
        metrics['avg_similarity_top3'] = np.mean(top3_sims)
    if top5_sims:
        metrics['avg_similarity_top5'] = np.mean(top5_sims)

    # Coverage: 최소 1개 이상의 결과를 찾은 쿼리 비율
    queries_with_results = sum(1 for r in results if len(r.get('search_results', [])) > 0)
    metrics['coverage'] = queries_with_results / len(results) * 100

    return metrics


def run_comparison_test():
    """비교 테스트 실행"""
    print("=" * 80)
    print("TF-IDF 비교 테스트 시작")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1/6] 법령 데이터 로드 중...")
    law_path = Path("laws/customs_investigation.json")
    chunks, metadata = load_law_data(law_path)
    print(f"  - 로드된 조문 수: {len(chunks)}")

    # 2. Word-based TF-IDF 벡터화
    print("\n[2/6] Word-based TF-IDF 벡터화 중...")
    word_vectorizer = create_tfidf_vectorizer(TFIDF_CONFIG_WORD)
    word_matrix = word_vectorizer.fit_transform(chunks)
    print(f"  - Vocabulary 크기: {len(word_vectorizer.vocabulary_)}")
    print(f"  - Matrix 크기: {word_matrix.shape}")

    # 3. Char-based TF-IDF 벡터화
    print("\n[3/6] Char-based TF-IDF 벡터화 중...")
    char_vectorizer = create_tfidf_vectorizer(TFIDF_CONFIG_CHAR)
    char_matrix = char_vectorizer.fit_transform(chunks)
    print(f"  - Vocabulary 크기: {len(char_vectorizer.vocabulary_)}")
    print(f"  - Matrix 크기: {char_matrix.shape}")

    # 4. 테스트 쿼리 로드
    print("\n[4/6] 테스트 쿼리 로드 중...")
    test_data = load_test_queries("test_queries.json")
    test_cases = test_data['test_cases']
    print(f"  - 테스트 쿼리 수: {len(test_cases)}")

    # 5. 검색 테스트 실행
    print("\n[5/6] 검색 테스트 실행 중...")
    word_results = []
    char_results = []

    for i, test_case in enumerate(test_cases, 1):
        query = test_case['query']
        print(f"  [{i}/{len(test_cases)}] '{query}'")

        # Word 방식 검색
        word_search = search_tfidf(query, word_vectorizer, word_matrix, chunks, metadata, top_k=5)
        word_results.append({
            'test_case': test_case,
            'search_results': word_search
        })

        # Char 방식 검색
        char_search = search_tfidf(query, char_vectorizer, char_matrix, chunks, metadata, top_k=5)
        char_results.append({
            'test_case': test_case,
            'search_results': char_search
        })

    # 6. 결과 분석 및 저장
    print("\n[6/6] 결과 분석 및 저장 중...")

    # 전체 메트릭 계산
    word_metrics = calculate_metrics(word_results)
    char_metrics = calculate_metrics(char_results)

    # 카테고리별 메트릭 계산
    categories = set(tc['category'] for tc in test_cases)
    category_metrics = {}

    for category in categories:
        word_cat_results = [r for r in word_results if r['test_case']['category'] == category]
        char_cat_results = [r for r in char_results if r['test_case']['category'] == category]

        category_metrics[category] = {
            'word': calculate_metrics(word_cat_results),
            'char': calculate_metrics(char_cat_results)
        }

    # 결과 저장
    output = {
        'metadata': {
            'test_date': datetime.now().isoformat(),
            'total_queries': len(test_cases),
            'total_articles': len(chunks),
            'word_config': TFIDF_CONFIG_WORD,
            'char_config': TFIDF_CONFIG_CHAR
        },
        'overall_metrics': {
            'word': word_metrics,
            'char': char_metrics
        },
        'category_metrics': category_metrics,
        'detailed_results': {
            'word': word_results,
            'char': char_results
        }
    }

    output_path = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n결과 저장 완료: {output_path}")

    # 7. 콘솔 출력
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)

    print("\n전체 성능 비교:")
    print(f"{'지표':<30} {'Word-based':<15} {'Char-based':<15}")
    print("-" * 60)
    print(f"{'Avg Similarity (Top-1)':<30} {word_metrics['avg_similarity_top1']:<15.4f} {char_metrics['avg_similarity_top1']:<15.4f}")
    print(f"{'Avg Similarity (Top-3)':<30} {word_metrics['avg_similarity_top3']:<15.4f} {char_metrics['avg_similarity_top3']:<15.4f}")
    print(f"{'Avg Similarity (Top-5)':<30} {word_metrics['avg_similarity_top5']:<15.4f} {char_metrics['avg_similarity_top5']:<15.4f}")
    print(f"{'Coverage (%)':<30} {word_metrics['coverage']:<15.2f} {char_metrics['coverage']:<15.2f}")

    print("\n\n카테고리별 성능 비교 (Top-1 Avg Similarity):")
    print(f"{'카테고리':<25} {'Word-based':<15} {'Char-based':<15} {'차이':<15}")
    print("-" * 70)
    for category in sorted(categories):
        word_sim = category_metrics[category]['word']['avg_similarity_top1']
        char_sim = category_metrics[category]['char']['avg_similarity_top1']
        diff = char_sim - word_sim
        print(f"{category:<25} {word_sim:<15.4f} {char_sim:<15.4f} {diff:+.4f}")

    print("\n" + "=" * 80)
    print(f"상세 결과는 {output_path} 파일을 확인하세요.")
    print("=" * 80)

    return output_path


if __name__ == "__main__":
    run_comparison_test()
