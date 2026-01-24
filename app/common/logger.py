"""
Настройка структурированного логирования.
"""
import logging
import sys
from typing import Optional


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    include_timestamp: bool = True
) -> None:
    """
    Настраивает структурированное логирование для приложения.
    
    :param level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    :param format_string: Кастомный формат строки (если None, используется стандартный)
    :param include_timestamp: Включать ли временную метку в логи
    """
    if format_string is None:
        if include_timestamp:
            format_string = (
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            )
        else:
            format_string = (
                "%(levelname)-8s | %(name)s | %(message)s"
            )
    
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с указанным именем.
    
    :param name: Имя логгера (обычно __name__)
    :return: Настроенный логгер
    """
    return logging.getLogger(name)
