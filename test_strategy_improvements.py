import unittest
import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from strategies import compute_crypto_indicators, SqueezeMomentumBreakout, LiquiditySweepReversal, TrendPullbackConfluence
from live_bot import LiveCryptoBot, ph_now

class TestStrategyImprovements(unittest.TestCase):

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

    def _create_mock_dataframe(self, n=60, rsi_val=60.0, body_ratio=0.7, upper_wick_ratio=0.1, rvol_val=1.5):
        """Generate synthetic candle sequence with exact indicator properties for signal testing."""
        dates = pd.date_range("2026-01-01", periods=n, freq="15min")
        close_base = 100.0
        open_base = close_base - 2.0  # Bullish body
        high_base = close_base + 0.5
        low_base = open_base - 0.5
        
        df = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": np.linspace(80, open_base, n),
            "high": np.linspace(82, high_base, n),
            "low": np.linspace(79, low_base, n),
            "close": np.linspace(81, close_base, n),
            "volume": np.full(n, 1000.0),
            "squeeze_on": [True] * (n - 2) + [False, False],
            "bb_upper": [close_base - 1.0] * n,
            "bb_lower": [close_base - 20.0] * n,
            "ema50": [close_base - 10.0] * n,
            "ema200": [close_base - 20.0] * n,
            "atr14": [2.0] * n,
            "rsi14": [rsi_val] * n,
            "momentum": [1.5] * n,
            "rvol": [rvol_val] * n
        })
        return df

    def test_rsi_safe_corridor_long_overbought_rejection(self):
        """Verify that Squeeze Breakout rejects LONGs when RSI > 68 (overbought blow-off)."""
        # 1. Normal safe RSI = 62.0 -> Should trigger
        df_safe = self._create_mock_dataframe(rsi_val=62.0)
        sig_safe = SqueezeMomentumBreakout.generate_signal(df_safe, len(df_safe) - 1, target_rr=2.0)
        self.assertIsNotNone(sig_safe)
        self.assertEqual(sig_safe["direction"], "LONG")

        # 2. Overbought RSI = 74.5 (like the BICOUSDT lose streak) -> Must be REJECTED
        df_overbought = self._create_mock_dataframe(rsi_val=74.5)
        sig_overbought = SqueezeMomentumBreakout.generate_signal(df_overbought, len(df_overbought) - 1, target_rr=2.0)
        self.assertIsNone(sig_overbought)

    def test_rsi_safe_corridor_short_oversold_rejection(self):
        """Verify that Squeeze Breakout rejects SHORTs when RSI < 32 (oversold bottom)."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        df_short = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": np.linspace(120, 100, 60),
            "high": np.linspace(121, 100.5, 60),
            "low": np.linspace(119, 97.5, 60),
            "close": np.linspace(120, 98, 60),
            "volume": np.full(60, 1000.0),
            "squeeze_on": [True] * 58 + [False, False],
            "bb_upper": [110.0] * 60,
            "bb_lower": [99.0] * 60,
            "ema50": [105.0] * 60,
            "ema200": [110.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [25.0] * 60,  # Deeply oversold
            "momentum": [-1.5] * 60,
            "rvol": [2.0] * 60
        })
        sig = SqueezeMomentumBreakout.generate_signal(df_short, len(df_short) - 1, target_rr=2.0)
        self.assertIsNone(sig)

    def test_candle_body_filter_rejects_wick_traps(self):
        """Verify that candle with huge upper rejection wick is rejected as a trap."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        # Long candle with 80% upper wick (shooting star / wick trap)
        df_wick = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [100.0] * 59 + [100.0],
            "high": [101.0] * 59 + [110.0],  # Giant wick to 110
            "low": [99.0] * 59 + [99.5],
            "close": [100.5] * 59 + [101.0],  # Closed near bottom (small body, 90% upper wick)
            "volume": np.full(60, 1000.0),
            "squeeze_on": [True] * 58 + [False, False],
            "bb_upper": [100.5] * 60,
            "bb_lower": [90.0] * 60,
            "ema50": [95.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [58.0] * 60,
            "momentum": [1.0] * 60,
            "rvol": [2.0] * 60
        })
        sig = SqueezeMomentumBreakout.generate_signal(df_wick, len(df_wick) - 1, target_rr=2.0)
        self.assertIsNone(sig)

    def test_adaptive_atr_noise_buffer(self):
        """Verify that micro-cap assets enforce minimum 0.8% stop-loss buffer."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        # Low price $0.018, tiny ATR 0.00001
        df_micro = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": np.linspace(0.010, 0.0175, 60),
            "high": np.linspace(0.011, 0.0182, 60),
            "low": np.linspace(0.009, 0.0174, 60),
            "close": np.linspace(0.010, 0.0180, 60),
            "volume": np.full(60, 1000.0),
            "squeeze_on": [True] * 58 + [False, False],
            "bb_upper": [0.0175] * 60,
            "bb_lower": [0.0120] * 60,
            "ema50": [0.0150] * 60,
            "atr14": [0.00001] * 60,  # Unusually tiny ATR
            "rsi14": [58.0] * 60,
            "momentum": [0.001] * 60,
            "rvol": [2.0] * 60
        })
        sig = SqueezeMomentumBreakout.generate_signal(df_micro, len(df_micro) - 1, target_rr=2.0)
        self.assertIsNotNone(sig)
        # Risk distance must be at least 0.8% of $0.018 = 0.000144
        self.assertGreaterEqual(sig["risk_distance"], 0.018 * 0.008)

    def test_portfolio_circuit_breaker_activates_on_3_consecutive_losses(self):
        """Verify that 3 consecutive losses activate the 30-minute portfolio circuit breaker."""
        self.assertIsNone(self.bot.circuit_breaker_until)
        
        # Add 3 losses in a row
        for i in range(1, 4):
            self.bot.open_positions[f"COIN{i}"] = {
                "trade_id": i,
                "symbol": f"COIN{i}",
                "direction": "LONG",
                "entry_time": 1700000000,
                "entry_time_str": "2026-08-20 12:00:00",
                "entry_price": 10.0,
                "sl_price": 9.0,
                "tp_price": 12.0,
                "risk_distance": 1.0,
                "risk_amount_usd": 1.0,
                "target_rr": 2.0,
                "bars_held": 1,
                "pre_trade_context": {"reason": "test"}
            }
            asyncio.run(self.bot._close_position(f"COIN{i}", exit_price=9.0, exit_time=1700000060 * i, outcome="LOSS"))

        # Circuit breaker should now be active
        self.assertIsNotNone(self.bot.circuit_breaker_until)
        self.assertGreater(self.bot.circuit_breaker_until, ph_now())

        # Test that scan_new_entries does NOT enter new trades while circuit breaker is active
        df_trigger = self._create_mock_dataframe(rsi_val=60.0)
        asyncio.run(self.bot._scan_new_entries({"BTCUSDT": df_trigger}))
        self.assertNotIn("BTCUSDT", self.bot.open_positions)

    def test_quarantine_persists_across_server_restart(self):
        """Verify that symbol loss cooldowns persist through save_state and load_state."""
        future_time = ph_now() + timedelta(minutes=45)
        self.bot.symbol_loss_cooldowns["BICOUSDT"] = future_time
        self.bot.save_state()

        # Create new bot instance from same data_dir
        rebooted_bot = LiveCryptoBot(data_dir=self.test_dir)
        self.assertIn("BICOUSDT", rebooted_bot.symbol_loss_cooldowns)
        self.assertAlmostEqual(
            rebooted_bot.symbol_loss_cooldowns["BICOUSDT"].timestamp(),
            future_time.timestamp(),
            delta=2
        )

if __name__ == '__main__':
    unittest.main()
