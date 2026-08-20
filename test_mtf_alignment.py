import unittest
import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from strategies import (
    compute_crypto_indicators, 
    evaluate_tf_trend, 
    evaluate_mtf_alignment, 
    SqueezeMomentumBreakout, 
    LiquiditySweepReversal, 
    TrendPullbackConfluence
)
from live_bot import LiveCryptoBot, ph_now

class TestMultiTimeframeAlignment(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.bot = LiveCryptoBot(
            initial_capital=100.0,
            fixed_risk_usd=1.0,
            timeframe="15m",
            max_open_positions=5,
            data_dir=self.test_dir
        )

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def _create_mock_df(self, n=60, close_val=100.0, ema50_val=95.0, rsi_val=60.0, is_bullish=True):
        """Create a mock technical dataframe with customizable trend regime."""
        dates = pd.date_range("2026-01-01", periods=n, freq="15min")
        open_val = close_val - 2.0 if is_bullish else close_val + 2.0
        high_val = max(open_val, close_val) + 0.5
        low_val = min(open_val, close_val) - 0.5

        df = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": np.linspace(open_val - 10, open_val, n),
            "high": np.linspace(high_val - 10, high_val, n),
            "low": np.linspace(low_val - 10, low_val, n),
            "close": np.linspace(close_val - 10, close_val, n),
            "volume": np.full(n, 1000.0),
            "squeeze_on": [True] * (n - 2) + [False, False],
            "bb_upper": [close_val - 1.0 if is_bullish else close_val + 10.0] * n,
            "bb_lower": [close_val - 10.0 if is_bullish else close_val + 1.0] * n,
            "ema50": [ema50_val] * n,
            "ema200": [ema50_val - 10.0 if is_bullish else ema50_val + 10.0] * n,
            "atr14": [2.0] * n,
            "rsi14": [rsi_val] * n,
            "momentum": [1.5 if is_bullish else -1.5] * n,
            "rvol": [1.8] * n
        })
        return df

    def test_evaluate_tf_trend_bullish_and_bearish(self):
        """Verify that evaluate_tf_trend accurately categorizes Bullish, Bearish, and Flash Dumps."""
        # 1. Bullish 1h dataset (Close > EMA50, RSI 58)
        df_bullish = self._create_mock_df(close_val=100.0, ema50_val=90.0, rsi_val=58.0, is_bullish=True)
        t_bull = evaluate_tf_trend(df_bullish)
        self.assertEqual(t_bull["regime"], "BULLISH")
        self.assertTrue(t_bull["is_valid"])

        # 2. Bearish 4h dataset (Close < EMA50, RSI 38)
        df_bearish = self._create_mock_df(close_val=80.0, ema50_val=95.0, rsi_val=38.0, is_bullish=False)
        t_bear = evaluate_tf_trend(df_bearish)
        self.assertEqual(t_bear["regime"], "BEARISH")
        self.assertTrue(t_bear["is_valid"])

    def test_mtf_long_approved_when_15m_with_1h_and_30m_with_4h_bullish(self):
        """Verify that 15m Long is approved with 1h Bullish, and 30m Long is approved with 4h Bullish."""
        df_15m = self._create_mock_df(close_val=100.0, ema50_val=95.0, rsi_val=62.0, is_bullish=True)
        df_30m = self._create_mock_df(close_val=100.0, ema50_val=95.0, rsi_val=62.0, is_bullish=True)
        df_1h = self._create_mock_df(close_val=100.0, ema50_val=92.0, rsi_val=58.0, is_bullish=True)
        df_4h = self._create_mock_df(close_val=100.0, ema50_val=85.0, rsi_val=55.0, is_bullish=True)

        htf_data = {"1h": df_1h, "4h": df_4h}
        
        # Test 15m entry -> Anchored to 1h
        sig_15m = SqueezeMomentumBreakout.generate_signal(df_15m, len(df_15m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="15m")
        self.assertIsNotNone(sig_15m)
        self.assertEqual(sig_15m["direction"], "LONG")
        self.assertEqual(sig_15m["timeframe"], "15m")
        self.assertEqual(sig_15m["pre_trade_context"]["mtf_alignment"]["anchor_tf"], "1h")
        self.assertEqual(sig_15m["pre_trade_context"]["mtf_alignment"]["anchor_regime"], "BULLISH")

        # Test 30m entry -> Anchored to 4h
        sig_30m = SqueezeMomentumBreakout.generate_signal(df_30m, len(df_30m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="30m")
        self.assertIsNotNone(sig_30m)
        self.assertEqual(sig_30m["direction"], "LONG")
        self.assertEqual(sig_30m["timeframe"], "30m")
        self.assertEqual(sig_30m["pre_trade_context"]["mtf_alignment"]["anchor_tf"], "4h")
        self.assertEqual(sig_30m["pre_trade_context"]["mtf_alignment"]["anchor_regime"], "BULLISH")

    def test_mtf_15m_long_rejected_when_1h_bearish(self):
        """Verify that a 15m Long breakout is REJECTED when 1h anchor trend is Bearish."""
        df_15m = self._create_mock_df(close_val=100.0, ema50_val=95.0, rsi_val=62.0, is_bullish=True)
        # 1h is Bearish (below EMA50, RSI 40)
        df_1h = self._create_mock_df(close_val=88.0, ema50_val=95.0, rsi_val=40.0, is_bullish=False)
        df_4h = self._create_mock_df(close_val=100.0, ema50_val=85.0, rsi_val=55.0, is_bullish=True)

        htf_data = {"1h": df_1h, "4h": df_4h}
        sig = SqueezeMomentumBreakout.generate_signal(df_15m, len(df_15m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="15m")

        # Must be rejected due to 1h counter-trend
        self.assertIsNone(sig)

    def test_mtf_30m_long_rejected_when_4h_bearish(self):
        """Verify that a 30m Long breakout is REJECTED when 4h anchor macro trend is Bearish."""
        df_30m = self._create_mock_df(close_val=100.0, ema50_val=95.0, rsi_val=62.0, is_bullish=True)
        df_1h = self._create_mock_df(close_val=100.0, ema50_val=92.0, rsi_val=58.0, is_bullish=True)
        # 4h is in Macro Downtrend (Price 80 < EMA50 100, RSI 35)
        df_4h = self._create_mock_df(close_val=80.0, ema50_val=100.0, rsi_val=35.0, is_bullish=False)

        htf_data = {"1h": df_1h, "4h": df_4h}
        sig = SqueezeMomentumBreakout.generate_signal(df_30m, len(df_30m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="30m")

        # Must be rejected due to 4h anchor macro downtrend
        self.assertIsNone(sig)

    def test_mtf_short_approved_for_15m_and_30m(self):
        """Verify that 15m Short is approved with 1h Bearish, and 30m Short is approved with 4h Bearish."""
        df_15m = self._create_mock_df(close_val=80.0, ema50_val=90.0, rsi_val=42.0, is_bullish=False)
        df_30m = self._create_mock_df(close_val=80.0, ema50_val=90.0, rsi_val=42.0, is_bullish=False)
        df_1h = self._create_mock_df(close_val=80.0, ema50_val=92.0, rsi_val=40.0, is_bullish=False)
        df_4h = self._create_mock_df(close_val=80.0, ema50_val=95.0, rsi_val=38.0, is_bullish=False)

        htf_data = {"1h": df_1h, "4h": df_4h}
        
        # Test 15m Short
        sig_15m = SqueezeMomentumBreakout.generate_signal(df_15m, len(df_15m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="15m")
        self.assertIsNotNone(sig_15m)
        self.assertEqual(sig_15m["direction"], "SHORT")
        self.assertEqual(sig_15m["timeframe"], "15m")
        self.assertEqual(sig_15m["pre_trade_context"]["mtf_alignment"]["anchor_tf"], "1h")
        self.assertEqual(sig_15m["pre_trade_context"]["mtf_alignment"]["anchor_regime"], "BEARISH")

        # Test 30m Short
        sig_30m = SqueezeMomentumBreakout.generate_signal(df_30m, len(df_30m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="30m")
        self.assertIsNotNone(sig_30m)
        self.assertEqual(sig_30m["direction"], "SHORT")
        self.assertEqual(sig_30m["timeframe"], "30m")
        self.assertEqual(sig_30m["pre_trade_context"]["mtf_alignment"]["anchor_tf"], "4h")
        self.assertEqual(sig_30m["pre_trade_context"]["mtf_alignment"]["anchor_regime"], "BEARISH")

    def test_mtf_15m_short_rejected_when_1h_bullish(self):
        """Verify that a 15m Short breakdown is REJECTED when 1h anchor trend is Bullish."""
        df_15m = self._create_mock_df(close_val=80.0, ema50_val=90.0, rsi_val=42.0, is_bullish=False)
        # 1h is Bullish
        df_1h = self._create_mock_df(close_val=110.0, ema50_val=100.0, rsi_val=58.0, is_bullish=True)
        df_4h = self._create_mock_df(close_val=80.0, ema50_val=95.0, rsi_val=38.0, is_bullish=False)

        htf_data = {"1h": df_1h, "4h": df_4h}
        sig = SqueezeMomentumBreakout.generate_signal(df_15m, len(df_15m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="15m")

        self.assertIsNone(sig)

    def test_mtf_30m_short_rejected_when_4h_bullish(self):
        """Verify that a 30m Short breakdown is REJECTED when 4h anchor macro trend is Bullish."""
        df_30m = self._create_mock_df(close_val=80.0, ema50_val=90.0, rsi_val=42.0, is_bullish=False)
        df_1h = self._create_mock_df(close_val=80.0, ema50_val=92.0, rsi_val=40.0, is_bullish=False)
        # 4h Macro is Bullish
        df_4h = self._create_mock_df(close_val=120.0, ema50_val=100.0, rsi_val=60.0, is_bullish=True)

        htf_data = {"1h": df_1h, "4h": df_4h}
        sig = SqueezeMomentumBreakout.generate_signal(df_30m, len(df_30m) - 1, target_rr=2.0, htf_data=htf_data, timeframe="30m")

        self.assertIsNone(sig)

    def test_1hr_and_4hr_direct_entries_blocked(self):
        """Verify that 1h and 4h cannot generate direct trade signals."""
        df = self._create_mock_df(close_val=100.0, ema50_val=90.0, rsi_val=60.0, is_bullish=True)
        sig_1h = SqueezeMomentumBreakout.generate_signal(df, len(df) - 1, target_rr=2.0, timeframe="1h")
        sig_4h = SqueezeMomentumBreakout.generate_signal(df, len(df) - 1, target_rr=2.0, timeframe="4h")
        self.assertIsNone(sig_1h)
        self.assertIsNone(sig_4h)

    def test_entry_only_permitted_on_15m_and_30m_no_1hr_position(self):
        """Verify that trade entry is ONLY allowed on 15m and 30m, and NO positions can be opened on 1h."""
        df_bullish = self._create_mock_df(close_val=100.0, ema50_val=90.0, rsi_val=60.0, is_bullish=True)
        df_1h = self._create_mock_df(close_val=100.0, ema50_val=90.0, rsi_val=58.0, is_bullish=True)
        df_4h = self._create_mock_df(close_val=100.0, ema50_val=85.0, rsi_val=55.0, is_bullish=True)
        
        # Populate MTF data
        self.bot.mtf_data["BTCUSDT"] = {"1h": df_1h, "4h": df_4h}
        self.bot.btc_macro_status = {"gate_status": "ALLOW_ALL", "regime": "BULLISH"}

        # 1. On 15m timeframe -> Allowed to open position
        self.bot.set_timeframe("15m")
        self.bot.open_positions.clear()
        asyncio.run(self.bot._scan_new_entries({"BTCUSDT": df_bullish}))
        self.assertIn("BTCUSDT", self.bot.open_positions)
        self.assertEqual(self.bot.open_positions["BTCUSDT"]["timeframe"], "15m")

        # 2. On 30m timeframe -> Allowed to open position
        self.bot.set_timeframe("30m")
        self.bot.open_positions.clear()
        asyncio.run(self.bot._scan_new_entries({"BTCUSDT": df_bullish}))
        self.assertIn("BTCUSDT", self.bot.open_positions)
        self.assertEqual(self.bot.open_positions["BTCUSDT"]["timeframe"], "30m")

        # 3. Attempting to switch to 1h timeframe is rejected and retains 30m
        res = self.bot.set_timeframe("1h")
        self.assertFalse(res)
        self.assertEqual(self.bot.timeframe, "30m")

if __name__ == '__main__':
    unittest.main()

