"""
Performance benchmarks for NLP components.

Tests response times, throughput, and resource usage for natural language
processing components under various load conditions.
"""

import pytest
import asyncio
import time
import statistics
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
import psutil
import gc

from combadge.intelligence.intent_classifier import IntentClassifier
from combadge.intelligence.entity_extractor import EntityExtractor
from combadge.intelligence.reasoning_engine import ReasoningEngine
from combadge.intelligence.llm_manager import LLMManager


class TestNLPPerformance:
    """Performance benchmarks for NLP components"""

    @pytest.fixture
    def fast_mock_llm(self):
        """Fast mock LLM for performance testing"""
        mock_llm = Mock(spec=LLMManager)
        mock_llm.is_available = Mock(return_value=True)
        
        # Fast async response
        async def fast_response(prompt, context=None):
            await asyncio.sleep(0.01)  # Simulate minimal processing time
            if "classify" in prompt.lower():
                return {
                    "intent": "maintenance_scheduling",
                    "confidence": 0.90,
                    "reasoning": ["Fast classification"]
                }
            elif "extract" in prompt.lower():
                return {
                    "entities": {"vehicle_id": "F-123", "date": "tomorrow"},
                    "confidence": 0.88
                }
            else:
                return {
                    "reasoning_steps": ["Fast reasoning"],
                    "conclusion": "Proceed",
                    "confidence": 0.89,
                    "recommendation": "proceed"
                }
        
        mock_llm.generate_response = fast_response
        return mock_llm

    @pytest.fixture
    def performance_nlp_components(self, fast_mock_llm):
        """NLP components configured for performance testing"""
        return {
            "intent_classifier": IntentClassifier(llm_manager=fast_mock_llm),
            "entity_extractor": EntityExtractor(llm_manager=fast_mock_llm),
            "reasoning_engine": ReasoningEngine(llm_manager=fast_mock_llm)
        }

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_intent_classification_response_time(self, performance_nlp_components, performance_monitor):
        """Benchmark intent classification response times"""
        classifier = performance_nlp_components["intent_classifier"]
        
        test_texts = [
            "Schedule maintenance for vehicle F-123",
            "Reserve vehicle V-456 for tomorrow",
            "Add new Toyota Camry to fleet",
            "Check status of vehicle T-789",
            "Cancel reservation for Friday"
        ] * 20  # 100 total tests
        
        response_times = []
        
        for text in test_texts:
            start_time = time.perf_counter()
            
            result = await classifier.classify_intent(text)
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            response_times.append(response_time)
            
            assert result["confidence"] >= 0.8
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        p99_response_time = statistics.quantiles(response_times, n=100)[98]  # 99th percentile
        
        # Performance assertions
        assert avg_response_time < 100, f"Average response time {avg_response_time:.2f}ms exceeds 100ms"
        assert p95_response_time < 200, f"95th percentile {p95_response_time:.2f}ms exceeds 200ms"
        assert p99_response_time < 500, f"99th percentile {p99_response_time:.2f}ms exceeds 500ms"
        
        print(f"\nIntent Classification Performance:")
        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"95th percentile: {p95_response_time:.2f}ms")
        print(f"99th percentile: {p99_response_time:.2f}ms")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_entity_extraction_throughput(self, performance_nlp_components):
        """Benchmark entity extraction throughput"""
        extractor = performance_nlp_components["entity_extractor"]
        
        # Generate test data
        test_texts = [
            f"Schedule maintenance for vehicle F-{i:03d} on {date} at {time}"
            for i in range(1, 101)
            for date in ["tomorrow", "next Monday", "2024-03-20"]
            for time in ["10:00 AM", "2:30 PM", "9:00 AM"]
        ][:500]  # 500 test cases
        
        start_time = time.perf_counter()
        
        # Process in batches for throughput testing
        batch_size = 50
        total_processed = 0
        
        for i in range(0, len(test_texts), batch_size):
            batch = test_texts[i:i+batch_size]
            
            # Process batch concurrently
            tasks = [
                extractor.extract_entities(text, intent="maintenance_scheduling")
                for text in batch
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify results
            for result in results:
                assert "entities" in result
                assert result["confidence"] > 0.5
            
            total_processed += len(results)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        throughput = total_processed / total_time  # Extractions per second
        
        # Performance assertion
        assert throughput >= 20, f"Throughput {throughput:.1f} extractions/sec is below minimum 20/sec"
        
        print(f"\nEntity Extraction Throughput:")
        print(f"Processed: {total_processed} extractions")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Throughput: {throughput:.1f} extractions/sec")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_reasoning_engine_memory_usage(self, performance_nlp_components):
        """Benchmark reasoning engine memory usage"""
        reasoning_engine = performance_nlp_components["reasoning_engine"]
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Create test interpretations
        interpretations = []
        for i in range(100):
            interpretation = Mock()
            interpretation.intent = "maintenance_scheduling"
            interpretation.entities = {
                "vehicle_id": f"F-{i:03d}",
                "date": "tomorrow",
                "action": "maintenance"
            }
            interpretation.confidence = 0.85
            interpretation.text = f"Schedule maintenance for vehicle F-{i:03d}"
            interpretations.append(interpretation)
        
        # Process all interpretations
        reasoning_results = []
        for interpretation in interpretations:
            result = await reasoning_engine.reason_about_interpretation(interpretation)
            reasoning_results.append(result)
        
        # Check memory usage
        peak_memory = process.memory_info().rss
        memory_increase = peak_memory - initial_memory
        memory_increase_mb = memory_increase / (1024 * 1024)
        
        # Memory per reasoning operation
        memory_per_operation = memory_increase / len(interpretations)
        memory_per_operation_kb = memory_per_operation / 1024
        
        # Performance assertions
        assert memory_increase_mb < 100, f"Memory increase {memory_increase_mb:.1f}MB exceeds 100MB limit"
        assert memory_per_operation_kb < 50, f"Memory per operation {memory_per_operation_kb:.1f}KB exceeds 50KB"
        
        print(f"\nReasoning Engine Memory Usage:")
        print(f"Initial memory: {initial_memory / (1024*1024):.1f}MB")
        print(f"Peak memory: {peak_memory / (1024*1024):.1f}MB")
        print(f"Memory increase: {memory_increase_mb:.1f}MB")
        print(f"Memory per operation: {memory_per_operation_kb:.1f}KB")
        
        # Cleanup
        del reasoning_results
        del interpretations
        gc.collect()

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_nlp_processing(self, performance_nlp_components):
        """Benchmark concurrent NLP processing performance"""
        components = performance_nlp_components
        
        async def process_complete_pipeline(text, user_id):
            """Process text through complete NLP pipeline"""
            # Intent classification
            intent_result = await components["intent_classifier"].classify_intent(text)
            
            # Entity extraction
            entity_result = await components["entity_extractor"].extract_entities(
                text, intent=intent_result["intent"]
            )
            
            # Reasoning
            interpretation = Mock()
            interpretation.intent = intent_result["intent"]
            interpretation.entities = entity_result["entities"]
            interpretation.confidence = min(
                intent_result["confidence"], 
                entity_result["confidence"]
            )
            interpretation.text = text
            
            reasoning_result = await components["reasoning_engine"].reason_about_interpretation(interpretation)
            
            return {
                "user_id": user_id,
                "intent": intent_result,
                "entities": entity_result,
                "reasoning": reasoning_result
            }
        
        # Generate concurrent requests
        concurrent_requests = [
            (f"Schedule maintenance for vehicle F-{i:03d}", f"user{i}@company.com")
            for i in range(50)
        ]
        
        start_time = time.perf_counter()
        
        # Process all requests concurrently
        tasks = [
            process_complete_pipeline(text, user_id)
            for text, user_id in concurrent_requests
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Verify all results
        assert len(results) == 50
        for result in results:
            assert result["intent"]["confidence"] >= 0.8
            assert result["entities"]["confidence"] >= 0.8
            assert result["reasoning"].confidence >= 0.8
        
        # Calculate performance metrics
        requests_per_second = len(results) / total_time
        avg_time_per_request = total_time / len(results) * 1000  # milliseconds
        
        # Performance assertions
        assert requests_per_second >= 10, f"Throughput {requests_per_second:.1f} req/sec below minimum 10/sec"
        assert avg_time_per_request <= 1000, f"Average time {avg_time_per_request:.0f}ms exceeds 1000ms"
        
        print(f"\nConcurrent NLP Processing Performance:")
        print(f"Concurrent requests: {len(results)}")
        print(f"Total time: {total_time:.2f} seconds")
        print(f"Requests per second: {requests_per_second:.1f}")
        print(f"Average time per request: {avg_time_per_request:.0f}ms")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_nlp_component_scalability(self, performance_nlp_components):
        """Test NLP component performance under increasing load"""
        components = performance_nlp_components
        
        load_levels = [10, 25, 50, 100, 200]  # Number of concurrent requests
        performance_results = {}
        
        for load_level in load_levels:
            print(f"\nTesting load level: {load_level} concurrent requests")
            
            # Generate requests for this load level
            requests = [
                f"Process request {i} for vehicle F-{i%20:02d}"
                for i in range(load_level)
            ]
            
            start_time = time.perf_counter()
            
            # Process intent classification concurrently
            classification_tasks = [
                components["intent_classifier"].classify_intent(request)
                for request in requests
            ]
            
            classification_results = await asyncio.gather(*classification_tasks)
            
            end_time = time.perf_counter()
            
            # Calculate metrics
            total_time = end_time - start_time
            throughput = load_level / total_time
            avg_response_time = total_time / load_level * 1000
            
            performance_results[load_level] = {
                "total_time": total_time,
                "throughput": throughput,
                "avg_response_time": avg_response_time
            }
            
            print(f"Throughput: {throughput:.1f} req/sec")
            print(f"Average response time: {avg_response_time:.1f}ms")
            
            # Verify quality doesn't degrade under load
            successful_results = [r for r in classification_results if r["confidence"] >= 0.8]
            success_rate = len(successful_results) / len(classification_results)
            
            assert success_rate >= 0.95, f"Success rate {success_rate:.2f} below 95% at load {load_level}"
        
        # Verify performance doesn't degrade significantly with load
        baseline_throughput = performance_results[10]["throughput"]
        high_load_throughput = performance_results[200]["throughput"]
        
        throughput_retention = high_load_throughput / baseline_throughput
        
        assert throughput_retention >= 0.7, f"Throughput retention {throughput_retention:.2f} below 70%"
        
        print(f"\nScalability Summary:")
        for load_level, metrics in performance_results.items():
            print(f"Load {load_level}: {metrics['throughput']:.1f} req/sec, {metrics['avg_response_time']:.1f}ms avg")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_nlp_cache_performance(self, performance_nlp_components):
        """Benchmark performance improvement from caching"""
        classifier = performance_nlp_components["intent_classifier"]
        
        # Enable caching if available
        if hasattr(classifier, 'enable_caching'):
            classifier.enable_caching = True
        
        # Test texts (some repeated for cache hits)
        test_texts = [
            "Schedule maintenance for vehicle F-123",
            "Reserve vehicle V-456 for tomorrow", 
            "Schedule maintenance for vehicle F-123",  # Repeat
            "Add new Toyota Camry to fleet",
            "Reserve vehicle V-456 for tomorrow",  # Repeat
            "Schedule maintenance for vehicle F-123",  # Repeat
        ] * 20  # Multiple iterations
        
        # First pass - populate cache and measure
        first_pass_times = []
        
        for text in test_texts:
            start_time = time.perf_counter()
            await classifier.classify_intent(text)
            end_time = time.perf_counter()
            
            first_pass_times.append((end_time - start_time) * 1000)
        
        # Second pass - should benefit from caching
        second_pass_times = []
        
        for text in test_texts:
            start_time = time.perf_counter()
            await classifier.classify_intent(text)
            end_time = time.perf_counter()
            
            second_pass_times.append((end_time - start_time) * 1000)
        
        # Calculate improvement
        avg_first_pass = statistics.mean(first_pass_times)
        avg_second_pass = statistics.mean(second_pass_times)
        
        # Cache should improve performance for repeated requests
        if hasattr(classifier, 'cache_hit_rate'):
            cache_hit_rate = getattr(classifier, 'cache_hit_rate', 0)
            if cache_hit_rate > 0:
                improvement_ratio = avg_first_pass / avg_second_pass
                assert improvement_ratio >= 1.2, f"Cache improvement {improvement_ratio:.2f}x below 1.2x minimum"
        
        print(f"\nCaching Performance:")
        print(f"First pass average: {avg_first_pass:.2f}ms")
        print(f"Second pass average: {avg_second_pass:.2f}ms")
        if hasattr(classifier, 'cache_hit_rate'):
            print(f"Cache hit rate: {getattr(classifier, 'cache_hit_rate', 0):.1%}")

    @pytest.mark.performance
    def test_nlp_component_initialization_time(self, fast_mock_llm):
        """Benchmark component initialization performance"""
        initialization_times = {}
        
        # Test IntentClassifier initialization
        start_time = time.perf_counter()
        intent_classifier = IntentClassifier(llm_manager=fast_mock_llm)
        end_time = time.perf_counter()
        initialization_times["IntentClassifier"] = (end_time - start_time) * 1000
        
        # Test EntityExtractor initialization
        start_time = time.perf_counter()
        entity_extractor = EntityExtractor(llm_manager=fast_mock_llm)
        end_time = time.perf_counter()
        initialization_times["EntityExtractor"] = (end_time - start_time) * 1000
        
        # Test ReasoningEngine initialization
        start_time = time.perf_counter()
        reasoning_engine = ReasoningEngine(llm_manager=fast_mock_llm)
        end_time = time.perf_counter()
        initialization_times["ReasoningEngine"] = (end_time - start_time) * 1000
        
        # Performance assertions
        for component_name, init_time in initialization_times.items():
            assert init_time < 100, f"{component_name} initialization {init_time:.1f}ms exceeds 100ms"
        
        print(f"\nComponent Initialization Times:")
        for component_name, init_time in initialization_times.items():
            print(f"{component_name}: {init_time:.1f}ms")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_error_handling_performance_impact(self, performance_nlp_components):
        """Benchmark performance impact of error handling"""
        classifier = performance_nlp_components["intent_classifier"]
        
        # Normal processing baseline
        normal_requests = ["Schedule maintenance for F-123"] * 50
        
        start_time = time.perf_counter()
        normal_results = await asyncio.gather(*[
            classifier.classify_intent(text) for text in normal_requests
        ])
        normal_time = time.perf_counter() - start_time
        
        # Mixed normal and error requests
        mixed_requests = ["Schedule maintenance for F-123"] * 25 + [None] * 25  # None will cause errors
        
        start_time = time.perf_counter()
        mixed_results = await asyncio.gather(*[
            classifier.classify_intent(text) if text else asyncio.coroutine(lambda: {"error": "null_input"})()
            for text in mixed_requests
        ], return_exceptions=True)
        mixed_time = time.perf_counter() - start_time
        
        # Calculate performance impact
        performance_impact = (mixed_time - normal_time) / normal_time
        
        # Error handling shouldn't significantly impact performance
        assert performance_impact < 0.5, f"Error handling impact {performance_impact:.2f} exceeds 50%"
        
        print(f"\nError Handling Performance Impact:")
        print(f"Normal processing time: {normal_time:.3f}s")
        print(f"Mixed processing time: {mixed_time:.3f}s")
        print(f"Performance impact: {performance_impact:.1%}")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_nlp_warmup_performance(self, performance_nlp_components):
        """Test NLP component warm-up performance characteristics"""
        components = performance_nlp_components
        
        # Cold start performance
        cold_start_times = []
        for i in range(5):  # First 5 requests (cold start)
            start_time = time.perf_counter()
            await components["intent_classifier"].classify_intent(f"Test request {i}")
            end_time = time.perf_counter()
            cold_start_times.append((end_time - start_time) * 1000)
        
        # Warmed up performance
        warm_times = []
        for i in range(20):  # Next 20 requests (warmed up)
            start_time = time.perf_counter()
            await components["intent_classifier"].classify_intent(f"Warm request {i}")
            end_time = time.perf_counter()
            warm_times.append((end_time - start_time) * 1000)
        
        # Calculate warm-up improvement
        avg_cold_start = statistics.mean(cold_start_times)
        avg_warm = statistics.mean(warm_times)
        warmup_improvement = avg_cold_start / avg_warm
        
        print(f"\nWarm-up Performance:")
        print(f"Cold start average: {avg_cold_start:.2f}ms")
        print(f"Warmed up average: {avg_warm:.2f}ms")
        print(f"Warm-up improvement: {warmup_improvement:.2f}x")
        
        # Warm-up should improve performance
        if warmup_improvement > 1.1:
            print("Warm-up effect detected and beneficial")
        else:
            print("Minimal warm-up effect (consistently fast)")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_batch_vs_individual_processing_performance(self, performance_nlp_components):
        """Compare batch vs individual processing performance"""
        classifier = performance_nlp_components["intent_classifier"]
        
        test_texts = [f"Schedule maintenance for vehicle F-{i:03d}" for i in range(100)]
        
        # Individual processing
        start_time = time.perf_counter()
        individual_results = []
        for text in test_texts:
            result = await classifier.classify_intent(text)
            individual_results.append(result)
        individual_time = time.perf_counter() - start_time
        
        # Batch processing (if available)
        if hasattr(classifier, 'batch_classify'):
            start_time = time.perf_counter()
            batch_results = await classifier.batch_classify(test_texts)
            batch_time = time.perf_counter() - start_time
            
            # Calculate efficiency gain
            efficiency_gain = individual_time / batch_time
            
            print(f"\nBatch vs Individual Processing:")
            print(f"Individual processing: {individual_time:.3f}s")
            print(f"Batch processing: {batch_time:.3f}s")
            print(f"Efficiency gain: {efficiency_gain:.2f}x")
            
            # Batch processing should be more efficient
            assert efficiency_gain >= 1.5, f"Batch efficiency gain {efficiency_gain:.2f}x below 1.5x minimum"
        else:
            print(f"\nIndividual Processing Time: {individual_time:.3f}s")
            print("Batch processing not available for this component")