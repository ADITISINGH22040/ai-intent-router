import hashlib
from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from apps.router.services.cache_service import CacheService
from apps.router.tools.summary_tool import SummaryTool

LOC_MEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


@override_settings(CACHES=LOC_MEM_CACHES)
class SummaryToolTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    @patch("apps.router.tools.summary_tool.get_llm_provider")
    def test_generates_and_caches_summary(self, mock_get_provider):
        mock_get_provider.return_value = MagicMock(complete=MagicMock(return_value="Short summary."))
        text = "Long text to summarize."

        first = SummaryTool().execute({"text": text})
        second = SummaryTool().execute({"text": text})

        self.assertTrue(first["success"])
        self.assertFalse(first["meta"]["cached"])
        self.assertEqual(first["data"]["summary"], "Short summary.")
        self.assertEqual(first["data"]["source_length"], len(text))

        self.assertTrue(second["success"])
        self.assertTrue(second["meta"]["cached"])
        self.assertEqual(second["data"], first["data"])
        mock_get_provider.return_value.complete.assert_called_once()

    @patch("apps.router.tools.summary_tool.get_llm_provider")
    def test_uses_sha256_text_hash_in_cache_key(self, mock_get_provider):
        mock_get_provider.return_value = MagicMock(complete=MagicMock(return_value="Cached summary."))
        text = "Hash me."
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cache_key = CacheService.build_key("summary", text_hash)
        CacheService.set(
            cache_key,
            {"summary": "Cached summary.", "source_length": len(text)},
            timeout=86400,
        )

        result = SummaryTool().execute({"text": text})

        self.assertTrue(result["success"])
        self.assertTrue(result["meta"]["cached"])
        mock_get_provider.return_value.complete.assert_not_called()
