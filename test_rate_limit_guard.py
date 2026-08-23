import unittest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
from data_loader import RateLimitManager, rate_limit_manager
from scanner import scan_market
from live_bot import LiveCryptoBot

class TestRateLimitGuard(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mgr = RateLimitManager(weight_limit_1m=1200)

    def test_update_from_headers(self):
        headers = {"x-mbx-used-weight-1m": "450"}
        self.mgr.update_from_headers(headers, latency_ms=45.2)
        
        telemetry = self.mgr.get_telemetry()
        self.assertEqual(telemetry["used_weight_1m"], 450)
        self.assertEqual(telemetry["weight_limit_1m"], 1200)
        self.assertEqual(telemetry["usage_pct"], 37.5)
        self.assertEqual(telemetry["status"], "HEALTHY")
        self.assertEqual(telemetry["badge_color"], "emerald")
        self.assertEqual(telemetry["last_latency_ms"], 45.2)
        self.assertEqual(telemetry["total_requests"], 1)

    def test_status_color_transitions(self):
        # 1. Healthy (<750)
        self.mgr.update_from_headers({"x-mbx-used-weight-1m": "600"})
        self.assertEqual(self.mgr.get_telemetry()["status"], "HEALTHY")
        self.assertEqual(self.mgr.get_telemetry()["badge_color"], "emerald")

        # 2. Paced (750 - 999)
        self.mgr.update_from_headers({"x-mbx-used-weight-1m": "850"})
        self.assertEqual(self.mgr.get_telemetry()["status"], "PACED")
        self.assertEqual(self.mgr.get_telemetry()["badge_color"], "amber")

        # 3. Defense (>=1000)
        self.mgr.update_from_headers({"x-mbx-used-weight-1m": "1080"})
        self.assertEqual(self.mgr.get_telemetry()["status"], "DEFENSE")
        self.assertEqual(self.mgr.get_telemetry()["badge_color"], "rose")

    def test_trigger_backoff(self):
        self.mgr.trigger_backoff(retry_after=10)
        telemetry = self.mgr.get_telemetry()
        self.assertTrue(telemetry["is_backed_off"])
        self.assertGreater(self.mgr.backoff_until_ts, time.time())

    async def test_adaptive_pacing_delay(self):
        # High weight triggers pacing
        self.mgr.used_weight_1m = 950
        t0 = time.perf_counter()
        await self.mgr.pace()
        elapsed = time.perf_counter() - t0
        self.assertGreaterEqual(elapsed, 0.08)

    async def test_cross_timeframe_kline_deduplication(self):
        """Verify that overlapping timeframes between scan_tfs and mtf_intervals are fetched only once."""
        bot = LiveCryptoBot(initial_capital=100.0, timeframe="triple")
        bot.symbols = ["BTCUSDT", "ETHUSDT"]

        scan_tfs = ["5m", "15m", "30m"]
        mtf_intervals = ["30m", "1h", "4h"]
        mtf_syms = ["BTCUSDT"]

        unique_requests = set()
        for tf in scan_tfs:
            for sym in bot.symbols:
                unique_requests.add((sym, tf))
        for mtf_tf in mtf_intervals:
            for sym in mtf_syms:
                unique_requests.add((sym, mtf_tf))

        # (BTCUSDT, 30m) is present in both primary (scan_tfs) and MTF (mtf_intervals)
        # Without deduplication: 6 primary + 3 MTF = 9 requests
        # With set deduplication: 2*3 + 2 = 8 unique requests
        self.assertEqual(len(unique_requests), 8)
        self.assertIn(("BTCUSDT", "30m"), unique_requests)
        self.assertIn(("BTCUSDT", "1h"), unique_requests)
        self.assertIn(("BTCUSDT", "4h"), unique_requests)

if __name__ == "__main__":
    unittest.main()
