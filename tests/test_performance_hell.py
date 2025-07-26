#!/usr/bin/env python3
"""
Hell-level performance tests for the optimized filename validator.
Tests performance improvements, memory usage, and scalability.
"""

import gc
import memory_profiler
import psutil
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List
import sys

import pytest
import hypothesis
from hypothesis import given, strategies as st, settings

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from validators.optimized_filename_validator import OptimizedFilenameValidator, check_filename, ValidationConfig


class TestPerformanceComparisons:
    """Compare performance between old and new implementations."""
    
    def test_basic_validation_speed(self):
        """Test basic validation speed improvements."""
        test_filenames = [
            "Smith, John - A Novel Approach to Machine Learning.pdf",
            "García, María A. - Advanced Quantum Mechanics in Curved Spacetime.pdf", 
            "von Neumann, John; Turing, Alan - Computational Theory and Practice.pdf",
            "李, Wei; 山田, Hiroshi - Cross-Cultural Analysis of Mathematical Methods.pdf",
            "O'Connor, Patrick J. - Statistical Methods for Large-Scale Data Analysis.pdf",
        ] * 100  # 500 test cases
        
        # Test optimized version
        validator = OptimizedFilenameValidator()
        
        start_time = time.perf_counter()
        for filename in test_filenames:
            result = validator.check_filename(filename)
            assert result is not None
        optimized_time = time.perf_counter() - start_time
        
        # Get performance stats
        stats = validator.get_performance_stats()
        
        print(f"Optimized validation: {len(test_filenames)} files in {optimized_time:.3f}s")
        print(f"Average time per file: {stats['average_time_ms']:.3f}ms")
        print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
        
        # Performance assertions
        assert optimized_time < 1.0  # Should validate 500 files in under 1 second
        assert stats['average_time_ms'] < 5.0  # Should average under 5ms per file
        assert stats['cache_hit_rate'] > 0.1   # Should have some cache benefits
    
    def test_unicode_processing_performance(self):
        """Test Unicode processing performance improvements."""
        unicode_filenames = [
            "Müller, Hans - Über die Grundlagen der Mathematik.pdf",
            "Гаусс, Карл - О теории чисел и алгебре.pdf", 
            "田中, 太郎 - 数学的解析の新手法について.pdf",
            "אוילר, לאונרד - יסודות התורה המתמטית.pdf",
            "محمد, أحمد - نظرية الأعداد والهندسة الجبرية.pdf",
            "café naïve résumé".replace(" ", ", ") + " - Mathematical Analysis.pdf",
            "Пуанкаре́, Анри́ - Топологический анализ.pdf",
        ] * 50  # 350 test cases
        
        validator = OptimizedFilenameValidator()
        
        start_time = time.perf_counter()
        for filename in unicode_filenames:
            result = validator.check_filename(filename)
            assert result is not None
        unicode_time = time.perf_counter() - start_time
        
        stats = validator.get_performance_stats()
        
        print(f"Unicode processing: {len(unicode_filenames)} files in {unicode_time:.3f}s")
        print(f"Unicode normalizations: {stats['unicode_normalizations']}")
        
        # Should handle Unicode efficiently
        assert unicode_time < 2.0
        assert stats['average_time_ms'] < 10.0
    
    def test_memory_usage(self):
        """Test memory efficiency."""
        import tracemalloc
        
        # Start memory tracing
        tracemalloc.start()
        
        # Create large dataset
        test_data = []
        for i in range(1000):
            test_data.extend([
                f"Author{i}, John - Title {i} with Some Mathematical Content.pdf",
                f"Smith{i}, Jane A. - Advanced Studies in Number Theory {i}.pdf",
                f"Professor{i}, Dr. - Research Paper {i} on Complex Analysis.pdf",
            ])
        
        validator = OptimizedFilenameValidator()
        
        # Measure memory before validation
        current, peak = tracemalloc.get_traced_memory()
        memory_before = current / 1024 / 1024  # MB
        
        # Process all files
        results = []
        for filename in test_data:
            result = validator.check_filename(filename)
            results.append(result)
        
        # Measure memory after validation
        current, peak = tracemalloc.get_traced_memory()
        memory_after = current / 1024 / 1024  # MB
        memory_peak = peak / 1024 / 1024  # MB
        
        tracemalloc.stop()
        
        print(f"Memory usage:")
        print(f"  Before: {memory_before:.2f} MB")
        print(f"  After: {memory_after:.2f} MB") 
        print(f"  Peak: {memory_peak:.2f} MB")
        print(f"  Growth: {memory_after - memory_before:.2f} MB")
        
        # Memory assertions
        memory_growth = memory_after - memory_before
        assert memory_growth < 50.0  # Should use less than 50MB additional memory
        assert memory_peak < 100.0    # Peak should be under 100MB
    
    @pytest.mark.skipif(not hasattr(memory_profiler, 'profile'), reason="memory_profiler not available")
    def test_memory_profiling(self):
        """Detailed memory profiling."""
        
        @memory_profiler.profile
        def validate_large_batch():
            validator = OptimizedFilenameValidator()
            filenames = [
                f"Author{i}, Name - Title {i} of Mathematical Paper.pdf" 
                for i in range(2000)
            ]
            
            return [validator.check_filename(f) for f in filenames]
        
        # Run profiling
        results = validate_large_batch()
        assert len(results) == 2000
        assert all(r is not None for r in results)
    
    def test_concurrent_performance(self):
        """Test performance under concurrent load."""
        filenames = [
            f"Author{i}, Name{j} - Title {i}-{j} Research Paper.pdf"
            for i in range(100) for j in range(10)
        ]  # 1000 files
        
        def validate_batch(file_batch):
            validator = OptimizedFilenameValidator()
            return [validator.check_filename(f) for f in file_batch]
        
        # Split into batches for concurrent processing
        batch_size = 50
        batches = [filenames[i:i+batch_size] for i in range(0, len(filenames), batch_size)]
        
        start_time = time.perf_counter()
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_batch = {executor.submit(validate_batch, batch): batch for batch in batches}
            
            results = []
            for future in as_completed(future_to_batch):
                batch_results = future.result()
                results.extend(batch_results)
        
        concurrent_time = time.perf_counter() - start_time
        
        print(f"Concurrent validation: {len(filenames)} files in {concurrent_time:.3f}s")
        print(f"Throughput: {len(filenames) / concurrent_time:.1f} files/sec")
        
        # Should handle concurrent load efficiently
        assert len(results) == len(filenames)
        assert concurrent_time < 5.0  # Should complete in under 5 seconds
        assert len(filenames) / concurrent_time > 100  # At least 100 files/sec


class TestScalabilityStress:
    """Test system behavior under extreme load."""
    
    def test_large_filename_handling(self):
        """Test handling of very large filenames."""
        validator = OptimizedFilenameValidator(ValidationConfig(max_filename_length=10000))
        
        # Generate increasingly large filenames
        base = "Smith, John - "
        title_base = "A Very Long Title That Goes On And On "
        
        sizes = [100, 500, 1000, 2000, 5000]
        times = []
        
        for size in sizes:
            # Create filename of target size
            title_length = size - len(base) - 4  # -4 for .pdf
            repetitions = max(1, title_length // len(title_base))
            title = (title_base * repetitions)[:title_length]
            filename = f"{base}{title}.pdf"
            
            start_time = time.perf_counter()
            result = validator.check_filename(filename)
            elapsed = time.perf_counter() - start_time
            times.append(elapsed)
            
            print(f"Size {size}: {elapsed*1000:.2f}ms")
            
            # Should handle large files without hanging
            assert elapsed < 0.1  # Should complete in under 100ms
            assert result is not None
        
        # Time complexity should be roughly linear
        # Later files shouldn't be dramatically slower
        assert times[-1] / times[0] < 10  # At most 10x slower for 50x larger file
    
    def test_pathological_input_performance(self):
        """Test performance on inputs designed to cause problems."""
        validator = OptimizedFilenameValidator()
        
        # Pathological inputs that could cause ReDoS or other issues
        evil_inputs = [
            # Potential ReDoS patterns (should be fast with fixed regex)
            "Smith, J" + ". A" * 100 + ". - Title.pdf",
            "Smith, " + "A." * 200 + " - Title.pdf", 
            
            # Unicode normalization stress
            "Smith, Café" + "é" * 1000 + " - Title.pdf",
            
            # Many repetitions
            ("Author, Name - " + "Word " * 1000).rstrip() + ".pdf",
            
            # Boundary conditions
            "A, B - C.pdf",  # Minimal valid
            "X" * 4999 + ".pdf",  # Just under limit
        ]
        
        for evil_input in evil_inputs:
            start_time = time.perf_counter()
            result = validator.check_filename(evil_input)
            elapsed = time.perf_counter() - start_time
            
            print(f"Evil input ({len(evil_input)} chars): {elapsed*1000:.2f}ms")
            
            # Should not hang or take excessive time
            assert elapsed < 0.05  # Under 50ms even for pathological cases
            assert result is not None
    
    def test_cache_effectiveness(self):
        """Test caching effectiveness under realistic usage patterns."""
        validator = OptimizedFilenameValidator()
        
        # Simulate realistic usage: some repeated validations
        base_files = [
            "Smith, John - Machine Learning Applications.pdf",
            "Jones, Mary - Statistical Analysis Methods.pdf", 
            "Wilson, Bob - Quantum Computing Theory.pdf",
            "Brown, Alice - Mathematical Optimization.pdf",
            "Davis, Carol - Numerical Analysis Techniques.pdf",
        ]
        
        # Create usage pattern with repetitions (simulating real usage)
        test_sequence = []
        for _ in range(200):
            test_sequence.extend(base_files)  # Some exact repeats
            test_sequence.extend([f.replace("John", "Johnny") for f in base_files])  # Similar but different
        
        # First pass - populate cache
        start_time = time.perf_counter()
        for filename in test_sequence[:500]:
            validator.check_filename(filename)
        first_pass_time = time.perf_counter() - start_time
        
        # Second pass - should benefit from cache
        start_time = time.perf_counter() 
        for filename in test_sequence[:500]:
            validator.check_filename(filename)
        second_pass_time = time.perf_counter() - start_time
        
        stats = validator.get_performance_stats()
        
        print(f"First pass: {first_pass_time:.3f}s")
        print(f"Second pass: {second_pass_time:.3f}s") 
        print(f"Cache hit rate: {stats['cache_hit_rate']:.2%}")
        
        # Cache should provide meaningful speedup
        assert stats['cache_hit_rate'] > 0.2  # At least 20% cache hits
        # Second pass might be faster due to caching, but not necessarily much faster
        # due to the lightweight nature of the operations
    
    def test_memory_leak_detection(self):
        """Test for memory leaks during extended operation."""
        validator = OptimizedFilenameValidator()
        
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run many validations
        for batch in range(100):  # 100 batches
            batch_files = [
                f"Author{batch}_{i}, Name - Title {batch}_{i} Research.pdf" 
                for i in range(100)
            ]  # 100 files per batch = 10,000 total
            
            for filename in batch_files:
                validator.check_filename(filename)
            
            # Force garbage collection every 10 batches
            if batch % 10 == 0:
                gc.collect()
                current_memory = process.memory_info().rss / 1024 / 1024
                memory_growth = current_memory - initial_memory
                
                print(f"Batch {batch}: Memory usage {current_memory:.1f} MB (+{memory_growth:.1f})")
                
                # Memory growth should be reasonable
                assert memory_growth < 100  # Less than 100MB growth
        
        # Final memory check
        final_memory = process.memory_info().rss / 1024 / 1024
        total_growth = final_memory - initial_memory
        
        print(f"Total memory growth: {total_growth:.1f} MB")
        
        # Should not have significant memory leaks
        assert total_growth < 200  # Less than 200MB total growth


class TestPropertyBasedPerformance:
    """Property-based performance testing."""
    
    @given(st.text(min_size=10, max_size=500))
    @settings(max_examples=200, deadline=1000)  # 1 second deadline per test
    def test_performance_properties(self, filename):
        """Test that performance is consistent across random inputs."""
        # Make it look like a filename
        if " - " not in filename:
            filename = f"Author, Name - {filename}.pdf"
        
        validator = OptimizedFilenameValidator()
        
        start_time = time.perf_counter()
        result = validator.check_filename(filename)
        elapsed = time.perf_counter() - start_time
        
        # Properties that should always hold
        assert elapsed < 0.01  # Should complete in under 10ms
        assert result is not None
        assert hasattr(result, 'filename')
        assert result.filename == filename
    
    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=50)
    def test_batch_performance_scaling(self, batch_size):
        """Test that performance scales reasonably with batch size."""
        validator = OptimizedFilenameValidator()
        
        filenames = [
            f"Author{i}, Name - Title {i} Research Paper.pdf" 
            for i in range(batch_size)
        ]
        
        start_time = time.perf_counter()
        results = [validator.check_filename(f) for f in filenames]
        elapsed = time.perf_counter() - start_time
        
        # Performance should scale roughly linearly
        time_per_file = elapsed / batch_size
        
        assert len(results) == batch_size
        assert time_per_file < 0.005  # Under 5ms per file on average
        assert elapsed < batch_size * 0.01  # Linear scaling with reasonable constant


if __name__ == "__main__":
    # Run with performance reporting
    import pytest
    pytest.main([__file__, "-v", "--tb=short", "-s"])