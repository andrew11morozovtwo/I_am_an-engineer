"""
Application services package.
"""
# Глобальные объекты для хранения сервисов
_comment_service = None
_ai_clients = None


def set_comment_service(service):
    """Устанавливает глобальный comment_service."""
    global _comment_service
    _comment_service = service


def get_comment_service():
    """Получает глобальный comment_service."""
    return _comment_service


def set_ai_clients(clients):
    """Устанавливает глобальные AI клиенты."""
    global _ai_clients
    _ai_clients = clients


def get_ai_clients():
    """Получает глобальные AI клиенты."""
    return _ai_clients
