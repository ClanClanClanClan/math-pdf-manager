#!/usr/bin/env python3
"""
Performance Profiling and Optimization Tools
Provides utilities for identifying and fixing performance bottlenecks
"""

import cProfile
import pstats
import io
import sys
import time
import functools
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar
from dataclasses import dataclass, field
from datetime import datetime
import psutil
import gc
from contextlib import contextmanager

T = TypeVar('T')


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    function_name: str
    execution_time: float
    cpu_percent: float
    memory_mb: float
    call_count: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        # Convert memory to MB
        if self.memory_mb > 1024:
            self.memory_mb = self.memory_mb / (1024 * 1024)


class PerformanceProfiler:
    """Advanced performance profiling utilities."""
    
    def __init__(self):
        self.metrics: Dict[str, List[PerformanceMetrics]] = {}
        self.profiler = cProfile.Profile()
        self.is_profiling = False
        self._lock = threading.Lock()
    
    def start_profiling(self):
        """Start CPU profiling."""
        with self._lock:
            if not self.is_profiling:
                self.profiler.enable()
                self.is_profiling = True
    
    def stop_profiling(self) -> str:
        """Stop profiling and return stats."""
        with self._lock:
            if self.is_profiling:
                self.profiler.disable()
                self.is_profiling = False
                
                # Generate stats
                s = io.StringIO()
                ps = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
                ps.print_stats(20)  # Top 20 functions
                return s.getvalue()
        return ""
    
    @contextmanager
    def profile_section(self, name: str):
        """Context manager for profiling a code section."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        start_cpu = psutil.cpu_percent(interval=0.1)
        
        yield
        
        # Collect metrics
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        end_cpu = psutil.cpu_percent(interval=0.1)
        
        metrics = PerformanceMetrics(
            function_name=name,
            execution_time=end_time - start_time,
            cpu_percent=(start_cpu + end_cpu) / 2,
            memory_mb=(end_memory - start_memory) / (1024 * 1024)
        )
        
        # Store metrics
        with self._lock:
            if name not in self.metrics:
                self.metrics[name] = []
            self.metrics[name].append(metrics)
    
    def get_slow_functions(self, threshold_seconds: float = 1.0) -> List[Tuple[str, float]]:
        """Get functions slower than threshold."""
        slow_functions = []
        
        with self._lock:
            for func_name, metrics_list in self.metrics.items():
                avg_time = sum(m.execution_time for m in metrics_list) / len(metrics_list)
                if avg_time > threshold_seconds:
                    slow_functions.append((func_name, avg_time))
        
        return sorted(slow_functions, key=lambda x: x[1], reverse=True)
    
    def get_memory_intensive_functions(self, threshold_mb: float = 10.0) -> List[Tuple[str, float]]:
        """Get functions using more memory than threshold."""
        memory_functions = []
        
        with self._lock:
            for func_name, metrics_list in self.metrics.items():
                max_memory = max(m.memory_mb for m in metrics_list)
                if max_memory > threshold_mb:
                    memory_functions.append((func_name, max_memory))
        
        return sorted(memory_functions, key=lambda x: x[1], reverse=True)
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report."""
        with self._lock:
            report = {
                "summary": {
                    "total_functions_profiled": len(self.metrics),
                    "total_measurements": sum(len(m) for m in self.metrics.values()),
                },
                "slow_functions": self.get_slow_functions(),
                "memory_intensive": self.get_memory_intensive_functions(),
                "detailed_metrics": {}
            }
            
            # Add detailed metrics
            for func_name, metrics_list in self.metrics.items():
                report["detailed_metrics"][func_name] = {
                    "call_count": len(metrics_list),
                    "total_time": sum(m.execution_time for m in metrics_list),
                    "avg_time": sum(m.execution_time for m in metrics_list) / len(metrics_list),
                    "max_time": max(m.execution_time for m in metrics_list),
                    "avg_cpu": sum(m.cpu_percent for m in metrics_list) / len(metrics_list),
                    "max_memory_mb": max(m.memory_mb for m in metrics_list),
                }
            
            return report


def profile_function(profiler: Optional[PerformanceProfiler] = None):
    """
    Decorator to profile function performance.
    
    Args:
        profiler: Optional profiler instance to use
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Use shared profiler if none provided
        nonlocal profiler
        if profiler is None:
            profiler = _global_profiler
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            with profiler.profile_section(func.__name__):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class MemoryOptimizer:
    """Tools for memory optimization."""
    
    @staticmethod
    def get_object_size(obj: Any, seen: Optional[set] = None) -> int:
        """Get deep size of object in bytes."""
        size = sys.getsizeof(obj)
        if seen is None:
            seen = set()
        
        obj_id = id(obj)
        if obj_id in seen:
            return 0
        
        seen.add(obj_id)
        
        if isinstance(obj, dict):
            size += sum(
                MemoryOptimizer.get_object_size(v, seen) + 
                MemoryOptimizer.get_object_size(k, seen) 
                for k, v in obj.items()
            )
        elif hasattr(obj, '__dict__'):
            size += MemoryOptimizer.get_object_size(obj.__dict__, seen)
        elif hasattr(obj, '__iter__') and not isinstance(obj, (str, bytes, bytearray)):
            size += sum(MemoryOptimizer.get_object_size(i, seen) for i in obj)
        
        return size
    
    @staticmethod
    def optimize_string_storage(strings: List[str]) -> List[str]:
        """Optimize string storage using interning."""
        return [sys.intern(s) for s in strings]
    
    @staticmethod
    def clear_caches():
        """Clear various Python caches."""
        gc.collect()
        
        # Clear functools caches
        import functools
        functools._lru_cache_wrapper.cache_clear()
        
        # Clear re caches
        import re
        re.purge()
    
    @staticmethod
    @contextmanager
    def memory_limit(limit_mb: float):
        """Context manager to limit memory usage."""
        import resource
        
        # Get current limits
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        
        # Set new limit
        limit_bytes = int(limit_mb * 1024 * 1024)
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, hard))
        
        try:
            yield
        finally:
            # Restore original limits
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


class OptimizationSuggestions:
    """Generate optimization suggestions based on profiling data."""
    
    @staticmethod
    def analyze_complexity(code: str) -> Dict[str, Any]:
        """Analyze code complexity and suggest improvements."""
        import ast
        import radon.complexity as radon_cc
        
        try:
            ast.parse(code)
            
            # Get cyclomatic complexity
            cc_results = radon_cc.cc_visit(code)
            
            suggestions = []
            
            for result in cc_results:
                if result.complexity > 10:
                    suggestions.append({
                        "function": result.name,
                        "complexity": result.complexity,
                        "suggestion": "Consider breaking this function into smaller functions",
                        "line": result.lineno
                    })
            
            return {
                "complexity_analysis": [
                    {
                        "name": r.name,
                        "complexity": r.complexity,
                        "rank": r.rank
                    } for r in cc_results
                ],
                "suggestions": suggestions
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def suggest_caching_opportunities(
        profiler_report: Dict[str, Any],
        min_calls: int = 10,
        min_time: float = 0.1
    ) -> List[Dict[str, Any]]:
        """Suggest functions that would benefit from caching."""
        suggestions = []
        
        for func_name, metrics in profiler_report.get("detailed_metrics", {}).items():
            if (metrics["call_count"] >= min_calls and 
                metrics["avg_time"] >= min_time):
                
                potential_savings = metrics["total_time"] * 0.9  # Assume 90% savings
                
                suggestions.append({
                    "function": func_name,
                    "reason": f"Called {metrics['call_count']} times, "
                             f"avg {metrics['avg_time']:.3f}s per call",
                    "potential_time_saved": potential_savings,
                    "recommendation": "Add @lru_cache or memoization"
                })
        
        return sorted(suggestions, key=lambda x: x["potential_time_saved"], reverse=True)


# Global profiler instance
_global_profiler = PerformanceProfiler()


def get_global_profiler() -> PerformanceProfiler:
    """Get the global profiler instance."""
    return _global_profiler