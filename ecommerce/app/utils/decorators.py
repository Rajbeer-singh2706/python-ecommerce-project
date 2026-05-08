import time
import functools
import logging
from typing import Callable

logger = logging.getLogger("ecommerce")

def timer(func: Callable) -> Callable:
    """Log execution time of any function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        logger.debug(f"{func.__qualname__} completed in {elapsed*1000:.1f}ms")
        return result
    return wrapper

def retry(max_attempts: int = 3, delay: float = 0.5, exceptions=(Exception,)):
    """Retry a function on failure."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    logger.warning(f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}")
                    if attempt < max_attempts:
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator

def require_admin(func: Callable) -> Callable:
    """Guard: first arg must be a User with admin role."""
    @functools.wraps(func)
    def wrapper(self, user, *args, **kwargs):
        from app.models.user import UserRole
        if not hasattr(user, "role") or user.role != UserRole.admin:
            raise PermissionError(f"Admin access required for {func.__name__}.")
        return func(self, user, *args, **kwargs)
    return wrapper

def validate_stock(func: Callable) -> Callable:
    """Ensure product has enough stock before proceeding."""
    @functools.wraps(func)
    def wrapper(self, product, quantity: int, *args, **kwargs):
        if quantity <= 0:
            raise ValueError("Quantity must be a positive integer.")
        if product.stock < quantity:
            raise ValueError(f"Insufficient stock: {product.stock} available, {quantity} requested.")
        return func(self, product, quantity, *args, **kwargs)
    return wrapper

def transactional(func: Callable) -> Callable:
    """Wrap a service method in a DB transaction; rollback on error."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            result = func(self, *args, **kwargs)
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise
    return wrapper
