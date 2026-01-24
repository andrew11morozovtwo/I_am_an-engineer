"""
Общие утилиты для приложения.
"""
from app.common.error_handler import handle_error, ErrorContext
from app.common.logger import setup_logging, get_logger

__all__ = ['handle_error', 'ErrorContext', 'setup_logging', 'get_logger']
