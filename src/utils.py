import time
import logging
import functools
from datetime import datetime
import os
from typing import Optional, Callable, Any

# Configure logging
def setup_logging(log_level: str = 'INFO') -> None:
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging format
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    # Setup file handler
    log_file = os.path.join(log_dir, f'family_planner_{datetime.now().strftime("%Y%m%d")}.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.metrics = {}
        self.logger = logging.getLogger('performance')
    
    def start_operation(self, operation_name: str) -> None:
        """Start timing an operation"""
        if operation_name not in self.metrics:
            self.metrics[operation_name] = {
                'count': 0,
                'total_time': 0,
                'min_time': float('inf'),
                'max_time': 0,
                'last_time': 0
            }
        self.metrics[operation_name]['start_time'] = time.time()
    
    def end_operation(self, operation_name: str) -> None:
        """End timing an operation and update metrics"""
        if operation_name not in self.metrics:
            return
        
        end_time = time.time()
        duration = end_time - self.metrics[operation_name]['start_time']
        
        metrics = self.metrics[operation_name]
        metrics['count'] += 1
        metrics['total_time'] += duration
        metrics['min_time'] = min(metrics['min_time'], duration)
        metrics['max_time'] = max(metrics['max_time'], duration)
        metrics['last_time'] = duration
        
        # Log slow operations
        if duration > 1.0:  # Log operations taking more than 1 second
            self.logger.warning(f"Slow operation detected: {operation_name} took {duration:.2f} seconds")
    
    def get_metrics(self) -> dict:
        """Get current performance metrics"""
        return {
            name: {
                'count': metrics['count'],
                'avg_time': metrics['total_time'] / metrics['count'] if metrics['count'] > 0 else 0,
                'min_time': metrics['min_time'],
                'max_time': metrics['max_time'],
                'last_time': metrics['last_time']
            }
            for name, metrics in self.metrics.items()
        }
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics"""
        self.metrics.clear()

# Global performance monitor instance
_performance_monitor = PerformanceMonitor()

def monitor_performance(operation_name: Optional[str] = None) -> Callable:
    """Decorator to monitor function performance"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Use function name if operation_name is not provided
            op_name = operation_name or func.__name__
            
            # Start monitoring
            _performance_monitor.start_operation(op_name)
            
            try:
                # Execute the function
                result = func(*args, **kwargs)
                return result
            finally:
                # End monitoring
                _performance_monitor.end_operation(op_name)
        
        return wrapper
    return decorator

def get_performance_metrics() -> dict:
    """Get current performance metrics"""
    return _performance_monitor.get_metrics()

def reset_performance_metrics() -> None:
    """Reset all performance metrics"""
    _performance_monitor.reset_metrics()

class CacheStats:
    """Monitor cache performance"""
    
    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.logger = logging.getLogger('cache')
    
    def record_hit(self) -> None:
        """Record a cache hit"""
        self.hits += 1
    
    def record_miss(self) -> None:
        """Record a cache miss"""
        self.misses += 1
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        
        return {
            'hits': self.hits,
            'misses': self.misses,
            'total': total,
            'hit_rate': hit_rate
        }
    
    def reset_stats(self) -> None:
        """Reset cache statistics"""
        self.hits = 0
        self.misses = 0

# Global cache stats instance
_cache_stats = CacheStats()

def record_cache_hit() -> None:
    """Record a cache hit"""
    _cache_stats.record_hit()

def record_cache_miss() -> None:
    """Record a cache miss"""
    _cache_stats.record_miss()

def get_cache_stats() -> dict:
    """Get cache statistics"""
    return _cache_stats.get_stats()

def reset_cache_stats() -> None:
    """Reset cache statistics"""
    _cache_stats.reset_stats()

def log_performance_summary() -> None:
    """Log a summary of performance metrics"""
    logger = logging.getLogger('performance')
    
    # Log database performance metrics
    db_metrics = get_performance_metrics()
    logger.info("Database Performance Metrics:")
    for operation, metrics in db_metrics.items():
        logger.info(f"  {operation}:")
        logger.info(f"    Count: {metrics['count']}")
        logger.info(f"    Average Time: {metrics['avg_time']:.3f}s")
        logger.info(f"    Min Time: {metrics['min_time']:.3f}s")
        logger.info(f"    Max Time: {metrics['max_time']:.3f}s")
        logger.info(f"    Last Time: {metrics['last_time']:.3f}s")
    
    # Log cache performance metrics
    cache_metrics = get_cache_stats()
    logger.info("Cache Performance Metrics:")
    logger.info(f"  Hits: {cache_metrics['hits']}")
    logger.info(f"  Misses: {cache_metrics['misses']}")
    logger.info(f"  Hit Rate: {cache_metrics['hit_rate']:.1f}%") 