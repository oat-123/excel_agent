import json
import os
import time
import logging
from datetime import datetime
from functools import wraps

ERROR_LOG_FILE = "brain/error_log.json"

def ensure_error_log():
    os.makedirs("brain", exist_ok=True)
    if not os.path.exists(ERROR_LOG_FILE):
        with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, ensure_ascii=False)

ensure_error_log()

def log_error(error_type, message, context=None, stack_trace=None):
    """Log error to file with context"""
    with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
        errors = json.load(f)
    
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "error_type": error_type,
        "message": message,
        "context": context or {},
        "stack_trace": stack_trace
    }
    errors.append(error_entry)
    
    with open(ERROR_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(errors[-100:], f, ensure_ascii=False, indent=2)  # Keep last 100 errors

def retry_with_backoff(max_retries=3, backoff_factor=1.5, default_return=None):
    """Decorator for automatic retry with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries >= max_retries:
                        log_error("retry_failed", str(e), {
                            "function": func.__name__,
                            "retries": retries
                        })
                        return default_return
                    wait_time = backoff_factor ** retries
                    time.sleep(wait_time)
            return default_return
        return wrapper
    return decorator

def safe_execute(func, default_return=None, error_context=None):
    """Execute function safely with error logging"""
    try:
        return func()
    except Exception as e:
        log_error(type(e).__name__, str(e), error_context)
        return default_return

def get_recent_errors(limit=10):
    """Get recent errors from log"""
    try:
        with open(ERROR_LOG_FILE, "r", encoding="utf-8") as f:
            errors = json.load(f)
        return errors[-limit:]
    except:
        return []