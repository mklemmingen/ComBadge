"""
Load testing and stress testing for ComBadge system.

Tests system behavior under extreme load conditions, user simulation,
and resource exhaustion scenarios.
"""

import pytest
import asyncio
import time
import random
import statistics
import psutil
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import threading
from contextlib import asynccontextmanager

from combadge.core.application import Application


@dataclass
class LoadTestResult:
    """Results from a load test"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    error_requests: int
    total_duration: float
    average_response_time: float
    p95_response_time: float
    p99_response_time: float
    requests_per_second: float
    peak_memory_mb: float
    average_cpu_percent: float
    peak_threads: int
    success_rate: float
    errors: List[str]


class LoadTestScenario:
    """Defines a load testing scenario"""
    
    def __init__(self, name: str, duration: int, concurrent_users: int, 
                 requests_per_user: int, think_time_range: Tuple[float, float]):
        self.name = name
        self.duration = duration  # seconds
        self.concurrent_users = concurrent_users
        self.requests_per_user = requests_per_user
        self.think_time_range = think_time_range  # (min, max) seconds between requests


class TestLoadTesting:
    """Load testing and stress testing suite"""

    @pytest.fixture
    async def load_test_application(self, temp_config_dir):
        """Create application configured for load testing"""
        load_test_config = {
            "app_name": "ComBadge-LoadTest",
            "environment": "load_test",
            "debug_mode": False,
            "llm": {
                "model": "load-test-model",
                "temperature": 0.1,
                "timeout": 5,  # Short timeout for load testing
                "base_url": "mock://localhost"
            },
            "api": {
                "base_url": "mock://load-test-api.com",
                "timeout": 10,
                "retry_attempts": 2,  # Fewer retries for load testing
                "authentication": {"method": "api_key", "api_key": "load-test-key"}
            },
            "processing": {
                "confidence_threshold": 0.8,
                "enable_caching": True,
                "cache_ttl": 300  # 5 minute cache for load testing
            }
        }
        
        import yaml
        config_file = temp_config_dir / "load_test_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(load_test_config, f)
        
        # Create application
        app = Application(config_path=str(config_file))
        
        # Setup realistic but fast mocks
        mock_llm = Mock()
        mock_llm.is_available = Mock(return_value=True)
        
        async def load_test_llm_response(prompt, context=None):
            # Variable response time to simulate real LLM
            await asyncio.sleep(random.uniform(0.005, 0.020))
            
            # Occasional failures to test error handling
            if random.random() < 0.02:  # 2% failure rate
                raise Exception("Simulated LLM overload")
            
            return {
                "intent": random.choice(["maintenance_scheduling", "vehicle_reservation", "vehicle_operations"]),
                "confidence": random.uniform(0.8, 0.95),
                "entities": {"vehicle_id": f"F-{random.randint(100, 999)}", "date": "tomorrow"},
                "reasoning_steps": ["Load test reasoning"],
                "conclusion": "Load test conclusion",
                "recommendation": "proceed"
            }
        
        mock_llm.generate_response = load_test_llm_response
        
        # Setup realistic API mock
        mock_http = Mock()
        
        async def load_test_api_response(*args, **kwargs):
            # Variable API response time
            await asyncio.sleep(random.uniform(0.010, 0.050))
            
            # Occasional API failures
            if random.random() < 0.01:  # 1% API failure rate
                raise Exception("API server overloaded")
            
            return {
                "success": True,
                "id": f"load-test-{random.randint(1000, 9999)}",
                "timestamp": time.time()
            }
        
        mock_http.post = load_test_api_response
        mock_http.get = load_test_api_response
        
        app.llm_manager = mock_llm
        app.http_client = mock_http
        
        await app.initialize()
        return app

    @asynccontextmanager
    async def system_monitor(self):
        """Monitor system resources during load testing"""
        process = psutil.Process()
        
        # Initial state
        initial_memory = process.memory_info().rss
        initial_threads = process.num_threads()
        
        # Resource tracking
        resource_data = {
            'memory_samples': [],
            'cpu_samples': [],
            'thread_samples': [],
            'timestamps': [],
            'monitoring': True
        }
        
        def monitor_resources():
            while resource_data['monitoring']:
                try:
                    current_time = time.time()
                    memory_info = process.memory_info()
                    cpu_percent = process.cpu_percent()
                    num_threads = process.num_threads()
                    
                    resource_data['timestamps'].append(current_time)
                    resource_data['memory_samples'].append(memory_info.rss)
                    resource_data['cpu_samples'].append(cpu_percent)
                    resource_data['thread_samples'].append(num_threads)
                    
                    time.sleep(0.5)  # Sample every 500ms
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
        
        monitor_thread = threading.Thread(target=monitor_resources, daemon=True)
        monitor_thread.start()
        
        try:
            yield resource_data
        finally:
            resource_data['monitoring'] = False
            monitor_thread.join(timeout=2)

    async def run_load_test_scenario(self, app: Application, scenario: LoadTestScenario) -> LoadTestResult:
        """Execute a load testing scenario"""
        print(f"\nExecuting load test scenario: {scenario.name}")
        print(f"Duration: {scenario.duration}s, Users: {scenario.concurrent_users}, "
              f"Requests/User: {scenario.requests_per_user}")
        
        # Request templates for variety
        request_templates = [
            "Schedule maintenance for vehicle F-{:03d}",
            "Reserve vehicle V-{:03d} for tomorrow",
            "Check status of vehicle T-{:03d}",
            "Cancel reservation for vehicle F-{:03d}",
            "Add fuel record for vehicle V-{:03d}",
            "Update mileage for vehicle T-{:03d}",
            "Schedule inspection for vehicle F-{:03d}",
            "Reserve parking spot for vehicle V-{:03d}"
        ]
        
        async with self.system_monitor() as monitor:
            # Shared state for all users
            shared_state = {
                'completed_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'error_requests': 0,
                'response_times': [],
                'errors': [],
                'start_time': None,
                'lock': asyncio.Lock()
            }
            
            async def simulate_user(user_id: int):
                """Simulate a single user's behavior"""
                user_response_times = []
                user_errors = []
                
                for request_num in range(scenario.requests_per_user):
                    # Generate request
                    template = random.choice(request_templates)
                    vehicle_num = random.randint(100, 999)
                    command = template.format(vehicle_num)
                    
                    # Execute request
                    request_start = time.time()
                    try:
                        result = await app.process_command(
                            command,
                            user_id=f"load_user_{user_id}@company.com"
                        )
                        
                        request_end = time.time()
                        response_time = request_end - request_start
                        user_response_times.append(response_time)
                        
                        async with shared_state['lock']:
                            shared_state['completed_requests'] += 1
                            shared_state['response_times'].append(response_time * 1000)  # Convert to ms
                            
                            if result.get("success", False):
                                shared_state['successful_requests'] += 1
                            else:
                                shared_state['failed_requests'] += 1
                                
                    except Exception as e:
                        request_end = time.time()
                        error_msg = str(e)
                        user_errors.append(error_msg)
                        
                        async with shared_state['lock']:
                            shared_state['completed_requests'] += 1
                            shared_state['error_requests'] += 1
                            shared_state['errors'].append(error_msg)
                    
                    # Think time between requests
                    if request_num < scenario.requests_per_user - 1:
                        think_time = random.uniform(*scenario.think_time_range)
                        await asyncio.sleep(think_time)
                
                return user_response_times, user_errors
            
            # Start the load test
            shared_state['start_time'] = time.time()
            
            # Create tasks for all users
            user_tasks = [
                simulate_user(user_id) 
                for user_id in range(scenario.concurrent_users)
            ]
            
            # Execute all user simulations concurrently
            user_results = await asyncio.gather(*user_tasks, return_exceptions=True)
            
            end_time = time.time()
            total_duration = end_time - shared_state['start_time']
        
        # Process results
        successful_users = [r for r in user_results if not isinstance(r, Exception)]
        failed_users = [r for r in user_results if isinstance(r, Exception)]
        
        # Calculate performance metrics
        response_times = shared_state['response_times']
        avg_response_time = statistics.mean(response_times) if response_times else 0
        
        p95_response_time = 0
        p99_response_time = 0
        if len(response_times) >= 20:
            p95_response_time = statistics.quantiles(response_times, n=20)[18]
        if len(response_times) >= 100:
            p99_response_time = statistics.quantiles(response_times, n=100)[98]
        
        requests_per_second = shared_state['completed_requests'] / total_duration if total_duration > 0 else 0
        success_rate = shared_state['successful_requests'] / shared_state['completed_requests'] if shared_state['completed_requests'] > 0 else 0
        
        # Resource usage metrics
        peak_memory_mb = max(monitor['memory_samples']) / (1024**2) if monitor['memory_samples'] else 0
        avg_cpu_percent = statistics.mean(monitor['cpu_samples']) if monitor['cpu_samples'] else 0
        peak_threads = max(monitor['thread_samples']) if monitor['thread_samples'] else 0
        
        return LoadTestResult(
            total_requests=shared_state['completed_requests'],
            successful_requests=shared_state['successful_requests'],
            failed_requests=shared_state['failed_requests'],
            error_requests=shared_state['error_requests'],
            total_duration=total_duration,
            average_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            requests_per_second=requests_per_second,
            peak_memory_mb=peak_memory_mb,
            average_cpu_percent=avg_cpu_percent,
            peak_threads=peak_threads,
            success_rate=success_rate,
            errors=shared_state['errors']
        )

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_light_load_scenario(self, load_test_application):
        """Test system under light load conditions"""
        scenario = LoadTestScenario(
            name="Light Load",
            duration=30,
            concurrent_users=5,
            requests_per_user=10,
            think_time_range=(1.0, 3.0)
        )
        
        result = await self.run_load_test_scenario(load_test_application, scenario)
        
        # Light load assertions
        assert result.success_rate >= 0.98, f"Success rate {result.success_rate:.2%} below 98% for light load"
        assert result.average_response_time <= 500, f"Average response time {result.average_response_time:.0f}ms exceeds 500ms"
        assert result.peak_memory_mb <= 200, f"Peak memory {result.peak_memory_mb:.1f}MB exceeds 200MB"
        
        self.print_load_test_results(result)

    @pytest.mark.performance
    @pytest.mark.slow 
    @pytest.mark.asyncio
    async def test_moderate_load_scenario(self, load_test_application):
        """Test system under moderate load conditions"""
        scenario = LoadTestScenario(
            name="Moderate Load",
            duration=60,
            concurrent_users=20,
            requests_per_user=15,
            think_time_range=(0.5, 2.0)
        )
        
        result = await self.run_load_test_scenario(load_test_application, scenario)
        
        # Moderate load assertions
        assert result.success_rate >= 0.95, f"Success rate {result.success_rate:.2%} below 95% for moderate load"
        assert result.average_response_time <= 1000, f"Average response time {result.average_response_time:.0f}ms exceeds 1000ms"
        assert result.requests_per_second >= 15, f"RPS {result.requests_per_second:.1f} below 15 for moderate load"
        assert result.peak_memory_mb <= 400, f"Peak memory {result.peak_memory_mb:.1f}MB exceeds 400MB"
        
        self.print_load_test_results(result)

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_heavy_load_scenario(self, load_test_application):
        """Test system under heavy load conditions"""
        scenario = LoadTestScenario(
            name="Heavy Load",
            duration=90,
            concurrent_users=50,
            requests_per_user=20,
            think_time_range=(0.1, 1.0)
        )
        
        result = await self.run_load_test_scenario(load_test_application, scenario)
        
        # Heavy load assertions (more lenient)
        assert result.success_rate >= 0.90, f"Success rate {result.success_rate:.2%} below 90% for heavy load"
        assert result.average_response_time <= 2000, f"Average response time {result.average_response_time:.0f}ms exceeds 2000ms"
        assert result.requests_per_second >= 25, f"RPS {result.requests_per_second:.1f} below 25 for heavy load"
        assert result.peak_memory_mb <= 600, f"Peak memory {result.peak_memory_mb:.1f}MB exceeds 600MB"
        
        self.print_load_test_results(result)

    @pytest.mark.performance
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_stress_scenario(self, load_test_application):
        """Test system under stress conditions (near breaking point)"""
        scenario = LoadTestScenario(
            name="Stress Test",
            duration=120,
            concurrent_users=100,
            requests_per_user=25,
            think_time_range=(0.05, 0.5)
        )
        
        result = await self.run_load_test_scenario(load_test_application, scenario)
        
        # Stress test assertions (very lenient, just ensure it doesn't crash)
        assert result.success_rate >= 0.80, f"Success rate {result.success_rate:.2%} below 80% for stress test"
        assert result.average_response_time <= 5000, f"Average response time {result.average_response_time:.0f}ms exceeds 5000ms"
        assert result.requests_per_second >= 20, f"RPS {result.requests_per_second:.1f} below 20 for stress test"
        assert result.peak_memory_mb <= 1000, f"Peak memory {result.peak_memory_mb:.1f}MB exceeds 1000MB"
        
        # Ensure system is still responsive
        assert len(result.errors) <= result.total_requests * 0.3, "Too many errors during stress test"
        
        self.print_load_test_results(result)

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_spike_load_scenario(self, load_test_application):
        """Test system response to sudden traffic spikes"""
        print("\nTesting spike load scenario...")
        
        # Normal load phase
        normal_scenario = LoadTestScenario(
            name="Normal Phase",
            duration=30,
            concurrent_users=10,
            requests_per_user=10,
            think_time_range=(1.0, 2.0)
        )
        
        normal_result = await self.run_load_test_scenario(load_test_application, normal_scenario)
        
        # Wait a moment
        await asyncio.sleep(5)
        
        # Spike phase - sudden increase
        spike_scenario = LoadTestScenario(
            name="Spike Phase", 
            duration=60,
            concurrent_users=75,  # 7.5x increase
            requests_per_user=20,
            think_time_range=(0.1, 0.5)
        )
        
        spike_result = await self.run_load_test_scenario(load_test_application, spike_scenario)
        
        # Recovery phase - back to normal
        recovery_scenario = LoadTestScenario(
            name="Recovery Phase",
            duration=30,
            concurrent_users=10,
            requests_per_user=10,
            think_time_range=(1.0, 2.0)
        )
        
        recovery_result = await self.run_load_test_scenario(load_test_application, recovery_scenario)
        
        # Spike test assertions
        assert spike_result.success_rate >= 0.85, f"Spike success rate {spike_result.success_rate:.2%} below 85%"
        
        # System should recover well
        recovery_performance_ratio = recovery_result.average_response_time / normal_result.average_response_time
        assert recovery_performance_ratio <= 1.5, f"Recovery performance {recovery_performance_ratio:.2f}x worse than normal"
        
        print(f"\nSpike Load Test Results:")
        print(f"Normal phase: {normal_result.success_rate:.1%} success, {normal_result.average_response_time:.0f}ms avg")
        print(f"Spike phase: {spike_result.success_rate:.1%} success, {spike_result.average_response_time:.0f}ms avg") 
        print(f"Recovery phase: {recovery_result.success_rate:.1%} success, {recovery_result.average_response_time:.0f}ms avg")
        print(f"Recovery ratio: {recovery_performance_ratio:.2f}x")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_endurance_scenario(self, load_test_application):
        """Test system endurance over extended period"""
        print("\nTesting system endurance...")
        
        endurance_phases = 6  # 6 phases of 5 minutes each (30 minutes total)
        phase_duration = 300  # 5 minutes per phase
        
        phase_results = []
        
        for phase in range(endurance_phases):
            print(f"Endurance phase {phase + 1}/{endurance_phases}")
            
            scenario = LoadTestScenario(
                name=f"Endurance Phase {phase + 1}",
                duration=phase_duration,
                concurrent_users=25,
                requests_per_user=30,
                think_time_range=(0.5, 1.5)
            )
            
            phase_result = await self.run_load_test_scenario(load_test_application, scenario)
            phase_results.append(phase_result)
            
            # Brief pause between phases
            await asyncio.sleep(10)
        
        # Analyze endurance results
        success_rates = [r.success_rate for r in phase_results]
        response_times = [r.average_response_time for r in phase_results]
        memory_usage = [r.peak_memory_mb for r in phase_results]
        
        # Check for degradation over time
        first_half_success = statistics.mean(success_rates[:3])
        second_half_success = statistics.mean(success_rates[3:])
        success_degradation = (first_half_success - second_half_success) / first_half_success
        
        first_half_response_time = statistics.mean(response_times[:3])
        second_half_response_time = statistics.mean(response_times[3:])
        response_time_degradation = (second_half_response_time - first_half_response_time) / first_half_response_time
        
        # Memory growth analysis
        memory_growth = (memory_usage[-1] - memory_usage[0]) / memory_usage[0] if memory_usage[0] > 0 else 0
        
        # Endurance assertions
        assert success_degradation <= 0.05, f"Success rate degradation {success_degradation:.2%} exceeds 5%"
        assert response_time_degradation <= 0.30, f"Response time degradation {response_time_degradation:.2%} exceeds 30%"
        assert memory_growth <= 0.50, f"Memory growth {memory_growth:.2%} exceeds 50%"
        
        # All phases should meet minimum standards
        for i, result in enumerate(phase_results):
            assert result.success_rate >= 0.90, f"Phase {i+1} success rate {result.success_rate:.2%} below 90%"
        
        print(f"\nEndurance Test Summary:")
        print(f"Phases completed: {len(phase_results)}")
        print(f"Success rate degradation: {success_degradation:.2%}")
        print(f"Response time degradation: {response_time_degradation:.2%}")
        print(f"Memory growth: {memory_growth:.2%}")
        print(f"Final success rate: {phase_results[-1].success_rate:.2%}")

    def print_load_test_results(self, result: LoadTestResult):
        """Print formatted load test results"""
        print(f"\nLoad Test Results Summary:")
        print(f"{'='*50}")
        print(f"Total Requests: {result.total_requests}")
        print(f"Successful: {result.successful_requests} ({result.success_rate:.1%})")
        print(f"Failed: {result.failed_requests}")
        print(f"Errors: {result.error_requests}")
        print(f"Duration: {result.total_duration:.1f}s")
        print(f"Requests/Second: {result.requests_per_second:.1f}")
        print(f"Average Response Time: {result.average_response_time:.0f}ms")
        print(f"95th Percentile: {result.p95_response_time:.0f}ms")
        print(f"99th Percentile: {result.p99_response_time:.0f}ms")
        print(f"Peak Memory: {result.peak_memory_mb:.1f}MB")
        print(f"Average CPU: {result.average_cpu_percent:.1f}%")
        print(f"Peak Threads: {result.peak_threads}")
        
        if result.errors:
            print(f"\nTop Errors:")
            error_counts = {}
            for error in result.errors[:10]:  # Show first 10 errors
                error_counts[error] = error_counts.get(error, 0) + 1
            
            for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"  {count}x: {error[:60]}...")

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_resource_exhaustion_recovery(self, load_test_application):
        """Test system behavior when resources are nearly exhausted"""
        app = load_test_application
        
        # Simulate resource exhaustion by creating many concurrent operations
        print("\nTesting resource exhaustion recovery...")
        
        # Phase 1: Push system to limits
        exhaustion_scenario = LoadTestScenario(
            name="Resource Exhaustion",
            duration=60,
            concurrent_users=200,  # Very high load
            requests_per_user=10,
            think_time_range=(0.01, 0.1)  # Very little think time
        )
        
        exhaustion_result = await self.run_load_test_scenario(app, exhaustion_scenario)
        
        # Wait for system to settle
        print("Allowing system recovery time...")
        await asyncio.sleep(30)
        
        # Phase 2: Test recovery
        recovery_scenario = LoadTestScenario(
            name="Recovery Test",
            duration=30,
            concurrent_users=20,  # Back to normal load
            requests_per_user=10,
            think_time_range=(0.5, 1.5)
        )
        
        recovery_result = await self.run_load_test_scenario(app, recovery_scenario)
        
        # Recovery assertions
        assert recovery_result.success_rate >= 0.95, f"Recovery success rate {recovery_result.success_rate:.2%} below 95%"
        assert recovery_result.average_response_time <= 1000, f"Recovery response time {recovery_result.average_response_time:.0f}ms too high"
        
        print(f"\nResource Exhaustion Recovery Results:")
        print(f"Exhaustion phase: {exhaustion_result.success_rate:.1%} success rate")
        print(f"Recovery phase: {recovery_result.success_rate:.1%} success rate")
        print(f"System recovered successfully: {recovery_result.success_rate >= 0.95}")