"""
Performance Benchmarking for Retrieval Engine

This script benchmarks the retrieval engine across multiple dimensions:
- Latency (p50, p95, p99, p99.9)
- Throughput (queries per second)
- Memory usage
- Accuracy metrics (relevance, diversity)
- Performance at different dataset sizes
- Parameter optimization

Generates a comprehensive performance report.

Usage:
    python benchmark_retrieval_engine.py --output benchmark_report.md

Requirements:
    - Qdrant running on localhost:6333
    - OpenAI API key for embeddings
    - Test documents loaded in vector store
"""

import asyncio
import time
import argparse
import statistics
import tracemalloc
import json
from typing import List, Dict, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
import uuid

from app.services.retrieval_engine import (
    RetrievalEngine,
    RetrievalConfig,
    RetrievalResult
)
from app.services.vector_store import QdrantStore, VectorStoreConfig
from app.models.document import DocumentFilters
from llama_index.embeddings.openai import OpenAIEmbedding
import os


# ============================================================================
# Configuration and Test Data
# ============================================================================

TEST_QUERIES = [
    # Simple queries
    "organizational capacity",
    "program evaluation",
    "budget narrative",

    # Multi-term queries
    "early childhood education programs",
    "youth development leadership training",
    "family support services community engagement",

    # Complex domain-specific queries
    "organizational capacity staff qualifications board governance track record",
    "program outcomes impact evaluation data-driven decision making",
    "budget sustainability funding model cost-effectiveness financial management",

    # Long-form queries
    """
    We need comprehensive information about our organization's track record
    of successfully implementing early childhood education programs with proven
    outcomes and strong community partnerships
    """,
]


@dataclass
class BenchmarkResult:
    """Results from a single benchmark test"""
    test_name: str
    query_count: int
    total_time_ms: float
    mean_latency_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    p999_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    throughput_qps: float
    memory_mb: float = 0.0
    config: Dict = None
    notes: str = ""


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for retrieval quality"""
    test_name: str
    avg_score: float
    score_distribution: Dict[str, int]
    avg_results_per_query: float
    diversity_score: float  # Unique documents / total results
    recency_score: float  # Avg year of results


# ============================================================================
# Benchmark Functions
# ============================================================================

async def measure_latency(
    engine: RetrievalEngine,
    queries: List[str],
    top_k: int = 5,
    filters: DocumentFilters = None
) -> Tuple[List[float], List[List[RetrievalResult]]]:
    """
    Measure retrieval latency for a list of queries

    Returns:
        Tuple of (latencies in ms, results for each query)
    """
    latencies = []
    all_results = []

    for query in queries:
        start = time.perf_counter()

        try:
            results = await engine.retrieve(
                query=query,
                top_k=top_k,
                filters=filters
            )
        except Exception as e:
            print(f"Error retrieving for query '{query[:50]}...': {e}")
            results = []

        end = time.perf_counter()
        latency_ms = (end - start) * 1000

        latencies.append(latency_ms)
        all_results.append(results)

    return latencies, all_results


async def measure_throughput(
    engine: RetrievalEngine,
    queries: List[str],
    duration_seconds: float = 10.0
) -> float:
    """
    Measure throughput (queries per second) over a fixed duration

    Returns:
        Queries per second
    """
    query_count = 0
    start = time.perf_counter()
    end_time = start + duration_seconds

    while time.perf_counter() < end_time:
        # Use a random query
        query = queries[query_count % len(queries)]

        try:
            await engine.retrieve(query=query, top_k=5)
            query_count += 1
        except Exception as e:
            print(f"Error during throughput test: {e}")
            break

    elapsed = time.perf_counter() - start
    qps = query_count / elapsed

    return qps


async def measure_concurrent_throughput(
    engine: RetrievalEngine,
    queries: List[str],
    num_concurrent: int = 5,
    duration_seconds: float = 10.0
) -> Tuple[float, int]:
    """
    Measure throughput with concurrent requests

    Returns:
        Tuple of (QPS, total queries completed)
    """
    query_counts = [0] * num_concurrent
    start = time.perf_counter()
    end_time = start + duration_seconds

    async def worker(worker_id: int):
        while time.perf_counter() < end_time:
            query = queries[query_counts[worker_id] % len(queries)]
            try:
                await engine.retrieve(query=query, top_k=5)
                query_counts[worker_id] += 1
            except Exception as e:
                print(f"Worker {worker_id} error: {e}")
                break

    # Run workers concurrently
    await asyncio.gather(*[worker(i) for i in range(num_concurrent)])

    elapsed = time.perf_counter() - start
    total_queries = sum(query_counts)
    qps = total_queries / elapsed

    return qps, total_queries


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile of a list of values"""
    if not values:
        return 0.0

    sorted_values = sorted(values)
    index = int(len(sorted_values) * percentile / 100)
    index = min(index, len(sorted_values) - 1)

    return sorted_values[index]


def analyze_accuracy(
    queries: List[str],
    results: List[List[RetrievalResult]]
) -> AccuracyMetrics:
    """
    Analyze accuracy and quality of retrieval results

    Returns:
        AccuracyMetrics object with quality measurements
    """
    # Calculate average score
    all_scores = []
    for result_list in results:
        for result in result_list:
            all_scores.append(result.score)

    avg_score = statistics.mean(all_scores) if all_scores else 0.0

    # Score distribution (buckets)
    score_buckets = {
        "0.0-0.2": 0,
        "0.2-0.4": 0,
        "0.4-0.6": 0,
        "0.6-0.8": 0,
        "0.8-1.0": 0,
        "1.0+": 0
    }

    for score in all_scores:
        if score < 0.2:
            score_buckets["0.0-0.2"] += 1
        elif score < 0.4:
            score_buckets["0.2-0.4"] += 1
        elif score < 0.6:
            score_buckets["0.4-0.6"] += 1
        elif score < 0.8:
            score_buckets["0.6-0.8"] += 1
        elif score < 1.0:
            score_buckets["0.8-1.0"] += 1
        else:
            score_buckets["1.0+"] += 1

    # Average results per query
    result_counts = [len(r) for r in results]
    avg_results = statistics.mean(result_counts) if result_counts else 0.0

    # Diversity score (unique documents / total results)
    unique_docs = set()
    total_results = 0
    for result_list in results:
        for result in result_list:
            doc_id = result.metadata.get("doc_id")
            if doc_id:
                unique_docs.add(doc_id)
            total_results += 1

    diversity_score = len(unique_docs) / total_results if total_results > 0 else 0.0

    # Recency score (average year)
    years = []
    for result_list in results:
        for result in result_list:
            year = result.metadata.get("year")
            if year:
                years.append(year)

    recency_score = statistics.mean(years) if years else 0.0

    return AccuracyMetrics(
        test_name="accuracy",
        avg_score=avg_score,
        score_distribution=score_buckets,
        avg_results_per_query=avg_results,
        diversity_score=diversity_score,
        recency_score=recency_score
    )


# ============================================================================
# Benchmark Suites
# ============================================================================

async def benchmark_basic_latency(engine: RetrievalEngine) -> BenchmarkResult:
    """Benchmark basic retrieval latency"""
    print("\n[1/8] Benchmarking basic latency...")

    latencies, _ = await measure_latency(engine, TEST_QUERIES, top_k=5)

    return BenchmarkResult(
        test_name="Basic Latency (top_k=5)",
        query_count=len(latencies),
        total_time_ms=sum(latencies),
        mean_latency_ms=statistics.mean(latencies),
        median_latency_ms=statistics.median(latencies),
        p95_latency_ms=calculate_percentile(latencies, 95),
        p99_latency_ms=calculate_percentile(latencies, 99),
        p999_latency_ms=calculate_percentile(latencies, 99.9),
        min_latency_ms=min(latencies),
        max_latency_ms=max(latencies),
        throughput_qps=len(latencies) / (sum(latencies) / 1000),
        config=asdict(engine.config)
    )


async def benchmark_varying_top_k(engine: RetrievalEngine) -> List[BenchmarkResult]:
    """Benchmark latency with different top_k values"""
    print("\n[2/8] Benchmarking varying top_k...")

    results = []
    top_k_values = [1, 3, 5, 10, 20]

    for top_k in top_k_values:
        latencies, _ = await measure_latency(
            engine,
            TEST_QUERIES[:5],  # Subset for speed
            top_k=top_k
        )

        result = BenchmarkResult(
            test_name=f"Latency (top_k={top_k})",
            query_count=len(latencies),
            total_time_ms=sum(latencies),
            mean_latency_ms=statistics.mean(latencies),
            median_latency_ms=statistics.median(latencies),
            p95_latency_ms=calculate_percentile(latencies, 95),
            p99_latency_ms=calculate_percentile(latencies, 99),
            p999_latency_ms=calculate_percentile(latencies, 99.9),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            throughput_qps=len(latencies) / (sum(latencies) / 1000),
            notes=f"top_k={top_k}"
        )
        results.append(result)

    return results


async def benchmark_with_filters(engine: RetrievalEngine) -> List[BenchmarkResult]:
    """Benchmark latency with various filters"""
    print("\n[3/8] Benchmarking with filters...")

    results = []

    # Test 1: No filters (baseline)
    latencies_no_filter, _ = await measure_latency(
        engine,
        TEST_QUERIES[:5],
        top_k=5,
        filters=None
    )

    results.append(BenchmarkResult(
        test_name="With Filters: None (baseline)",
        query_count=len(latencies_no_filter),
        total_time_ms=sum(latencies_no_filter),
        mean_latency_ms=statistics.mean(latencies_no_filter),
        median_latency_ms=statistics.median(latencies_no_filter),
        p95_latency_ms=calculate_percentile(latencies_no_filter, 95),
        p99_latency_ms=calculate_percentile(latencies_no_filter, 99),
        p999_latency_ms=calculate_percentile(latencies_no_filter, 99.9),
        min_latency_ms=min(latencies_no_filter),
        max_latency_ms=max(latencies_no_filter),
        throughput_qps=len(latencies_no_filter) / (sum(latencies_no_filter) / 1000),
        notes="No filters applied"
    ))

    # Test 2: Document type filter
    filters_doc_type = DocumentFilters(doc_types=["Grant Proposal"])
    latencies_doc_type, _ = await measure_latency(
        engine,
        TEST_QUERIES[:5],
        top_k=5,
        filters=filters_doc_type
    )

    results.append(BenchmarkResult(
        test_name="With Filters: Document type",
        query_count=len(latencies_doc_type),
        total_time_ms=sum(latencies_doc_type),
        mean_latency_ms=statistics.mean(latencies_doc_type),
        median_latency_ms=statistics.median(latencies_doc_type),
        p95_latency_ms=calculate_percentile(latencies_doc_type, 95),
        p99_latency_ms=calculate_percentile(latencies_doc_type, 99),
        p999_latency_ms=calculate_percentile(latencies_doc_type, 99.9),
        min_latency_ms=min(latencies_doc_type),
        max_latency_ms=max(latencies_doc_type),
        throughput_qps=len(latencies_doc_type) / (sum(latencies_doc_type) / 1000),
        notes="Filter: doc_type=Grant Proposal"
    ))

    # Test 3: Complex filters (type + year range + programs)
    filters_complex = DocumentFilters(
        doc_types=["Grant Proposal", "Annual Report"],
        date_range=(2020, 2024),
        programs=["Early Childhood"]
    )
    latencies_complex, _ = await measure_latency(
        engine,
        TEST_QUERIES[:5],
        top_k=5,
        filters=filters_complex
    )

    results.append(BenchmarkResult(
        test_name="With Filters: Complex (3 filters)",
        query_count=len(latencies_complex),
        total_time_ms=sum(latencies_complex),
        mean_latency_ms=statistics.mean(latencies_complex),
        median_latency_ms=statistics.median(latencies_complex),
        p95_latency_ms=calculate_percentile(latencies_complex, 95),
        p99_latency_ms=calculate_percentile(latencies_complex, 99),
        p999_latency_ms=calculate_percentile(latencies_complex, 99.9),
        min_latency_ms=min(latencies_complex),
        max_latency_ms=max(latencies_complex),
        throughput_qps=len(latencies_complex) / (sum(latencies_complex) / 1000),
        notes="Filters: doc_type + year_range + programs"
    ))

    return results


async def benchmark_throughput(engine: RetrievalEngine) -> BenchmarkResult:
    """Benchmark single-threaded throughput"""
    print("\n[4/8] Benchmarking throughput (single-threaded)...")

    duration = 10.0  # seconds
    qps = await measure_throughput(engine, TEST_QUERIES[:5], duration)

    return BenchmarkResult(
        test_name="Throughput (single-threaded)",
        query_count=int(qps * duration),
        total_time_ms=duration * 1000,
        mean_latency_ms=1000 / qps,  # Approximate
        median_latency_ms=1000 / qps,
        p95_latency_ms=0,  # Not measured in throughput test
        p99_latency_ms=0,
        p999_latency_ms=0,
        min_latency_ms=0,
        max_latency_ms=0,
        throughput_qps=qps,
        notes=f"Sustained over {duration}s"
    )


async def benchmark_concurrent_throughput(engine: RetrievalEngine) -> List[BenchmarkResult]:
    """Benchmark concurrent throughput with varying concurrency"""
    print("\n[5/8] Benchmarking concurrent throughput...")

    results = []
    concurrency_levels = [1, 2, 5, 10]
    duration = 10.0

    for num_concurrent in concurrency_levels:
        qps, total_queries = await measure_concurrent_throughput(
            engine,
            TEST_QUERIES[:5],
            num_concurrent=num_concurrent,
            duration_seconds=duration
        )

        result = BenchmarkResult(
            test_name=f"Concurrent Throughput (n={num_concurrent})",
            query_count=total_queries,
            total_time_ms=duration * 1000,
            mean_latency_ms=1000 / (qps / num_concurrent) if qps > 0 else 0,
            median_latency_ms=0,
            p95_latency_ms=0,
            p99_latency_ms=0,
            p999_latency_ms=0,
            min_latency_ms=0,
            max_latency_ms=0,
            throughput_qps=qps,
            notes=f"{num_concurrent} concurrent workers, {duration}s"
        )
        results.append(result)

    return results


async def benchmark_memory_usage(engine: RetrievalEngine) -> BenchmarkResult:
    """Benchmark memory usage during retrieval"""
    print("\n[6/8] Benchmarking memory usage...")

    # Start memory tracking
    tracemalloc.start()

    # Run queries
    latencies, _ = await measure_latency(engine, TEST_QUERIES, top_k=5)

    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    memory_mb = peak / (1024 * 1024)  # Convert to MB

    return BenchmarkResult(
        test_name="Memory Usage",
        query_count=len(latencies),
        total_time_ms=sum(latencies),
        mean_latency_ms=statistics.mean(latencies),
        median_latency_ms=statistics.median(latencies),
        p95_latency_ms=calculate_percentile(latencies, 95),
        p99_latency_ms=calculate_percentile(latencies, 99),
        p999_latency_ms=calculate_percentile(latencies, 99.9),
        min_latency_ms=min(latencies),
        max_latency_ms=max(latencies),
        throughput_qps=len(latencies) / (sum(latencies) / 1000),
        memory_mb=memory_mb,
        notes=f"Peak memory: {memory_mb:.2f} MB"
    )


async def benchmark_accuracy(engine: RetrievalEngine) -> Tuple[BenchmarkResult, AccuracyMetrics]:
    """Benchmark accuracy and quality of results"""
    print("\n[7/8] Benchmarking accuracy and quality...")

    latencies, results = await measure_latency(engine, TEST_QUERIES, top_k=5)

    accuracy = analyze_accuracy(TEST_QUERIES, results)

    benchmark = BenchmarkResult(
        test_name="Accuracy Benchmark",
        query_count=len(latencies),
        total_time_ms=sum(latencies),
        mean_latency_ms=statistics.mean(latencies),
        median_latency_ms=statistics.median(latencies),
        p95_latency_ms=calculate_percentile(latencies, 95),
        p99_latency_ms=calculate_percentile(latencies, 99),
        p999_latency_ms=calculate_percentile(latencies, 99.9),
        min_latency_ms=min(latencies),
        max_latency_ms=max(latencies),
        throughput_qps=len(latencies) / (sum(latencies) / 1000),
        notes=f"Avg score: {accuracy.avg_score:.3f}, Diversity: {accuracy.diversity_score:.3f}"
    )

    return benchmark, accuracy


async def benchmark_parameter_optimization(
    vector_store,
    embedding_model
) -> List[Tuple[RetrievalConfig, BenchmarkResult]]:
    """Test different parameter configurations to find optimal settings"""
    print("\n[8/8] Benchmarking parameter optimization...")

    configurations = [
        # Baseline
        RetrievalConfig(vector_weight=0.7, keyword_weight=0.3, recency_weight=0.7),

        # Vector-heavy
        RetrievalConfig(vector_weight=0.9, keyword_weight=0.1, recency_weight=0.7),

        # Keyword-heavy
        RetrievalConfig(vector_weight=0.3, keyword_weight=0.7, recency_weight=0.7),

        # Balanced
        RetrievalConfig(vector_weight=0.5, keyword_weight=0.5, recency_weight=0.7),

        # No recency
        RetrievalConfig(vector_weight=0.7, keyword_weight=0.3, recency_weight=0.0),

        # High recency
        RetrievalConfig(vector_weight=0.7, keyword_weight=0.3, recency_weight=1.0),
    ]

    results = []

    for i, config in enumerate(configurations):
        print(f"   Testing config {i+1}/{len(configurations)}: "
              f"v={config.vector_weight:.1f}, k={config.keyword_weight:.1f}, r={config.recency_weight:.1f}")

        # Create engine with this config
        engine = RetrievalEngine(
            vector_store=vector_store,
            embedding_model=embedding_model,
            config=config
        )
        await engine.build_bm25_index()

        # Benchmark
        latencies, _ = await measure_latency(engine, TEST_QUERIES[:5], top_k=5)

        benchmark = BenchmarkResult(
            test_name=f"Config: v={config.vector_weight:.1f} k={config.keyword_weight:.1f} r={config.recency_weight:.1f}",
            query_count=len(latencies),
            total_time_ms=sum(latencies),
            mean_latency_ms=statistics.mean(latencies),
            median_latency_ms=statistics.median(latencies),
            p95_latency_ms=calculate_percentile(latencies, 95),
            p99_latency_ms=calculate_percentile(latencies, 99),
            p999_latency_ms=calculate_percentile(latencies, 99.9),
            min_latency_ms=min(latencies),
            max_latency_ms=max(latencies),
            throughput_qps=len(latencies) / (sum(latencies) / 1000),
            config=asdict(config)
        )

        results.append((config, benchmark))

    return results


# ============================================================================
# Report Generation
# ============================================================================

def generate_report(
    all_results: Dict[str, any],
    output_file: str
):
    """Generate comprehensive markdown report"""

    report = f"""# Retrieval Engine Performance Benchmark Report

**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Executive Summary

This report contains comprehensive performance benchmarks for the Org Archivist retrieval engine,
covering latency, throughput, memory usage, accuracy, and parameter optimization.

### Key Findings

"""

    # Basic latency summary
    basic = all_results["basic_latency"]
    report += f"""
- **Average Latency:** {basic.mean_latency_ms:.2f}ms
- **P95 Latency:** {basic.p95_latency_ms:.2f}ms
- **P99 Latency:** {basic.p99_latency_ms:.2f}ms
- **Throughput (single-threaded):** {basic.throughput_qps:.2f} QPS
"""

    # Throughput summary
    throughput = all_results["throughput"]
    report += f"- **Sustained Throughput:** {throughput.throughput_qps:.2f} QPS over 10s\n"

    # Concurrent throughput
    concurrent_results = all_results["concurrent_throughput"]
    max_concurrent_qps = max(r.throughput_qps for r in concurrent_results)
    report += f"- **Max Concurrent Throughput:** {max_concurrent_qps:.2f} QPS (n={len(concurrent_results[-1])})\n"

    # Memory
    memory = all_results["memory"]
    report += f"- **Peak Memory Usage:** {memory.memory_mb:.2f} MB\n"

    # Accuracy
    accuracy = all_results["accuracy_metrics"]
    report += f"""
- **Average Relevance Score:** {accuracy.avg_score:.3f}
- **Result Diversity:** {accuracy.diversity_score:.3f} (unique docs / total results)
- **Average Recency:** {accuracy.recency_score:.1f} (document year)
"""

    report += "\n---\n\n"

    # Detailed results
    report += "## 1. Basic Latency Benchmark\n\n"
    report += format_benchmark_result(basic)

    report += "\n## 2. Latency vs top_k\n\n"
    report += "How retrieval latency changes with different result counts:\n\n"
    report += "| top_k | Mean (ms) | Median (ms) | P95 (ms) | P99 (ms) | Throughput (QPS) |\n"
    report += "|-------|-----------|-------------|----------|----------|------------------|\n"

    for result in all_results["varying_top_k"]:
        top_k = result.notes.split("=")[1]
        report += f"| {top_k:5} | {result.mean_latency_ms:9.2f} | {result.median_latency_ms:11.2f} | {result.p95_latency_ms:8.2f} | {result.p99_latency_ms:8.2f} | {result.throughput_qps:16.2f} |\n"

    report += "\n## 3. Impact of Metadata Filters\n\n"
    report += "Performance comparison with different filter configurations:\n\n"
    report += "| Filter Type | Mean (ms) | Median (ms) | P95 (ms) | P99 (ms) | Notes |\n"
    report += "|-------------|-----------|-------------|----------|----------|-------|\n"

    for result in all_results["with_filters"]:
        filter_type = result.test_name.split(": ")[1]
        report += f"| {filter_type:11} | {result.mean_latency_ms:9.2f} | {result.median_latency_ms:11.2f} | {result.p95_latency_ms:8.2f} | {result.p99_latency_ms:8.2f} | {result.notes} |\n"

    report += "\n## 4. Throughput Benchmark\n\n"
    report += format_benchmark_result(throughput)

    report += "\n## 5. Concurrent Throughput\n\n"
    report += "Throughput scaling with concurrent requests:\n\n"
    report += "| Concurrency | Throughput (QPS) | Total Queries | Duration (s) |\n"
    report += "|-------------|------------------|---------------|---------------|\n"

    for result in concurrent_results:
        n = result.notes.split()[0]
        report += f"| {n:11} | {result.throughput_qps:16.2f} | {result.query_count:13} | {result.total_time_ms/1000:13.1f} |\n"

    report += "\n## 6. Memory Usage\n\n"
    report += format_benchmark_result(memory)

    report += "\n## 7. Accuracy and Quality Metrics\n\n"
    report += f"### Overall Quality\n\n"
    report += f"- **Average Relevance Score:** {accuracy.avg_score:.3f}\n"
    report += f"- **Average Results per Query:** {accuracy.avg_results_per_query:.2f}\n"
    report += f"- **Result Diversity:** {accuracy.diversity_score:.3f}\n"
    report += f"- **Average Document Year:** {accuracy.recency_score:.1f}\n\n"

    report += "### Score Distribution\n\n"
    report += "| Score Range | Count |\n"
    report += "|-------------|-------|\n"

    for range_label, count in accuracy.score_distribution.items():
        report += f"| {range_label:11} | {count:5} |\n"

    report += "\n## 8. Parameter Optimization\n\n"
    report += "Testing different weight configurations:\n\n"
    report += "| Vector Weight | Keyword Weight | Recency Weight | Mean Latency (ms) | P95 (ms) | Throughput (QPS) |\n"
    report += "|---------------|----------------|----------------|-------------------|----------|------------------|\n"

    for config, result in all_results["parameter_optimization"]:
        report += f"| {config.vector_weight:13.1f} | {config.keyword_weight:14.1f} | {config.recency_weight:14.1f} | {result.mean_latency_ms:17.2f} | {result.p95_latency_ms:8.2f} | {result.throughput_qps:16.2f} |\n"

    # Recommendations
    report += "\n---\n\n## Recommendations\n\n"

    report += "### Performance Recommendations\n\n"

    if basic.p95_latency_ms < 500:
        report += "- ✅ **Excellent latency:** P95 latency under 500ms meets target\n"
    elif basic.p95_latency_ms < 1000:
        report += "- ⚠️ **Acceptable latency:** P95 latency between 500-1000ms\n"
    else:
        report += "- ❌ **High latency:** P95 latency over 1000ms, optimization needed\n"

    if throughput.throughput_qps >= 10:
        report += "- ✅ **Good throughput:** Sustained >10 QPS for typical workloads\n"
    else:
        report += "- ⚠️ **Low throughput:** Consider caching or optimization\n"

    if memory.memory_mb < 500:
        report += "- ✅ **Memory efficient:** Peak usage under 500MB\n"
    elif memory.memory_mb < 1000:
        report += "- ⚠️ **Moderate memory usage:** Consider monitoring for large datasets\n"
    else:
        report += "- ❌ **High memory usage:** Optimization recommended\n"

    report += "\n### Quality Recommendations\n\n"

    if accuracy.avg_score >= 0.7:
        report += "- ✅ **High relevance:** Average score >0.7 indicates good matches\n"
    elif accuracy.avg_score >= 0.5:
        report += "- ⚠️ **Moderate relevance:** Consider query expansion or tuning\n"
    else:
        report += "- ❌ **Low relevance:** Review retrieval parameters and document quality\n"

    if accuracy.diversity_score >= 0.7:
        report += "- ✅ **Good diversity:** Results span multiple documents\n"
    else:
        report += "- ⚠️ **Low diversity:** Consider adjusting max_per_doc parameter\n"

    # Find best config
    best_config, best_result = max(
        all_results["parameter_optimization"],
        key=lambda x: x[1].throughput_qps / x[1].mean_latency_ms
    )

    report += "\n### Optimal Configuration\n\n"
    report += f"""Based on benchmarks, the recommended configuration is:
- **Vector Weight:** {best_config.vector_weight:.1f}
- **Keyword Weight:** {best_config.keyword_weight:.1f}
- **Recency Weight:** {best_config.recency_weight:.1f}

This configuration provides the best balance of latency ({best_result.mean_latency_ms:.2f}ms) and throughput ({best_result.throughput_qps:.2f} QPS).
"""

    report += "\n---\n\n## Appendix: Test Configuration\n\n"
    report += f"- **Test Queries:** {len(TEST_QUERIES)}\n"
    report += f"- **Query Types:** Simple, multi-term, complex, long-form\n"
    report += f"- **Default top_k:** 5\n"
    report += f"- **Embedding Model:** OpenAI text-embedding-3-small\n"
    report += f"- **Vector Store:** Qdrant (localhost:6333)\n"

    # Write report to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"\n✅ Report generated: {output_file}")


def format_benchmark_result(result: BenchmarkResult) -> str:
    """Format a single benchmark result as markdown"""
    text = f"**Test:** {result.test_name}\n\n"
    text += f"| Metric | Value |\n"
    text += f"|--------|-------|\n"
    text += f"| Query Count | {result.query_count} |\n"
    text += f"| Total Time | {result.total_time_ms:.2f} ms |\n"
    text += f"| Mean Latency | {result.mean_latency_ms:.2f} ms |\n"
    text += f"| Median Latency | {result.median_latency_ms:.2f} ms |\n"
    text += f"| P95 Latency | {result.p95_latency_ms:.2f} ms |\n"
    text += f"| P99 Latency | {result.p99_latency_ms:.2f} ms |\n"
    text += f"| P99.9 Latency | {result.p999_latency_ms:.2f} ms |\n"
    text += f"| Min Latency | {result.min_latency_ms:.2f} ms |\n"
    text += f"| Max Latency | {result.max_latency_ms:.2f} ms |\n"
    text += f"| Throughput | {result.throughput_qps:.2f} QPS |\n"

    if result.memory_mb > 0:
        text += f"| Memory Usage | {result.memory_mb:.2f} MB |\n"

    if result.notes:
        text += f"| Notes | {result.notes} |\n"

    return text


# ============================================================================
# Main Execution
# ============================================================================

async def run_benchmarks(output_file: str):
    """Run all benchmarks and generate report"""

    print("=" * 80)
    print("Retrieval Engine Performance Benchmark")
    print("=" * 80)

    # Initialize components
    print("\nInitializing components...")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return

    # Vector store config
    vector_store_config = VectorStoreConfig(
        host="localhost",
        port=6333,
        collection_name="org_archivist_docs",
        vector_size=1536,
        use_grpc=False
    )

    vector_store = QdrantStore(vector_store_config)
    embedding_model = OpenAIEmbedding(model="text-embedding-3-small", api_key=api_key)

    # Create baseline engine
    baseline_config = RetrievalConfig(
        vector_weight=0.7,
        keyword_weight=0.3,
        recency_weight=0.7,
        max_per_doc=3,
        enable_reranking=False,
        expand_query=True
    )

    engine = RetrievalEngine(
        vector_store=vector_store,
        embedding_model=embedding_model,
        config=baseline_config
    )

    # Build BM25 index
    print("Building BM25 index...")
    await engine.build_bm25_index()

    # Run benchmarks
    print("\nRunning benchmarks...\n")

    all_results = {}

    # 1. Basic latency
    all_results["basic_latency"] = await benchmark_basic_latency(engine)

    # 2. Varying top_k
    all_results["varying_top_k"] = await benchmark_varying_top_k(engine)

    # 3. With filters
    all_results["with_filters"] = await benchmark_with_filters(engine)

    # 4. Throughput
    all_results["throughput"] = await benchmark_throughput(engine)

    # 5. Concurrent throughput
    all_results["concurrent_throughput"] = await benchmark_concurrent_throughput(engine)

    # 6. Memory usage
    all_results["memory"] = await benchmark_memory_usage(engine)

    # 7. Accuracy
    accuracy_benchmark, accuracy_metrics = await benchmark_accuracy(engine)
    all_results["accuracy_benchmark"] = accuracy_benchmark
    all_results["accuracy_metrics"] = accuracy_metrics

    # 8. Parameter optimization
    all_results["parameter_optimization"] = await benchmark_parameter_optimization(
        vector_store,
        embedding_model
    )

    # Generate report
    print("\nGenerating report...")
    generate_report(all_results, output_file)

    print("\n" + "=" * 80)
    print("Benchmarking complete!")
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="Benchmark retrieval engine performance")
    parser.add_argument(
        "--output",
        "-o",
        default="benchmark_report.md",
        help="Output file for benchmark report (default: benchmark_report.md)"
    )

    args = parser.parse_args()

    # Run benchmarks
    asyncio.run(run_benchmarks(args.output))


if __name__ == "__main__":
    main()
