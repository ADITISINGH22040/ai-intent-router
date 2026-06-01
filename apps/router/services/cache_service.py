import logging
from typing import Any

from django.core.cache import cache

WEATHER_CACHE_TTL = 60 * 60
CURRENCY_RATE_CACHE_TTL = 60 * 60
SUMMARY_CACHE_TTL = 60 * 60 * 24

logger = logging.getLogger(__name__)


class CacheService:
    """Redis-backed cache access via Django's cache framework."""

    @staticmethod
    def build_key(*parts: str) -> str:
        return ":".join(str(part) for part in parts)

    @staticmethod
    def get(key: str) -> Any | None:
        value = cache.get(key)
        if value is not None:
            logger.info("Cache hit key=%s", key)
        else:
            logger.info("Cache miss key=%s", key)
        return value

    @staticmethod
    def set(key: str, value: Any, timeout: int) -> None:
        cache.set(key, value, timeout)
        logger.info("Cache set key=%s ttl=%ss", key, timeout)
