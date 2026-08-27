import unittest
import asyncio
import time
from unittest.mock import MagicMock, AsyncMock, patch
import pandas as pd
import numpy as np

import scanner
from scanner import (
    filter_liquid_usdt_pairs,
    fetch_top_usdt_pairs,
    fetch_symbol_htf_data,
    scan_market_multi_tf,
    DEFAULT_TOP_COINS,
    EXCLUDED_KEYWORDS,
    _top_pairs_cache
)


class TestScannerLiquidityAndMTF(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Reset cache before each test
        _top_pairs_cache["timestamp"] = 0.0
        _top_pairs_cache["pairs"] = []

    def test_filter_liquid_usdt_pairs_volume_floor(self):
        """
        Verify that filter_liquid_usdt_pairs correctly includes symbols >= $15M quoteVolume
        and strictly excludes low-volume tokens (< $15M) and non-USDT / leveraged pairs.
        """
        mock_tickers = [
            {"symbol": "BTCUSDT", "quoteVolume": "1200000000.0"},  # $1.2B -> PASS
            {"symbol": "ETHUSDT", "quoteVolume": "800000000.0"},   # $800M -> PASS
            {"symbol": "SOLUSDT", "quoteVolume": "350000000.0"},   # $350M -> PASS
            {"symbol": "AAVEUSDT", "quoteVolume": "25000000.0"},   # $25M -> PASS
            {"symbol": "EXACT15MUSDT", "quoteVolume": "15000000.0"}, # $15M -> PASS (boundary)
            {"symbol": "BELOW15MUSDT", "quoteVolume": "14999999.0"}, # <$15M -> EXCLUDE
            {"symbol": "HOMEUSDT", "quoteVolume": "1200000.0"},    # $1.2M -> EXCLUDE (<$15M)
            {"symbol": "SNXXBUSDT", "quoteVolume": "450000.0"},    # $450K -> EXCLUDE (<$15M)
            {"symbol": "BICOUSDT", "quoteVolume": "8500000.0"},    # $8.5M -> EXCLUDE (<$15M)
        ]

        result = filter_liquid_usdt_pairs(mock_tickers, min_quote_volume=15000000.0)

        # Confirm liquid tokens >= $15M are included
        self.assertIn("BTCUSDT", result)
        self.assertIn("ETHUSDT", result)
        self.assertIn("SOLUSDT", result)
        self.assertIn("AAVEUSDT", result)
        self.assertIn("EXACT15MUSDT", result)

        # Confirm low-volume tokens < $15M are excluded
        self.assertNotIn("HOMEUSDT", result)
        self.assertNotIn("SNXXBUSDT", result)
        self.assertNotIn("BICOUSDT", result)
        self.assertNotIn("BELOW15MUSDT", result)

        # Confirm sorted in descending order of quoteVolume
        expected_order = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AAVEUSDT", "EXACT15MUSDT"]
        self.assertEqual(result, expected_order)

    def test_filter_liquid_usdt_pairs_exclusions_and_edge_cases(self):
        """
        Verify that stablecoins, leveraged tokens, non-USDT pairs, and malformed items are filtered out.
        """
        mock_tickers = [
            {"symbol": "USDCUSDT", "quoteVolume": "2000000000.0"}, # Stablecoin in EXCLUDED_KEYWORDS -> EXCLUDE
            {"symbol": "FDUSDUSDT", "quoteVolume": "3000000000.0"}, # Stablecoin in EXCLUDED_KEYWORDS -> EXCLUDE
            {"symbol": "BTCUPUSDT", "quoteVolume": "50000000.0"},  # Leveraged token -> EXCLUDE
            {"symbol": "BTCDOWNUSDT", "quoteVolume": "40000000.0"},# Leveraged token -> EXCLUDE
            {"symbol": "ETHBTC", "quoteVolume": "100000000.0"},    # Non-USDT -> EXCLUDE
            {"symbol": "SOLBNB", "quoteVolume": "80000000.0"},     # Non-USDT -> EXCLUDE
            {"symbol": "VALIDUSDT", "quoteVolume": "20000000.0"},  # Valid -> PASS
            {"symbol": "CORRUPTUSDT", "quoteVolume": "bad_number"},# Malformed float -> EXCLUDE
            {"symbol": "MISSINGUSDT"},                             # Missing quoteVolume -> EXCLUDE
            None,                                                   # None item -> EXCLUDE
            "not_a_dict"                                            # Invalid type -> EXCLUDE
        ]

        result = filter_liquid_usdt_pairs(mock_tickers, min_quote_volume=15000000.0)
        self.assertEqual(result, ["VALIDUSDT"])

    def test_filter_empty_or_invalid_input(self):
        """Verify graceful handling of empty or non-list input."""
        self.assertEqual(filter_liquid_usdt_pairs([]), [])
        self.assertEqual(filter_liquid_usdt_pairs(None), [])
        self.assertEqual(filter_liquid_usdt_pairs("invalid"), [])

    async def test_fetch_top_usdt_pairs_api_success(self):
        """Verify fetch_top_usdt_pairs queries API, applies liquid filtering, and respects limit."""
        mock_data = [
            {"symbol": "BTCUSDT", "quoteVolume": "500000000.0"},
            {"symbol": "ETHUSDT", "quoteVolume": "400000000.0"},
            {"symbol": "SOLUSDT", "quoteVolume": "300000000.0"},
            {"symbol": "AAVEUSDT", "quoteVolume": "30000000.0"},
            {"symbol": "BICOUSDT", "quoteVolume": "5000000.0"}, # low volume
        ]

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value=mock_data)

        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_resp

        with patch("scanner.get_http_session", return_value=mock_session):
            pairs = await fetch_top_usdt_pairs(limit=3, min_quote_volume=15000000.0)
            self.assertEqual(pairs, ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

    async def test_fetch_top_usdt_pairs_fallback_on_api_error(self):
        """Verify fallback to DEFAULT_TOP_COINS when Binance API fails or raises exception."""
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection timeout / network error")

        with patch("scanner.get_http_session", return_value=mock_session):
            pairs = await fetch_top_usdt_pairs(limit=10)
            self.assertEqual(pairs, DEFAULT_TOP_COINS[:10])

    async def test_fetch_symbol_htf_data(self):
        """Verify fetch_symbol_htf_data returns dictionary with pre-computed indicators for 30m, 1h, 4h."""
        def make_mock_df(n=100):
            df = pd.DataFrame({
                "time": [1000 + i * 60 for i in range(n)],
                "open": [100.0 + i * 0.1 for i in range(n)],
                "high": [101.0 + i * 0.1 for i in range(n)],
                "low": [99.0 + i * 0.1 for i in range(n)],
                "close": [100.5 + i * 0.1 for i in range(n)],
                "volume": [5000.0 + i * 10 for i in range(n)],
                "taker_buy_base": [2600.0 + i * 5 for i in range(n)],
            })
            return df

        async def mock_fetch_klines(session, symbol, interval="30m", limit=120):
            return make_mock_df(60)

        mock_session = MagicMock()
        with patch("scanner.fetch_klines", side_effect=mock_fetch_klines):
            htf_data = await fetch_symbol_htf_data(mock_session, "BTCUSDT", intervals=["30m", "1h", "4h"])
            
            self.assertIn("30m", htf_data)
            self.assertIn("1h", htf_data)
            self.assertIn("4h", htf_data)
            self.assertIn("ema50", htf_data["30m"].columns)
            self.assertIn("rsi14", htf_data["1h"].columns)
            self.assertIn("atr14", htf_data["4h"].columns)

    async def test_scan_market_multi_tf_guarantees_htf_data_pipeline(self):
        """Verify that scan_market_multi_tf provides htf_data with 30m, 1h, 4h for each scanned symbol."""
        def make_mock_df(n=80):
            df = pd.DataFrame({
                "time": [1000 + i * 60 for i in range(n)],
                "open": [100.0 + i * 0.1 for i in range(n)],
                "high": [101.0 + i * 0.1 for i in range(n)],
                "low": [99.0 + i * 0.1 for i in range(n)],
                "close": [100.5 + i * 0.1 for i in range(n)],
                "volume": [5000.0 + i * 10 for i in range(n)],
                "taker_buy_base": [2600.0 + i * 5 for i in range(n)],
            })
            return df

        async def mock_fetch_top(limit=50, min_quote_volume=15000000.0):
            return ["BTCUSDT", "ETHUSDT"]

        async def mock_fetch_klines(session, symbol, interval="15m", limit=250):
            return make_mock_df(80)

        with patch("scanner.fetch_top_usdt_pairs", side_effect=mock_fetch_top), \
             patch("scanner.fetch_klines", side_effect=mock_fetch_klines), \
             patch("scanner.get_http_session", return_value=MagicMock()):

            results = await scan_market_multi_tf(
                intervals=["30m", "1h", "4h"],
                primary_interval="15m",
                limit_pairs=2,
                min_quote_volume=15000000.0
            )

            self.assertEqual(len(results), 2)
            for res in results:
                self.assertIn("htf_data", res)
                self.assertIn("30m", res["htf_data"])
                self.assertIn("1h", res["htf_data"])
                self.assertIn("4h", res["htf_data"])
                self.assertIn("mtf_30m", res)
                self.assertIn("mtf_1h", res)
                self.assertIn("mtf_4h", res)


if __name__ == "__main__":
    unittest.main()
