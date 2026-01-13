"""
Модуль для работы с AI-провайдерами через ProxyAPI.

Предоставляет клиенты для OpenAI и Google Gemini без привязки к Telegram.
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional, Final

from dotenv import load_dotenv
from openai import OpenAI
from google import genai as google_genai

load_dotenv()
logger = logging.getLogger(__name__)
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )

# Константы для OpenAI
OPENAI_ENV_VAR: Final[str] = "OPENAI_API_KEY"
OPENAI_BASE_URL: Final[str] = "https://api.proxyapi.ru/openai/v1"

# Константы для Gemini
GEMINI_ENV_VAR: Final[str] = "GEMINI_API_KEY"
GEMINI_BASE_URL: Final[str] = "https://api.proxyapi.ru/google"


def create_openai_client() -> OpenAI:
    """
    Создаёт и настраивает клиента OpenAI для работы через ProxyAPI.

    :raises RuntimeError: если переменная окружения OPENAI_API_KEY не задана.
    """
    api_key = os.getenv(OPENAI_ENV_VAR)
    if not api_key:
        logger.critical(
            "Необходимо установить переменную окружения %s в файле .env!",
            OPENAI_ENV_VAR,
        )
        raise RuntimeError(
            f"Переменная окружения {OPENAI_ENV_VAR} не установлена. "
            "Укажите ключ OpenAI в .env."
        )

    client = OpenAI(
        api_key=api_key,
        base_url=OPENAI_BASE_URL,
    )
    logger.info(
        "Клиент OpenAI успешно инициализирован (base_url=%s).",
        OPENAI_BASE_URL,
    )
    return client


def create_gemini_client() -> Optional[google_genai.Client]:
    """
    Создаёт и настраивает клиента Google Gemini для работы через ProxyAPI.

    :return: Экземпляр клиента Gemini или None, если ключ не задан или произошла ошибка инициализации.
    """
    api_key = os.getenv(GEMINI_ENV_VAR)
    if not api_key:
        logger.warning(
            "GEMINI_API_KEY не найден в .env! Функции Gemini будут недоступны."
        )
        return None

    try:
        client = google_genai.Client(
            api_key=api_key,
            http_options={
                "base_url": GEMINI_BASE_URL,
            },
        )
        logger.info(
            "Gemini клиент успешно инициализирован через ProxyAPI (base_url=%s).",
            GEMINI_BASE_URL,
        )
        return client
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось инициализировать Gemini клиент: %s", exc)
        return None


@dataclass
class AIClients:
    """
    Контейнер для клиентов ИИ-сервисов.
    """

    openai: OpenAI
    gemini: Optional[google_genai.Client]


def init_ai_clients() -> AIClients:
    """
    Инициализирует все клиенты внешних ИИ-сервисов.

    :raises RuntimeError: при ошибке инициализации обязательных клиентов (например, OpenAI).
    """
    openai_client = create_openai_client()
    gemini_client = create_gemini_client()
    return AIClients(openai=openai_client, gemini=gemini_client)
