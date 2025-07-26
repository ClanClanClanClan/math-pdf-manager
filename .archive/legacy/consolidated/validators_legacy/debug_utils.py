#!/usr/bin/env python3
"""
Debug Utilities for Filename Validation
Extracted from filename_checker.py to improve maintainability
"""

# Global debug state
_DEBUG_ENABLED = False


def enable_debug():
    """Enable comprehensive debugging output"""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = True
    print("🔍 DEBUG: Comprehensive debugging ENABLED")


def disable_debug():
    """Disable debugging output"""
    global _DEBUG_ENABLED
    _DEBUG_ENABLED = False


def debug_print(*args, **kwargs):
    """Print debug message only if debugging is enabled"""
    if _DEBUG_ENABLED:
        print("🔍 DEBUG:", *args, **kwargs)


def is_debug_enabled() -> bool:
    """Check if debug mode is enabled"""
    return _DEBUG_ENABLED


def debug_section(section_name: str):
    """Print a debug section header"""
    if _DEBUG_ENABLED:
        print(f"🔍 DEBUG: === {section_name} ===")


def debug_result(operation: str, result: any):
    """Print debug result"""
    if _DEBUG_ENABLED:
        print(f"🔍 DEBUG: {operation} -> {result}")


def debug_timing(operation: str, duration: float):
    """Print timing debug information"""
    if _DEBUG_ENABLED:
        print(f"🔍 DEBUG: {operation} took {duration:.4f}s")


def debug_warning(message: str):
    """Print debug warning"""
    if _DEBUG_ENABLED:
        print(f"🔍 DEBUG WARNING: {message}")


def debug_error(message: str):
    """Print debug error"""
    if _DEBUG_ENABLED:
        print(f"🔍 DEBUG ERROR: {message}")


def debug_list(name: str, items: list, max_items: int = 10):
    """Print debug list with truncation"""
    if _DEBUG_ENABLED:
        if len(items) <= max_items:
            print(f"🔍 DEBUG: {name}: {items}")
        else:
            truncated = items[:max_items]
            print(f"🔍 DEBUG: {name}: {truncated} ... ({len(items)} total)")


def debug_dict(name: str, data: dict, max_items: int = 10):
    """Print debug dictionary with truncation"""
    if _DEBUG_ENABLED:
        if len(data) <= max_items:
            print(f"🔍 DEBUG: {name}: {data}")
        else:
            truncated_items = list(data.items())[:max_items]
            truncated_dict = dict(truncated_items)
            print(f"🔍 DEBUG: {name}: {truncated_dict} ... ({len(data)} total)")


def debug_function_call(func_name: str, args: tuple = (), kwargs: dict = None):
    """Print debug function call information"""
    if _DEBUG_ENABLED:
        if kwargs:
            print(f"🔍 DEBUG: Calling {func_name}({args}, {kwargs})")
        else:
            print(f"🔍 DEBUG: Calling {func_name}({args})")


def debug_performance(operation: str, count: int, duration: float):
    """Print performance debug information"""
    if _DEBUG_ENABLED:
        rate = count / duration if duration > 0 else 0
        print(f"🔍 DEBUG: {operation}: {count} items in {duration:.4f}s ({rate:.2f} items/s)")


class DebugContext:
    """Context manager for debug sections"""
    
    def __init__(self, section_name: str):
        self.section_name = section_name
        self.start_time = None
    
    def __enter__(self):
        if _DEBUG_ENABLED:
            import time
            self.start_time = time.time()
            debug_section(f"ENTER {self.section_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if _DEBUG_ENABLED:
            import time
            duration = time.time() - self.start_time
            if exc_type:
                debug_error(f"EXIT {self.section_name} with error: {exc_val}")
            else:
                debug_section(f"EXIT {self.section_name} ({duration:.4f}s)")
        return False


def debug_context(section_name: str):
    """Create a debug context manager"""
    return DebugContext(section_name)