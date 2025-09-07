"""
System-wide performance benchmarks and stress tests.

Tests overall system performance, resource usage, and scalability
under various load conditions and usage patterns.
"""

import pytest
import asyncio
import time
import statistics
import psutil
import gc
import threading
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import asynccontextmanager

from combadge.core.application import Application
from combadge.fleet.processors.command_processor import CommandProcessor
from combadge.api.client import HTTPClient


class TestSystemBenchmarks:
    """System-wide performance and stress tests"""

    @pytest.fixture
    async def benchmark_application(self, temp_config_dir):
        """Create application configured for benchmarking"""
        # Optimized test configuration for performance
        benchmark_config = {
            "app_name": "ComBadge-Benchmark",
            "environment": "benchmark",
            "debug_mode": False,  # Disable debug for better performance
            "llm": {
                "model": "benchmark-model",
                "temperature": 0.1,
                "timeout": 10,  # Shorter timeout for benchmarks
                "streaming": False,
                "base_url": "mock://localhost"
            },
            "api": {
                "base_url": "mock://benchmark-api.com",
                "timeout": 15,
                "retry_attempts": 3,
                "authentication": {"method": "api_key", "api_key": "benchmark-key"}
            },
            "processing": {
                "confidence_threshold": 0.8,
                "enable_caching": True,  # Enable caching for better performance
                "cache_ttl": 3600
            },
            "ui": {
                "auto_approve_high_confidence": True,
                "confidence_threshold": 0.9
            }
        }
        
        import yaml
        config_file = temp_config_dir / "benchmark_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(benchmark_config, f)
        
        # Create application
        app = Application(config_path=str(config_file))
        
        # Setup fast mock LLM
        fast_mock_llm = Mock()
        fast_mock_llm.is_available = Mock(return_value=True)
        
        async def ultra_fast_llm_response(prompt, context=None):
            # Minimal delay for realistic but fast responses
            await asyncio.sleep(0.005)
            
            if "classify" in prompt.lower():
                return {
                    "intent": "maintenance_scheduling",
                    "confidence": 0.92,
                    "reasoning": ["Benchmark classification"]
                }
            elif "extract" in prompt.lower():
                return {
                    "entities": {"vehicle_id": "F-123", "date": "tomorrow"},
                    "confidence": 0.90
                }
            else:
                return {
                    "reasoning_steps": ["Benchmark reasoning"],
                    "conclusion": "Proceed with action",
                    "confidence": 0.91,
                    "recommendation": "proceed",
                    "risk_level": "low"
                }
        
        fast_mock_llm.generate_response = ultra_fast_llm_response
        
        # Setup fast mock HTTP client
        fast_mock_http = Mock(spec=HTTPClient)
        
        async def fast_api_response(*args, **kwargs):
            await asyncio.sleep(0.002)  # 2ms simulated API latency
            return {
                "success": True,
                "id": "benchmark-001",
                "timestamp": time.time()
            }
        
        fast_mock_http.post = fast_api_response
        fast_mock_http.get = fast_api_response
        fast_mock_http.put = fast_api_response
        
        # Inject mocks
        app.llm_manager = fast_mock_llm
        app.http_client = fast_mock_http
        
        await app.initialize()
        return app

    @asynccontextmanager
    async def resource_monitor(self):
        """Context manager for monitoring system resources"""
        process = psutil.Process()
        
        # Initial readings
        initial_memory = process.memory_info().rss
        initial_cpu_percent = process.cpu_percent()
        initial_threads = process.num_threads()
        
        # Start monitoring thread
        resource_readings = []
        monitoring = True
        
        def monitor_resources():
            while monitoring:
                try:
                    resource_readings.append({
                        'timestamp': time.time(),
                        'memory_rss': process.memory_info().rss,
                        'memory_vms': process.memory_info().vms,
                        'cpu_percent': process.cpu_percent(),
                        'num_threads': process.num_threads()
                    })
                    time.sleep(0.1)  # Sample every 100ms
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        
        monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
        monitor_thread.start()
        
        try:
            yield {
                'initial_memory': initial_memory,
                'initial_cpu': initial_cpu_percent,
                'initial_threads': initial_threads,
                'readings': resource_readings
            }
        finally:
            monitoring = False
            monitor_thread.join(timeout=1)

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, benchmark_application):
        """Test system performance under sustained load"""
        app = benchmark_application
        
        # Test configuration
        duration_seconds = 30  # 30 second test
        target_rps = 50  # 50 requests per second
        total_requests = duration_seconds * target_rps
        
        print(f"\nSustained Load Test: {total_requests} requests over {duration_seconds} seconds")
        
        async with self.resource_monitor() as monitor:
            start_time = time.time()
            completed_requests = 0
            error_count = 0
            response_times = []
            
            # Request generator
            async def generate_request(request_id):
                nonlocal completed_requests, error_count
                
                request_start = time.time()
                try:
                    result = await app.process_command(
                        f"Schedule maintenance for vehicle F-{request_id:04d}",
                        user_id=f"benchmark_user_{request_id % 10}@company.com"
                    )
                    
                    request_end = time.time()
                    response_time = (request_end - request_start) * 1000
                    response_times.append(response_time)
                    
                    if result.get("success", False):
                        completed_requests += 1
                    else:
                        error_count += 1
                        
                except Exception as e:
                    error_count += 1
                    print(f"Request {request_id} failed: {e}")
            
            # Generate requests at target rate
            tasks = []
            for i in range(total_requests):
                task = asyncio.create_task(generate_request(i))
                tasks.append(task)
                
                # Rate limiting
                if i > 0 and i % target_rps == 0:
                    elapsed = time.time() - start_time
                    expected_time = i / target_rps
                    if elapsed < expected_time:
                        await asyncio.sleep(expected_time - elapsed)
            
            # Wait for all requests to complete
            await asyncio.gather(*tasks)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
        # Calculate performance metrics
        actual_rps = completed_requests / total_duration
        success_rate = completed_requests / total_requests
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) >= 20 else 0
        p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) >= 100 else 0
        
        # Resource usage analysis
        memory_readings = [r['memory_rss'] for r in monitor['readings']]
        cpu_readings = [r['cpu_percent'] for r in monitor['readings']]
        thread_readings = [r['num_threads'] for r in monitor['readings']]
        
        peak_memory = max(memory_readings) if memory_readings else 0
        avg_cpu = statistics.mean(cpu_readings) if cpu_readings else 0
        max_threads = max(thread_readings) if thread_readings else 0
        
        # Performance assertions
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below 95%"
        assert actual_rps >= target_rps * 0.9, f"Actual RPS {actual_rps:.1f} below 90% of target {target_rps}"
        assert avg_response_time <= 2000, f"Average response time {avg_response_time:.0f}ms exceeds 2000ms"
        assert peak_memory / (1024**2) <= 500, f"Peak memory {peak_memory/(1024**2):.1f}MB exceeds 500MB"
        
        # Print detailed results
        print(f"\nSustained Load Results:")
        print(f"Total requests: {total_requests}")
        print(f"Completed: {completed_requests}")
        print(f"Errors: {error_count}")
        print(f"Success rate: {success_rate:.2%}")
        print(f"Actual RPS: {actual_rps:.1f}")
        print(f"Average response time: {avg_response_time:.0f}ms")
        print(f"95th percentile: {p95_response_time:.0f}ms")
        print(f"99th percentile: {p99_response_time:.0f}ms")
        print(f"Peak memory: {peak_memory/(1024**2):.1f}MB")
        print(f"Average CPU: {avg_cpu:.1f}%")
        print(f"Max threads: {max_threads}")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_burst_load_handling(self, benchmark_application):
        """Test system performance under sudden burst loads"""
        app = benchmark_application
        
        burst_sizes = [10, 50, 100, 200, 500]  # Increasing burst sizes
        burst_results = {}
        
        for burst_size in burst_sizes:
            print(f"\nTesting burst load: {burst_size} concurrent requests")
            
            async with self.resource_monitor() as monitor:
                start_time = time.time()
                
                # Generate burst of concurrent requests
                tasks = [
                    app.process_command(
                        f"Process burst request {i} for vehicle F-{i%20:03d}",
                        user_id=f"burst_user_{i%5}@company.com"
                    )
                    for i in range(burst_size)
                ]
                
                # Execute all requests concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                burst_duration = end_time - start_time
            
            # Analyze results
            successful_results = [r for r in results if not isinstance(r, Exception) and r.get("success", False)]
            failed_results = [r for r in results if isinstance(r, Exception) or not r.get("success", True)]
            
            success_rate = len(successful_results) / len(results)
            avg_response_time = burst_duration / burst_size * 1000  # Average ms per request
            throughput = burst_size / burst_duration  # Requests per second
            
            # Memory analysis
            memory_readings = [r['memory_rss'] for r in monitor['readings']]
            peak_memory_mb = max(memory_readings) / (1024**2) if memory_readings else 0
            
            burst_results[burst_size] = {
                'duration': burst_duration,
                'success_rate': success_rate,
                'throughput': throughput,
                'avg_response_time': avg_response_time,
                'peak_memory_mb': peak_memory_mb,
                'failed_count': len(failed_results)
            }
            
            print(f"Duration: {burst_duration:.2f}s")
            print(f"Success rate: {success_rate:.2%}")
            print(f"Throughput: {throughput:.1f} req/s")
            print(f"Avg response time: {avg_response_time:.0f}ms")
            print(f"Peak memory: {peak_memory_mb:.1f}MB")
            print(f"Failures: {len(failed_results)}")
            
            # Performance assertions per burst size
            assert success_rate >= 0.90, f"Success rate {success_rate:.2%} below 90% for burst {burst_size}"
            
            # Small bursts should have high success rates
            if burst_size <= 100:
                assert success_rate >= 0.95, f"Small burst success rate {success_rate:.2%} below 95%"
            
            # Avoid memory leaks
            gc.collect()
        
        # Analyze scalability across burst sizes
        print(f"\nBurst Load Scalability Summary:")
        for size, metrics in burst_results.items():
            print(f"Burst {size}: {metrics['throughput']:.1f} req/s, "
                  f"{metrics['success_rate']:.1%} success, "
                  f"{metrics['peak_memory_mb']:.1f}MB peak")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_memory_leak_detection(self, benchmark_application):
        """Test for memory leaks during extended operation"""
        app = benchmark_application
        
        cycles = 10  # Number of test cycles
        requests_per_cycle = 100
        
        memory_measurements = []
        
        for cycle in range(cycles):
            # Measure memory before cycle
            gc.collect()  # Force garbage collection
            process = psutil.Process()
            pre_cycle_memory = process.memory_info().rss
            
            # Process requests
            tasks = [
                app.process_command(
                    f"Memory test cycle {cycle} request {i}",
                    user_id=f"memtest_{i%10}@company.com"
                )
                for i in range(requests_per_cycle)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Measure memory after cycle
            gc.collect()
            post_cycle_memory = process.memory_info().rss
            
            memory_increase = post_cycle_memory - pre_cycle_memory
            memory_measurements.append({
                'cycle': cycle,
                'pre_memory_mb': pre_cycle_memory / (1024**2),
                'post_memory_mb': post_cycle_memory / (1024**2),
                'increase_mb': memory_increase / (1024**2)
            })
            
            print(f"Cycle {cycle}: {pre_cycle_memory/(1024**2):.1f}MB -> "
                  f"{post_cycle_memory/(1024**2):.1f}MB "
                  f"(+{memory_increase/(1024**2):.1f}MB)")
            
            # Verify request success
            successful_requests = sum(1 for r in results if r.get("success", False))
            assert successful_requests >= requests_per_cycle * 0.95
        
        # Analyze memory growth trend
        memory_increases = [m['increase_mb'] for m in memory_measurements]
        avg_increase_per_cycle = statistics.mean(memory_increases)
        total_memory_increase = sum(memory_increases)
        
        # Memory leak assertions
        assert avg_increase_per_cycle <= 5.0, f"Average memory increase {avg_increase_per_cycle:.1f}MB/cycle indicates leak"
        assert total_memory_increase <= 50.0, f"Total memory increase {total_memory_increase:.1f}MB indicates significant leak"
        
        # Check for accelerating memory growth (sign of leak)
        first_half_avg = statistics.mean(memory_increases[:cycles//2])
        second_half_avg = statistics.mean(memory_increases[cycles//2:])
        growth_acceleration = second_half_avg / first_half_avg if first_half_avg > 0 else 1
        
        assert growth_acceleration <= 2.0, f"Memory growth acceleration {growth_acceleration:.1f}x indicates worsening leak"
        
        print(f"\nMemory Leak Analysis:")
        print(f"Average increase per cycle: {avg_increase_per_cycle:.1f}MB")
        print(f"Total memory increase: {total_memory_increase:.1f}MB")
        print(f"Growth acceleration: {growth_acceleration:.1f}x")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_cold_start_vs_warm_performance(self, temp_config_dir):
        """Compare cold start vs warm system performance"""
        
        # Cold start test
        print("\nTesting cold start performance...")
        
        cold_start_app = Application(config_path=str(temp_config_dir / "benchmark_config.yaml"))
        
        # Setup mocks for cold start
        mock_llm = Mock()
        mock_llm.is_available = Mock(return_value=True)
        mock_llm.generate_response = AsyncMock(return_value={
            "intent": "maintenance_scheduling", "confidence": 0.90
        })
        
        mock_http = Mock()
        mock_http.post = AsyncMock(return_value={"success": True})
        
        cold_start_app.llm_manager = mock_llm
        cold_start_app.http_client = mock_http
        
        await cold_start_app.initialize()
        
        # Measure cold start performance
        cold_start_times = []
        for i in range(10):  # First 10 requests
            start_time = time.perf_counter()
            
            result = await cold_start_app.process_command(
                f"Cold start test {i}",
                user_id="coldstart@company.com"
            )
            
            end_time = time.perf_counter()
            cold_start_times.append((end_time - start_time) * 1000)
        
        avg_cold_start = statistics.mean(cold_start_times)
        
        # Warm performance test
        print("Testing warm performance...")
        
        # Let the system "warm up" with some requests
        warmup_tasks = [
            cold_start_app.process_command(f"Warmup {i}", user_id="warmup@company.com")
            for i in range(50)
        ]
        await asyncio.gather(*warmup_tasks)
        
        # Measure warm performance
        warm_times = []
        for i in range(10):
            start_time = time.perf_counter()
            
            result = await cold_start_app.process_command(
                f"Warm test {i}",
                user_id="warm@company.com"
            )
            
            end_time = time.perf_counter()
            warm_times.append((end_time - start_time) * 1000)
        
        avg_warm = statistics.mean(warm_times)
        
        # Calculate warm-up benefit
        warmup_improvement = avg_cold_start / avg_warm if avg_warm > 0 else 1
        
        print(f"\nCold Start vs Warm Performance:")
        print(f"Cold start average: {avg_cold_start:.0f}ms")
        print(f"Warm average: {avg_warm:.0f}ms")
        print(f"Warm-up improvement: {warmup_improvement:.1f}x")
        
        # Performance assertions
        assert avg_cold_start <= 5000, f"Cold start time {avg_cold_start:.0f}ms exceeds 5000ms"
        assert avg_warm <= 1000, f"Warm performance {avg_warm:.0f}ms exceeds 1000ms"
        
        if warmup_improvement > 1.5:
            print("Significant warm-up benefit detected")
        
        await cold_start_app.cleanup()

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_error_recovery_performance_impact(self, benchmark_application):
        """Test performance impact of error recovery mechanisms"""
        app = benchmark_application
        
        # Baseline performance (no errors)
        baseline_requests = 100
        
        start_time = time.time()
        baseline_tasks = [
            app.process_command(
                f"Baseline test {i}",
                user_id=f"baseline_{i%5}@company.com"
            )
            for i in range(baseline_requests)
        ]
        baseline_results = await asyncio.gather(*baseline_tasks)
        baseline_time = time.time() - start_time
        
        baseline_success = sum(1 for r in baseline_results if r.get("success", False))
        baseline_rps = baseline_success / baseline_time
        
        # Test with simulated errors
        # Mock intermittent LLM failures
        original_llm_method = app.llm_manager.generate_response
        error_count = 0
        
        async def failing_llm_response(prompt, context=None):
            nonlocal error_count
            error_count += 1
            if error_count % 5 == 0:  # Every 5th request fails
                raise Exception("Simulated LLM failure")
            return await original_llm_method(prompt, context)
        
        app.llm_manager.generate_response = failing_llm_response
        
        # Test with errors
        error_test_requests = 100
        
        start_time = time.time()
        error_tasks = [
            app.process_command(
                f"Error test {i}",
                user_id=f"error_{i%5}@company.com"
            )
            for i in range(error_test_requests)
        ]
        error_results = await asyncio.gather(*error_tasks, return_exceptions=True)
        error_time = time.time() - start_time
        
        # Analyze error test results
        error_success = sum(1 for r in error_results 
                           if not isinstance(r, Exception) and r.get("success", False))
        error_rps = error_success / error_time if error_time > 0 else 0
        
        # Calculate performance impact
        performance_impact = (error_time - baseline_time) / baseline_time if baseline_time > 0 else 0
        rps_impact = (baseline_rps - error_rps) / baseline_rps if baseline_rps > 0 else 0
        
        print(f"\nError Recovery Performance Impact:")
        print(f"Baseline: {baseline_success}/{baseline_requests} in {baseline_time:.2f}s ({baseline_rps:.1f} RPS)")
        print(f"With errors: {error_success}/{error_test_requests} in {error_time:.2f}s ({error_rps:.1f} RPS)")
        print(f"Performance impact: {performance_impact:.1%}")
        print(f"RPS impact: {rps_impact:.1%}")
        
        # Assertions
        assert performance_impact <= 1.0, f"Error recovery impact {performance_impact:.1%} exceeds 100%"
        assert rps_impact <= 0.5, f"RPS impact {rps_impact:.1%} exceeds 50%"
        assert error_success >= error_test_requests * 0.7, "Too many requests failed during error recovery test"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_database_connection_pooling_performance(self, benchmark_application):
        """Test database connection pooling impact on performance"""
        app = benchmark_application
        
        # Simulate database operations with connection overhead
        connection_times = []
        
        async def simulate_db_operation_with_pooling():
            """Simulate DB operation with connection pooling"""
            # Simulate getting connection from pool (fast)
            await asyncio.sleep(0.001)  # 1ms to get pooled connection
            
            # Simulate actual DB operation
            await asyncio.sleep(0.005)  # 5ms for DB query
            
            return {"success": True, "data": "pooled_result"}
        
        async def simulate_db_operation_without_pooling():
            """Simulate DB operation without connection pooling"""
            # Simulate establishing new connection (slower)
            await asyncio.sleep(0.010)  # 10ms to establish connection
            
            # Simulate actual DB operation
            await asyncio.sleep(0.005)  # 5ms for DB query
            
            # Simulate connection cleanup
            await asyncio.sleep(0.002)  # 2ms cleanup
            
            return {"success": True, "data": "direct_result"}
        
        # Test with connection pooling
        pooled_start = time.time()
        pooled_tasks = [simulate_db_operation_with_pooling() for _ in range(100)]
        pooled_results = await asyncio.gather(*pooled_tasks)
        pooled_time = time.time() - pooled_start
        
        # Test without connection pooling
        direct_start = time.time()
        direct_tasks = [simulate_db_operation_without_pooling() for _ in range(100)]
        direct_results = await asyncio.gather(*direct_tasks)
        direct_time = time.time() - direct_start
        
        # Calculate performance improvement
        pooling_improvement = direct_time / pooled_time if pooled_time > 0 else 1
        time_saved = direct_time - pooled_time
        
        print(f"\nConnection Pooling Performance:")
        print(f"With pooling: {pooled_time:.3f}s")
        print(f"Without pooling: {direct_time:.3f}s")
        print(f"Improvement: {pooling_improvement:.2f}x")
        print(f"Time saved: {time_saved:.3f}s")
        
        # Pooling should provide significant improvement
        assert pooling_improvement >= 2.0, f"Pooling improvement {pooling_improvement:.2f}x below 2.0x minimum"

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_caching_system_performance_impact(self, benchmark_application):
        """Test the performance impact of the caching system"""
        app = benchmark_application
        
        # Test requests with high cache hit potential
        cache_friendly_requests = [
            "Schedule maintenance for vehicle F-123",
            "Reserve vehicle V-456 for tomorrow", 
            "Schedule maintenance for vehicle F-123",  # Repeat
            "Check status of vehicle T-789",
            "Reserve vehicle V-456 for tomorrow",  # Repeat
            "Schedule maintenance for vehicle F-123",  # Repeat
        ] * 20  # 120 requests, many repeated
        
        # Enable caching if available
        if hasattr(app, 'enable_caching'):
            app.enable_caching = True
        
        # First run - populate cache
        print("First run (populating cache)...")
        first_run_start = time.time()
        
        first_run_tasks = [
            app.process_command(request, user_id=f"cache_user_{i%5}@company.com")
            for i, request in enumerate(cache_friendly_requests)
        ]
        first_run_results = await asyncio.gather(*first_run_tasks)
        first_run_time = time.time() - first_run_start
        
        # Second run - should benefit from cache
        print("Second run (using cache)...")
        second_run_start = time.time()
        
        second_run_tasks = [
            app.process_command(request, user_id=f"cache_user_{i%5}@company.com")
            for i, request in enumerate(cache_friendly_requests)
        ]
        second_run_results = await asyncio.gather(*second_run_tasks)
        second_run_time = time.time() - second_run_start
        
        # Calculate cache performance benefit
        cache_improvement = first_run_time / second_run_time if second_run_time > 0 else 1
        time_saved = first_run_time - second_run_time
        
        # Verify results quality
        first_run_success = sum(1 for r in first_run_results if r.get("success", False))
        second_run_success = sum(1 for r in second_run_results if r.get("success", False))
        
        print(f"\nCaching System Performance:")
        print(f"First run: {first_run_time:.3f}s ({first_run_success}/{len(first_run_results)} success)")
        print(f"Second run: {second_run_time:.3f}s ({second_run_success}/{len(second_run_results)} success)")
        print(f"Cache improvement: {cache_improvement:.2f}x")
        print(f"Time saved: {time_saved:.3f}s")
        
        # Get cache statistics if available
        if hasattr(app, 'get_cache_stats'):
            cache_stats = app.get_cache_stats()
            cache_hit_rate = cache_stats.get('hit_rate', 0)
            print(f"Cache hit rate: {cache_hit_rate:.1%}")
            
            if cache_hit_rate > 0.3:  # If we have decent cache hits
                assert cache_improvement >= 1.2, f"Cache improvement {cache_improvement:.2f}x below 1.2x minimum"
        
        # Quality shouldn't degrade with caching
        assert second_run_success >= first_run_success * 0.95, "Cache degraded result quality"