from django.core.cache import cache
from django.test import SimpleTestCase, override_settings

from apps.router.services.cache_service import CacheService

LOC_MEM_CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}


@override_settings(CACHES=LOC_MEM_CACHES)
class CacheServiceTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_build_key_joins_parts_with_colons(self):
        self.assertEqual(
            CacheService.build_key("weather", "London"),
            "weather:London",
        )
        self.assertEqual(
            CacheService.build_key("currency_rate", "USD", "EUR"),
            "currency_rate:USD:EUR",
        )

    def test_set_and_get_round_trip(self):
        CacheService.set("test:key", {"value": 1}, timeout=60)
        self.assertEqual(CacheService.get("test:key"), {"value": 1})

    def test_get_returns_none_for_missing_key(self):
        self.assertIsNone(CacheService.get("missing:key"))
