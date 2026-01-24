"""
Централизованная обработка ошибок.
"""
import logging
import traceback
from typing import Optional, Dict, Any, Callable
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Уровни серьезности ошибок"""
    LOW = "low"  # Незначительные ошибки, не влияющие на работу
    MEDIUM = "medium"  # Ошибки, которые могут повлиять на функциональность
    HIGH = "high"  # Критические ошибки, требующие внимания
    CRITICAL = "critical"  # Критические ошибки, останавливающие работу


@dataclass
class ErrorContext:
    """Контекст ошибки для логирования"""
    operation: str  # Название операции
    user_id: Optional[int] = None  # ID пользователя (если применимо)
    message_id: Optional[int] = None  # ID сообщения (если применимо)
    additional_data: Optional[Dict[str, Any]] = None  # Дополнительные данные
    severity: ErrorSeverity = ErrorSeverity.MEDIUM


async def handle_error(
    error: Exception,
    context: ErrorContext,
    send_notification: Optional[Callable] = None,
    notification_message: Optional[str] = None,
    reraise: bool = False
) -> None:
    """
    Централизованная обработка ошибок.
    
    :param error: Исключение
    :param context: Контекст ошибки
    :param send_notification: Функция для отправки уведомления пользователю (опционально)
    :param notification_message: Сообщение для пользователя (опционально)
    :param reraise: Повторно поднять исключение после обработки
    """
    # Формируем сообщение для логирования
    log_message_parts = [
        f"[{context.severity.value.upper()}] Ошибка в операции: {context.operation}"
    ]
    
    if context.user_id:
        log_message_parts.append(f"user_id={context.user_id}")
    if context.message_id:
        log_message_parts.append(f"message_id={context.message_id}")
    if context.additional_data:
        for key, value in context.additional_data.items():
            log_message_parts.append(f"{key}={value}")
    
    log_message_parts.append(f"error={type(error).__name__}: {str(error)}")
    log_message = " | ".join(log_message_parts)
    
    # Логируем в зависимости от серьезности
    if context.severity == ErrorSeverity.CRITICAL:
        logger.critical(log_message, exc_info=True)
    elif context.severity == ErrorSeverity.HIGH:
        logger.error(log_message, exc_info=True)
    elif context.severity == ErrorSeverity.MEDIUM:
        logger.warning(log_message, exc_info=True)
    else:
        logger.info(log_message, exc_info=True)
    
    # Отправляем уведомление пользователю, если указано
    if send_notification and notification_message:
        try:
            await send_notification(notification_message)
        except Exception as notify_error:
            logger.error(
                f"Не удалось отправить уведомление об ошибке: {notify_error}",
                exc_info=True
            )
    
    # Повторно поднимаем исключение, если нужно
    if reraise:
        raise


def handle_sync_error(
    error: Exception,
    context: ErrorContext,
    reraise: bool = False
) -> None:
    """
    Синхронная версия обработки ошибок.
    
    :param error: Исключение
    :param context: Контекст ошибки
    :param reraise: Повторно поднять исключение после обработки
    """
    log_message_parts = [
        f"[{context.severity.value.upper()}] Ошибка в операции: {context.operation}"
    ]
    
    if context.user_id:
        log_message_parts.append(f"user_id={context.user_id}")
    if context.message_id:
        log_message_parts.append(f"message_id={context.message_id}")
    if context.additional_data:
        for key, value in context.additional_data.items():
            log_message_parts.append(f"{key}={value}")
    
    log_message_parts.append(f"error={type(error).__name__}: {str(error)}")
    log_message = " | ".join(log_message_parts)
    
    if context.severity == ErrorSeverity.CRITICAL:
        logger.critical(log_message, exc_info=True)
    elif context.severity == ErrorSeverity.HIGH:
        logger.error(log_message, exc_info=True)
    elif context.severity == ErrorSeverity.MEDIUM:
        logger.warning(log_message, exc_info=True)
    else:
        logger.info(log_message, exc_info=True)
    
    if reraise:
        raise
