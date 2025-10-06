"""
Character n-gram TF-IDF 설정 비교 테스트

설정 A: (2,4)-gram, min_df=1, max_df=0.8 (테스트 검증 설정)
설정 B: (2,5)-gram, min_df=2, max_df=0.85 (최적화 제안 설정)
"""

import json
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
from datetime import datetime
import time


# 설정 A: 테스트에서 검증된 기본 설정
TFIDF_CONFIG_A = {
    'ngram_range': (2, 4),
    'analyzer': 'char',
    'min_df': 1,
    'max_df': 0.8,
    'sublinear_tf': True,
    'use_idf': True,
    'smooth_idf': True,
    'norm': 'l2'
}

# 설정 B: 최적화 제안 설정
TFIDF_CONFIG_B = {
    'ngram_range': (2, 4),
    'analyzer': 'char',
    'min_df': 2,
    'max_df': 0.85,
    'sublinear_tf': True,
    'use_idf': True,
    'smooth_idf': True,
    'norm': 'l2',
    'lowercase': True
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

    queries_with_results = sum(1 for r in results if len(r.get('search_results', [])) > 0)
    metrics['coverage'] = queries_with_results / len(results) * 100

    return metrics


def compare_configs():
    """두 설정 비교 테스트 실행"""
    print("=" * 80)
    print("Character n-gram TF-IDF 설정 비교 테스트")
    print("=" * 80)
    print("\n설정 A (기본): (2,4)-gram, min_df=1, max_df=0.8")
    print("설정 B (최적화): (2,5)-gram, min_df=2, max_df=0.85")
    print("=" * 80)

    # 1. 데이터 로드
    print("\n[1/7] 법령 데이터 로드 중...")
    law_path = Path("laws/customs_investigation.json")
    chunks, metadata = load_law_data(law_path)
    print(f"  - 로드된 조문 수: {len(chunks)}")

    # 2. 설정 A 벡터화
    print("\n[2/7] 설정 A 벡터화 중...")
    start_time_a = time.time()
    vectorizer_a = create_tfidf_vectorizer(TFIDF_CONFIG_A)
    matrix_a = vectorizer_a.fit_transform(chunks)
    time_a = time.time() - start_time_a

    vocab_size_a = len(vectorizer_a.vocabulary_)
    matrix_size_a = matrix_a.shape
    memory_a = matrix_a.data.nbytes + matrix_a.indptr.nbytes + matrix_a.indices.nbytes

    print(f"  - Vocabulary 크기: {vocab_size_a:,}")
    print(f"  - Matrix 크기: {matrix_size_a}")
    print(f"  - 메모리 사용량: {memory_a / 1024 / 1024:.2f} MB")
    print(f"  - 벡터화 시간: {time_a:.2f}초")

    # 3. 설정 B 벡터화
    print("\n[3/7] 설정 B 벡터화 중...")
    start_time_b = time.time()
    vectorizer_b = create_tfidf_vectorizer(TFIDF_CONFIG_B)
    matrix_b = vectorizer_b.fit_transform(chunks)
    time_b = time.time() - start_time_b

    vocab_size_b = len(vectorizer_b.vocabulary_)
    matrix_size_b = matrix_b.shape
    memory_b = matrix_b.data.nbytes + matrix_b.indptr.nbytes + matrix_b.indices.nbytes

    print(f"  - Vocabulary 크기: {vocab_size_b:,}")
    print(f"  - Matrix 크기: {matrix_size_b}")
    print(f"  - 메모리 사용량: {memory_b / 1024 / 1024:.2f} MB")
    print(f"  - 벡터화 시간: {time_b:.2f}초")

    # 4. Vocabulary 크기 비교
    print("\n[4/7] Vocabulary 분석...")
    vocab_diff = vocab_size_b - vocab_size_a
    vocab_diff_pct = (vocab_diff / vocab_size_a) * 100
    memory_diff = memory_b - memory_a
    memory_diff_pct = (memory_diff / memory_a) * 100

    print(f"  - Vocabulary 차이: {vocab_diff:+,} ({vocab_diff_pct:+.1f}%)")
    print(f"  - 메모리 차이: {memory_diff / 1024 / 1024:+.2f} MB ({memory_diff_pct:+.1f}%)")

    # 5. 테스트 쿼리 로드
    print("\n[5/7] 테스트 쿼리 로드 중...")
    test_data = load_test_queries("test_queries.json")
    test_cases = test_data['test_cases']
    print(f"  - 테스트 쿼리 수: {len(test_cases)}")

    # 6. 검색 테스트 실행
    print("\n[6/7] 검색 테스트 실행 중...")
    results_a = []
    results_b = []

    search_time_a = 0
    search_time_b = 0

    for i, test_case in enumerate(test_cases, 1):
        query = test_case['query']
        print(f"  [{i}/{len(test_cases)}] '{query}'")

        # 설정 A 검색
        start = time.time()
        search_a = search_tfidf(query, vectorizer_a, matrix_a, chunks, metadata, top_k=5)
        search_time_a += time.time() - start
        results_a.append({
            'test_case': test_case,
            'search_results': search_a
        })

        # 설정 B 검색
        start = time.time()
        search_b = search_tfidf(query, vectorizer_b, matrix_b, chunks, metadata, top_k=5)
        search_time_b += time.time() - start
        results_b.append({
            'test_case': test_case,
            'search_results': search_b
        })

    avg_search_time_a = search_time_a / len(test_cases) * 1000
    avg_search_time_b = search_time_b / len(test_cases) * 1000

    # 7. 결과 분석
    print("\n[7/7] 결과 분석 중...")

    # 전체 메트릭 계산
    metrics_a = calculate_metrics(results_a)
    metrics_b = calculate_metrics(results_b)

    # 카테고리별 메트릭
    categories = set(tc['category'] for tc in test_cases)
    category_metrics = {}

    for category in categories:
        results_a_cat = [r for r in results_a if r['test_case']['category'] == category]
        results_b_cat = [r for r in results_b if r['test_case']['category'] == category]

        category_metrics[category] = {
            'config_a': calculate_metrics(results_a_cat),
            'config_b': calculate_metrics(results_b_cat)
        }

    # 결과 저장
    output = {
        'metadata': {
            'test_date': datetime.now().isoformat(),
            'total_queries': len(test_cases),
            'total_articles': len(chunks),
            'config_a': TFIDF_CONFIG_A,
            'config_b': TFIDF_CONFIG_B
        },
        'resource_usage': {
            'config_a': {
                'vocab_size': vocab_size_a,
                'memory_mb': memory_a / 1024 / 1024,
                'vectorization_time': time_a,
                'avg_search_time_ms': avg_search_time_a
            },
            'config_b': {
                'vocab_size': vocab_size_b,
                'memory_mb': memory_b / 1024 / 1024,
                'vectorization_time': time_b,
                'avg_search_time_ms': avg_search_time_b
            }
        },
        'overall_metrics': {
            'config_a': metrics_a,
            'config_b': metrics_b
        },
        'category_metrics': category_metrics,
        'detailed_results': {
            'config_a': results_a,
            'config_b': results_b
        }
    }

    output_path = f"test_char_ngram_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 콘솔 출력
    print("\n" + "=" * 80)
    print("리소스 사용량 비교")
    print("=" * 80)
    print(f"{'지표':<30} {'설정 A':<20} {'설정 B':<20} {'차이':<15}")
    print("-" * 85)
    print(f"{'Vocabulary 크기':<30} {vocab_size_a:<20,} {vocab_size_b:<20,} {vocab_diff:+,} ({vocab_diff_pct:+.1f}%)")
    print(f"{'메모리 (MB)':<30} {memory_a/1024/1024:<20.2f} {memory_b/1024/1024:<20.2f} {memory_diff/1024/1024:+.2f} ({memory_diff_pct:+.1f}%)")
    print(f"{'벡터화 시간 (초)':<30} {time_a:<20.2f} {time_b:<20.2f} {time_b-time_a:+.2f}")
    print(f"{'평균 검색 시간 (ms)':<30} {avg_search_time_a:<20.2f} {avg_search_time_b:<20.2f} {avg_search_time_b-avg_search_time_a:+.2f}")

    print("\n" + "=" * 80)
    print("검색 성능 비교")
    print("=" * 80)
    print(f"{'지표':<30} {'설정 A':<20} {'설정 B':<20} {'차이':<15}")
    print("-" * 85)

    sim_diff_top1 = metrics_b['avg_similarity_top1'] - metrics_a['avg_similarity_top1']
    sim_diff_pct_top1 = (sim_diff_top1 / metrics_a['avg_similarity_top1']) * 100 if metrics_a['avg_similarity_top1'] > 0 else 0

    sim_diff_top3 = metrics_b['avg_similarity_top3'] - metrics_a['avg_similarity_top3']
    sim_diff_pct_top3 = (sim_diff_top3 / metrics_a['avg_similarity_top3']) * 100 if metrics_a['avg_similarity_top3'] > 0 else 0

    sim_diff_top5 = metrics_b['avg_similarity_top5'] - metrics_a['avg_similarity_top5']
    sim_diff_pct_top5 = (sim_diff_top5 / metrics_a['avg_similarity_top5']) * 100 if metrics_a['avg_similarity_top5'] > 0 else 0

    print(f"{'Avg Similarity (Top-1)':<30} {metrics_a['avg_similarity_top1']:<20.4f} {metrics_b['avg_similarity_top1']:<20.4f} {sim_diff_top1:+.4f} ({sim_diff_pct_top1:+.1f}%)")
    print(f"{'Avg Similarity (Top-3)':<30} {metrics_a['avg_similarity_top3']:<20.4f} {metrics_b['avg_similarity_top3']:<20.4f} {sim_diff_top3:+.4f} ({sim_diff_pct_top3:+.1f}%)")
    print(f"{'Avg Similarity (Top-5)':<30} {metrics_a['avg_similarity_top5']:<20.4f} {metrics_b['avg_similarity_top5']:<20.4f} {sim_diff_top5:+.4f} ({sim_diff_pct_top5:+.1f}%)")
    print(f"{'Coverage (%)':<30} {metrics_a['coverage']:<20.2f} {metrics_b['coverage']:<20.2f} {metrics_b['coverage']-metrics_a['coverage']:+.2f}")

    print("\n" + "=" * 80)
    print("카테고리별 성능 비교 (Top-1 Avg Similarity)")
    print("=" * 80)
    print(f"{'카테고리':<25} {'설정 A':<15} {'설정 B':<15} {'차이':<15}")
    print("-" * 70)

    for category in sorted(categories):
        sim_a = category_metrics[category]['config_a']['avg_similarity_top1']
        sim_b = category_metrics[category]['config_b']['avg_similarity_top1']
        diff = sim_b - sim_a
        print(f"{category:<25} {sim_a:<15.4f} {sim_b:<15.4f} {diff:+.4f}")

    print("\n" + "=" * 80)
    print("종합 분석")
    print("=" * 80)

    # 성능 우위 판단
    performance_better = "설정 B" if metrics_b['avg_similarity_top1'] > metrics_a['avg_similarity_top1'] else "설정 A"
    resource_better = "설정 A" if memory_a < memory_b else "설정 B"
    speed_better = "설정 A" if avg_search_time_a < avg_search_time_b else "설정 B"

    print(f"\n검색 성능 우위: {performance_better}")
    print(f"리소스 효율 우위: {resource_better}")
    print(f"검색 속도 우위: {speed_better}")

    # 카테고리별 승률
    category_wins_a = sum(1 for cat in categories if category_metrics[cat]['config_a']['avg_similarity_top1'] > category_metrics[cat]['config_b']['avg_similarity_top1'])
    category_wins_b = sum(1 for cat in categories if category_metrics[cat]['config_b']['avg_similarity_top1'] > category_metrics[cat]['config_a']['avg_similarity_top1'])

    print(f"\n카테고리별 승률:")
    print(f"  - 설정 A 승리: {category_wins_a}/{len(categories)} 카테고리")
    print(f"  - 설정 B 승리: {category_wins_b}/{len(categories)} 카테고리")

    print("\n" + "=" * 80)
    print(f"상세 결과는 {output_path} 파일을 확인하세요.")
    print("=" * 80)

    return output_path


if __name__ == "__main__":
    compare_configs()
