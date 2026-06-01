import hashlib
import logging
from typing import Any

from apps.router.llm import get_llm_provider
from apps.router.llm.exceptions import LLMProviderError
from apps.router.services.cache_service import SUMMARY_CACHE_TTL, CacheService
from apps.router.tools.base import BaseTool
from apps.router.user_errors import SUMMARY_UNAVAILABLE

logger = logging.getLogger(__name__)

SUMMARY_PROMPT_TEMPLATE = (
    "Summarize the following text in 2-4 concise sentences. "
    "Return only the summary with no preamble.\n\n{text}"
)


class SummaryTool(BaseTool):
    def __init__(self, cache_service: CacheService | None = None) -> None:
        self._cache = cache_service or CacheService()

    def execute(self, parameters: dict[str, Any]) -> dict[str, Any]:
        text = parameters["text"]
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cache_key = self._cache.build_key("summary", text_hash)

        cached_data = self._cache.get(cache_key)
        if cached_data is not None:
            return {
                "success": True,
                "data": cached_data,
                "errors": None,
                "meta": {"cached": True},
            }

        try:
            summary = get_llm_provider().complete(
                SUMMARY_PROMPT_TEMPLATE.format(text=text)
            )
        except LLMProviderError as exc:
            logger.warning("Summary generation failed error=%s", exc)
            return {
                "success": False,
                "data": None,
                "errors": {"summary": [SUMMARY_UNAVAILABLE]},
                "meta": {"cached": False},
            }

        data = {
            "summary": summary.strip(),
            "source_length": len(text),
        }
        self._cache.set(cache_key, data, SUMMARY_CACHE_TTL)
        return {
            "success": True,
            "data": data,
            "errors": None,
            "meta": {"cached": False},
        }
