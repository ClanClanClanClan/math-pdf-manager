#!/usr/bin/env python3
"""
Advanced Performance Benchmarking Suite
=======================================

Comprehensive benchmarking for the academic PDF system:
- Download speed tests across publishers
- Metadata extraction performance
- Cache effectiveness measurement
- Concurrent operation scaling
- Memory and CPU profiling
- Load testing scenarios
"""

import asyncio
import json
import logging
import statistics

# System imports
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
import matplotlib.pyplot as plt
import pandas as pd
import psutil

sys.path.append(str(Path(__file__).parent.parent.parent / "src"))

from core.caching.advanced_cache import get_cache_manager
from core.monitoring.telemetry import TelemetryCollector, get_telemetry
from downloader.proper_downloader import ProperAcademicDownloader
from publishers.ieee_publisher import IEEEPublisher
from publishers.siam_publisher import SIAMPublisher


@dataclass
class BenchmarkResult:
    """Single benchmark test result"""

    test_name: str
    operation: str
    duration: float
    success: bool
    throughput: float = 0.0
    memory_peak: int = 0
    cpu_percent: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SystemMetrics:
    """System resource metrics"""

    cpu_percent: float
    memory_percent: float
    memory_used: int
    disk_io_read: int
    disk_io_write: int
    network_sent: int
    network_recv: int
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class PerformanceBenchmark:
    """Advanced performance benchmarking suite"""

    def __init__(self, output_dir: Path = Path("benchmark_results")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)

        self.results: List[BenchmarkResult] = []
        self.system_metrics: List[SystemMetrics] = []

        # Test configurations
        self.test_papers = {
            "ieee": [
                "10.1109/CVPR.2016.90",  # ResNet paper
                "10.1109/TPAMI.2020.2992934",
                "10.1109/ICCV.2019.00069",
            ],
            "siam": [
                "10.1137/S0097539795293172",
                "10.1137/20M1320493",
                "10.1137/1.9781611974737.1",
            ],
            "arxiv": [
                "2103.14030",  # EfficientNet paper
                "1706.03762",  # Transformer paper
                "1512.03385",  # ResNet paper
            ],
        }

        # System monitoring
        self.process = psutil.Process()
        self.monitoring_task = None

        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    async def start_system_monitoring(self, interval: float = 1.0):
        """Start background system metrics collection"""

        async def monitor():
            while True:
                try:
                    # CPU and memory
                    cpu_percent = self.process.cpu_percent()
                    memory_info = self.process.memory_info()
                    memory_percent = self.process.memory_percent()

                    # I/O stats
                    io_counters = self.process.io_counters()

                    # Network stats (system-wide)
                    net_io = psutil.net_io_counters()

                    metrics = SystemMetrics(
                        cpu_percent=cpu_percent,
                        memory_percent=memory_percent,
                        memory_used=memory_info.rss,
                        disk_io_read=io_counters.read_bytes,
                        disk_io_write=io_counters.write_bytes,
                        network_sent=net_io.bytes_sent,
                        network_recv=net_io.bytes_recv,
                    )

                    self.system_metrics.append(metrics)

                    # Keep only recent metrics (last hour)
                    cutoff = time.time() - 3600
                    self.system_metrics = [m for m in self.system_metrics if m.timestamp > cutoff]

                    await asyncio.sleep(interval)

                except Exception as e:
                    self.logger.warning(f"System monitoring error: {e}")
                    await asyncio.sleep(interval)

        self.monitoring_task = asyncio.create_task(monitor())

    async def stop_system_monitoring(self):
        """Stop system monitoring"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

    async def benchmark_download_speed(
        self, publisher: str, concurrent: int = 1
    ) -> List[BenchmarkResult]:
        """Benchmark download speeds for a publisher"""
        results = []
        papers = self.test_papers.get(publisher, [])

        if not papers:
            self.logger.warning(f"No test papers for publisher: {publisher}")
            return results

        self.logger.info(f"Benchmarking {publisher} downloads (concurrent={concurrent})")

        # Setup downloader
        downloader = ProperAcademicDownloader(f"benchmark_{publisher}")

        try:
            if concurrent == 1:
                # Sequential downloads
                for paper in papers:
                    start_time = time.time()
                    tracemalloc.start()

                    try:
                        result = await downloader.download(paper)
                        duration = time.time() - start_time
                        current, peak = tracemalloc.get_traced_memory()

                        benchmark_result = BenchmarkResult(
                            test_name=f"{publisher}_download_sequential",
                            operation=f"download_{paper}",
                            duration=duration,
                            success=result.success,
                            throughput=result.file_size / duration if result.success else 0,
                            memory_peak=peak,
                            metadata={
                                "paper_id": paper,
                                "file_size": result.file_size if result.success else 0,
                                "source": result.source_used if result.success else None,
                            },
                        )
                        results.append(benchmark_result)

                    except Exception as e:
                        duration = time.time() - start_time
                        results.append(
                            BenchmarkResult(
                                test_name=f"{publisher}_download_sequential",
                                operation=f"download_{paper}",
                                duration=duration,
                                success=False,
                                error=str(e),
                            )
                        )
                    finally:
                        tracemalloc.stop()

            else:
                # Concurrent downloads
                start_time = time.time()
                tracemalloc.start()

                tasks = []
                for paper in papers[:concurrent]:
                    tasks.append(downloader.download(paper))

                try:
                    download_results = await asyncio.gather(*tasks, return_exceptions=True)
                    duration = time.time() - start_time
                    current, peak = tracemalloc.get_traced_memory()

                    success_count = sum(
                        1 for r in download_results if hasattr(r, "success") and r.success
                    )

                    total_size = sum(
                        r.file_size
                        for r in download_results
                        if hasattr(r, "success") and r.success and r.file_size
                    )

                    results.append(
                        BenchmarkResult(
                            test_name=f"{publisher}_download_concurrent",
                            operation=f"download_batch_{concurrent}",
                            duration=duration,
                            success=success_count == len(tasks),
                            throughput=total_size / duration if total_size > 0 else 0,
                            memory_peak=peak,
                            metadata={
                                "concurrent_count": concurrent,
                                "success_count": success_count,
                                "total_size": total_size,
                            },
                        )
                    )

                except Exception as e:
                    duration = time.time() - start_time
                    results.append(
                        BenchmarkResult(
                            test_name=f"{publisher}_download_concurrent",
                            operation=f"download_batch_{concurrent}",
                            duration=duration,
                            success=False,
                            error=str(e),
                        )
                    )
                finally:
                    tracemalloc.stop()

        finally:
            await downloader.close()

        return results

    async def benchmark_cache_performance(self) -> List[BenchmarkResult]:
        """Benchmark cache system performance"""
        results = []
        cache_manager = get_cache_manager()

        # Test data
        test_keys = [f"test_key_{i}" for i in range(100)]
        test_values = [{"data": f"test_data_{i}" * 100} for i in range(100)]

        # Cache write performance
        start_time = time.time()
        tracemalloc.start()

        try:
            for key, value in zip(test_keys, test_values):
                await cache_manager.set(key, value)

            duration = time.time() - start_time
            current, peak = tracemalloc.get_traced_memory()

            results.append(
                BenchmarkResult(
                    test_name="cache_write_performance",
                    operation="cache_batch_write",
                    duration=duration,
                    success=True,
                    throughput=len(test_keys) / duration,
                    memory_peak=peak,
                    metadata={"keys_written": len(test_keys)},
                )
            )

        finally:
            tracemalloc.stop()

        # Cache read performance (cold)
        start_time = time.time()
        cache_hits = 0

        for key in test_keys:
            result = await cache_manager.get(key)
            if result is not None:
                cache_hits += 1

        duration = time.time() - start_time

        results.append(
            BenchmarkResult(
                test_name="cache_read_cold",
                operation="cache_batch_read",
                duration=duration,
                success=True,
                throughput=len(test_keys) / duration,
                metadata={
                    "keys_read": len(test_keys),
                    "cache_hits": cache_hits,
                    "hit_rate": cache_hits / len(test_keys),
                },
            )
        )

        # Cache read performance (warm)
        start_time = time.time()
        cache_hits = 0

        for key in test_keys:
            result = await cache_manager.get(key)
            if result is not None:
                cache_hits += 1

        duration = time.time() - start_time

        results.append(
            BenchmarkResult(
                test_name="cache_read_warm",
                operation="cache_batch_read_warm",
                duration=duration,
                success=True,
                throughput=len(test_keys) / duration,
                metadata={
                    "keys_read": len(test_keys),
                    "cache_hits": cache_hits,
                    "hit_rate": cache_hits / len(test_keys),
                },
            )
        )

        return results

    async def benchmark_scaling(self, max_concurrent: int = 20) -> List[BenchmarkResult]:
        """Benchmark system scaling with increasing concurrency"""
        results = []

        # Test different concurrency levels
        concurrency_levels = [1, 2, 5, 10, max_concurrent]

        for concurrent in concurrency_levels:
            self.logger.info(f"Testing concurrency level: {concurrent}")

            # Use ArXiv as it's most reliable for testing
            papers = self.test_papers["arxiv"][:concurrent]

            start_time = time.time()
            tracemalloc.start()

            try:
                # Create multiple downloader instances
                downloaders = [
                    ProperAcademicDownloader(f"scale_test_{i}") for i in range(concurrent)
                ]

                # Create download tasks
                tasks = []
                for i, paper in enumerate(papers):
                    downloader = downloaders[i % len(downloaders)]
                    tasks.append(downloader.download(paper))

                # Execute concurrently
                download_results = await asyncio.gather(*tasks, return_exceptions=True)

                duration = time.time() - start_time
                current, peak = tracemalloc.get_traced_memory()

                success_count = sum(
                    1 for r in download_results if hasattr(r, "success") and r.success
                )

                # Cleanup downloaders
                for downloader in downloaders:
                    await downloader.close()

                results.append(
                    BenchmarkResult(
                        test_name="scaling_test",
                        operation=f"concurrent_{concurrent}",
                        duration=duration,
                        success=success_count > 0,
                        throughput=success_count / duration,
                        memory_peak=peak,
                        cpu_percent=self.process.cpu_percent(),
                        metadata={
                            "concurrency": concurrent,
                            "success_count": success_count,
                            "total_tasks": len(tasks),
                        },
                    )
                )

            except Exception as e:
                duration = time.time() - start_time
                results.append(
                    BenchmarkResult(
                        test_name="scaling_test",
                        operation=f"concurrent_{concurrent}",
                        duration=duration,
                        success=False,
                        error=str(e),
                        metadata={"concurrency": concurrent},
                    )
                )
            finally:
                tracemalloc.stop()

        return results

    async def run_comprehensive_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        self.logger.info("Starting comprehensive performance benchmark")

        await self.start_system_monitoring()

        try:
            # Download speed benchmarks
            for publisher in ["ieee", "siam", "arxiv"]:
                # Sequential downloads
                sequential_results = await self.benchmark_download_speed(publisher, 1)
                self.results.extend(sequential_results)

                # Concurrent downloads
                concurrent_results = await self.benchmark_download_speed(publisher, 3)
                self.results.extend(concurrent_results)

            # Cache performance
            cache_results = await self.benchmark_cache_performance()
            self.results.extend(cache_results)

            # Scaling tests
            scaling_results = await self.benchmark_scaling(10)
            self.results.extend(scaling_results)

        finally:
            await self.stop_system_monitoring()

        # Generate report
        report = await self.generate_report()

        self.logger.info("Comprehensive benchmark completed")
        return report

    async def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive benchmark report"""
        timestamp = datetime.now().isoformat()

        # Group results by test type
        results_by_test = {}
        for result in self.results:
            if result.test_name not in results_by_test:
                results_by_test[result.test_name] = []
            results_by_test[result.test_name].append(result)

        # Calculate statistics
        stats = {}
        for test_name, test_results in results_by_test.items():
            durations = [r.duration for r in test_results if r.success]
            throughputs = [r.throughput for r in test_results if r.success and r.throughput > 0]

            if durations:
                stats[test_name] = {
                    "count": len(test_results),
                    "success_rate": len([r for r in test_results if r.success]) / len(test_results),
                    "avg_duration": statistics.mean(durations),
                    "median_duration": statistics.median(durations),
                    "min_duration": min(durations),
                    "max_duration": max(durations),
                    "avg_throughput": statistics.mean(throughputs) if throughputs else 0,
                    "max_memory_peak": max(r.memory_peak for r in test_results if r.memory_peak),
                }

        # System metrics summary
        system_summary = {}
        if self.system_metrics:
            cpu_values = [m.cpu_percent for m in self.system_metrics]
            memory_values = [m.memory_percent for m in self.system_metrics]

            system_summary = {
                "avg_cpu_percent": statistics.mean(cpu_values),
                "max_cpu_percent": max(cpu_values),
                "avg_memory_percent": statistics.mean(memory_values),
                "max_memory_percent": max(memory_values),
                "peak_memory_usage": max(m.memory_used for m in self.system_metrics),
            }

        report = {
            "timestamp": timestamp,
            "summary": {
                "total_tests": len(self.results),
                "successful_tests": len([r for r in self.results if r.success]),
                "total_duration": sum(r.duration for r in self.results),
                "overall_success_rate": len([r for r in self.results if r.success])
                / len(self.results),
            },
            "test_statistics": stats,
            "system_metrics": system_summary,
            "raw_results": [asdict(r) for r in self.results],
        }

        # Save report
        report_file = self.output_dir / f"benchmark_report_{int(time.time())}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        self.logger.info(f"Benchmark report saved to: {report_file}")

        # Generate visualizations
        await self.generate_visualizations(report)

        return report

    async def generate_visualizations(self, report: Dict[str, Any]):
        """Generate performance visualization charts"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns

            # Set style
            plt.style.use("seaborn-v0_8")

            # Duration comparison chart
            test_names = list(report["test_statistics"].keys())
            durations = [stats["avg_duration"] for stats in report["test_statistics"].values()]

            plt.figure(figsize=(12, 6))
            plt.bar(range(len(test_names)), durations)
            plt.xticks(range(len(test_names)), test_names, rotation=45, ha="right")
            plt.ylabel("Average Duration (seconds)")
            plt.title("Performance Benchmark - Average Duration by Test")
            plt.tight_layout()

            chart_file = self.output_dir / "benchmark_durations.png"
            plt.savefig(chart_file, dpi=300, bbox_inches="tight")
            plt.close()

            # Throughput comparison
            throughputs = [stats["avg_throughput"] for stats in report["test_statistics"].values()]

            plt.figure(figsize=(12, 6))
            plt.bar(range(len(test_names)), throughputs)
            plt.xticks(range(len(test_names)), test_names, rotation=45, ha="right")
            plt.ylabel("Average Throughput")
            plt.title("Performance Benchmark - Average Throughput by Test")
            plt.tight_layout()

            throughput_file = self.output_dir / "benchmark_throughput.png"
            plt.savefig(throughput_file, dpi=300, bbox_inches="tight")
            plt.close()

            self.logger.info("Benchmark visualizations generated")

        except ImportError:
            self.logger.warning("Matplotlib not available - skipping visualizations")
        except Exception as e:
            self.logger.error(f"Visualization generation failed: {e}")


async def main():
    """Run benchmark suite"""
    benchmark = PerformanceBenchmark()
    report = await benchmark.run_comprehensive_benchmark()

    print("\n🚀 PERFORMANCE BENCHMARK RESULTS")
    print("=" * 50)
    print(f"Total Tests: {report['summary']['total_tests']}")
    print(f"Success Rate: {report['summary']['overall_success_rate']:.1%}")
    print(f"Total Duration: {report['summary']['total_duration']:.2f}s")

    print("\n📊 TOP PERFORMING TESTS:")
    stats = report["test_statistics"]
    sorted_tests = sorted(stats.items(), key=lambda x: x[1]["avg_duration"])

    for test_name, test_stats in sorted_tests[:5]:
        print(f"  {test_name}: {test_stats['avg_duration']:.3f}s avg")

    if "system_metrics" in report:
        sys_metrics = report["system_metrics"]
        print(f"\n💻 SYSTEM USAGE:")
        print(f"  Peak CPU: {sys_metrics.get('max_cpu_percent', 0):.1f}%")
        print(f"  Peak Memory: {sys_metrics.get('max_memory_percent', 0):.1f}%")


if __name__ == "__main__":
    asyncio.run(main())
