from test_causal_fixtures import signal_with_history, simulation_fixture
import unittest
import numpy as np
import pandas as pd
from strategies import (
    compute_crypto_indicators, 
    SqueezeMomentumBreakout, 
    LiquiditySweepReversal, 
    TrendPullbackConfluence, 
    format_price_precision,
    StrategyBase
)
from sim_engine import simulate_strategy_on_dataframe, diagnose_trade_outcome, compile_simulation_metrics

class TestProfitabilityAndRR(unittest.TestCase):

    def _generate_synthetic_df(self, n=100, with_taker_buy=False, seed=42):
        """Generate synthetic OHLCV dataframe with realistic price movements."""
        np.random.seed(seed)
        dates = pd.date_range("2026-01-01", periods=n, freq="15min")
        returns = np.random.normal(0.0005, 0.01, n)
        close_prices = 100.0 * np.exp(np.cumsum(returns))
        high_prices = close_prices * (1.0 + np.abs(np.random.normal(0.005, 0.003, n)))
        low_prices = close_prices * (1.0 - np.abs(np.random.normal(0.005, 0.003, n)))
        open_prices = low_prices + (high_prices - low_prices) * np.random.uniform(0.2, 0.8, n)
        volume = np.random.uniform(500.0, 5000.0, n)
        data = {
            "time": [int(d.timestamp()) for d in dates],
            "open": open_prices,
            "high": high_prices,
            "low": low_prices,
            "close": close_prices,
            "volume": volume,
        }
        if with_taker_buy:
            data["taker_buy_base"] = volume * np.random.uniform(0.3, 0.7, n)
        return pd.DataFrame(data)

    def test_new_feature_indicators(self):
        """Verify compute_crypto_indicators calculates bb_width_percentile, atr_expansion, and buyer_ratio."""
        df = self._generate_synthetic_df(n=100, with_taker_buy=False)
        res = compute_crypto_indicators(df)
        self.assertIn("bb_width_percentile", res.columns)
        self.assertIn("atr_expansion", res.columns)
        self.assertIn("buyer_ratio", res.columns)
        self.assertFalse(res["bb_width_percentile"].isna().any())
        self.assertFalse(np.isinf(res["bb_width_percentile"]).any())
        self.assertFalse(res["atr_expansion"].isna().any())
        self.assertFalse(np.isinf(res["atr_expansion"]).any())
        self.assertFalse(res["buyer_ratio"].isna().any())
        self.assertFalse(np.isinf(res["buyer_ratio"]).any())
        self.assertTrue((res["bb_width_percentile"] >= 0.0).all())
        self.assertTrue((res["bb_width_percentile"] <= 100.0).all())
        self.assertEqual(res["bb_width_percentile"].iloc[0], 50.0)
        self.assertEqual(res["bb_width_percentile"].iloc[48], 50.0)
        self.assertTrue((res["atr_expansion"] > 0.0).all())
        self.assertEqual(res["atr_expansion"].iloc[0], 1.0)
        self.assertTrue((res["buyer_ratio"] >= 0.0).all())
        self.assertTrue((res["buyer_ratio"] <= 100.0).all())

    def test_buyer_ratio_with_taker_buy_volume(self):
        """Verify buyer_ratio uses (taker_buy_base / volume) * 100 when taker_buy_base is present."""
        df = self._generate_synthetic_df(n=80, with_taker_buy=True)
        res = compute_crypto_indicators(df)
        expected = (df["taker_buy_base"] / df["volume"] * 100.0).fillna(50.0)
        np.testing.assert_allclose(res["buyer_ratio"].values, expected.values, rtol=1e-5)

    def test_bb_width_percentile_ranking_logic(self):
        """Verify that bb_width_percentile computes valid quantile rank."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        closes = [100.0 + i * 2.0 for i in range(60)]
        df = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": closes,
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [1000.0] * 60
        })
        res = compute_crypto_indicators(df)
        self.assertTrue(0.0 <= res["bb_width_percentile"].iloc[-1] <= 100.0)
        self.assertFalse(res["bb_width_percentile"].isna().any())

    def test_zero_division_and_edge_cases(self):
        """Verify robust handling of zero ranges and zero volumes."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        df_flat = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [100.0] * 60,
            "high": [100.0] * 60,
            "low": [100.0] * 60,
            "close": [100.0] * 60,
            "volume": [0.0] * 60
        })
        res = compute_crypto_indicators(df_flat)
        self.assertFalse(res["buyer_ratio"].isna().any())
        self.assertFalse(res["atr_expansion"].isna().any())
        self.assertFalse(res["bb_width_percentile"].isna().any())

    def test_squeeze_filters_wick_traps_and_low_volume(self):
        """Verify SqueezeMomentumBreakout filters out high-wick traps, low volume, weak buyer ratio, and uncompressed bands."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        
        # Base template for a breakout candidate
        def make_base_df():
            return pd.DataFrame({
                "time": [int(d.timestamp()) for d in dates],
                "open": [98.0] * 59 + [98.0],
                "high": [101.0] * 59 + [100.5],
                "low": [97.0] * 59 + [97.5],
                "close": [99.0] * 59 + [100.0],
                "volume": np.full(60, 1000.0),
                "squeeze_on": [True] * 58 + [False, False],
                "bb_upper": [99.0] * 60,
                "bb_lower": [85.0] * 60,
                "ema20": [96.0] * 60,
                "ema50": [92.0] * 60,
                "ema200": [85.0] * 60,
                "atr14": [2.0] * 60,
                "rsi14": [56.0] * 60,
                "momentum": [1.2] * 60,
                "rvol": [2.0] * 60,
                "buyer_ratio": [60.0] * 60,
                "bb_width_percentile": [20.0] * 60,
                "atr_expansion": [1.20] * 60,
                "adx14": [28.0] * 60,
                "hurst": [0.58] * 60,
                "swing_high_5": [99.0] * 60
            })

        # 1. Low volume rejection: rvol = 1.30 (< 1.60)
        df_low_vol = make_base_df()
        df_low_vol.loc[59, "rvol"] = 1.30
        self.assertIsNone(signal_with_history(SqueezeMomentumBreakout, df_low_vol, 59, timeframe="15m"))

        # 2. Low buyer ratio rejection for Long: buyer_ratio = 48.0 (< 53.0)
        df_low_buyer = make_base_df()
        df_low_buyer.loc[59, "buyer_ratio"] = 48.0
        self.assertIsNone(signal_with_history(SqueezeMomentumBreakout, df_low_buyer, 59, timeframe="15m"))

        # 3. High upper wick rejection (wick trap): upper wick ratio = (105.0 - 100.0) / (105.0 - 97.5) = 5.0 / 7.5 = 0.667 (> 0.32)
        df_wick_trap = make_base_df()
        df_wick_trap.loc[59, "high"] = 105.0
        df_wick_trap.loc[59, "close"] = 100.0
        df_wick_trap.loc[59, "open"] = 98.0
        df_wick_trap.loc[59, "low"] = 97.5
        self.assertIsNone(signal_with_history(SqueezeMomentumBreakout, df_wick_trap, 59, timeframe="15m"))

        # 4. Small body ratio rejection: body ratio = (100.2 - 100.0) / (102.0 - 98.0) = 0.2 / 4.0 = 0.05 (< 0.40)
        df_small_body = make_base_df()
        df_small_body.loc[59, "open"] = 100.0
        df_small_body.loc[59, "close"] = 100.2
        df_small_body.loc[59, "high"] = 102.0
        df_small_body.loc[59, "low"] = 98.0
        self.assertIsNone(signal_with_history(SqueezeMomentumBreakout, df_small_body, 59, timeframe="15m"))

        # 5. Non-compressed bandwidth and no ATR expansion: bb_width_percentile = 65.0 (> 30.0) and atr_expansion = 0.98 (< 1.05)
        df_no_squeeze_expansion = make_base_df()
        df_no_squeeze_expansion.loc[59, "bb_width_percentile"] = 65.0
        df_no_squeeze_expansion.loc[59, "atr_expansion"] = 0.98
        self.assertIsNone(signal_with_history(SqueezeMomentumBreakout, df_no_squeeze_expansion, 59, timeframe="15m"))

        # 6. Short setup: high lower wick rejection (wick trap for shorts): lower wick ratio = (98.0 - 92.0) / (100.5 - 92.0) = 6.0 / 8.5 = 0.706 (> 0.32)
        df_short_wick = make_base_df()
        df_short_wick["momentum"] = [-1.2] * 60
        df_short_wick["close"] = [101.0] * 59 + [98.0]
        df_short_wick["open"] = [102.0] * 59 + [100.0]
        df_short_wick["high"] = [103.0] * 59 + [100.5]
        df_short_wick["low"] = [99.0] * 59 + [92.0]
        df_short_wick["ema50"] = [105.0] * 60
        df_short_wick["bb_lower"] = [99.0] * 60
        df_short_wick["buyer_ratio"] = [40.0] * 60
        df_short_wick["rsi14"] = [45.0] * 60
        df_short_wick["swing_low_5"] = [99.0] * 60
        self.assertIsNone(signal_with_history(SqueezeMomentumBreakout, df_short_wick, 59, timeframe="15m"))

        # 7. Short setup: buyer_ratio = 52.0 (> 47.0)
        df_short_buyer = make_base_df()
        df_short_buyer["momentum"] = [-1.2] * 60
        df_short_buyer["close"] = [101.0] * 59 + [98.0]
        df_short_buyer["open"] = [102.0] * 59 + [100.0]
        df_short_buyer["high"] = [103.0] * 59 + [100.5]
        df_short_buyer["low"] = [99.0] * 59 + [97.5]
        df_short_buyer["ema50"] = [105.0] * 60
        df_short_buyer["bb_lower"] = [99.0] * 60
        df_short_buyer["buyer_ratio"] = [52.0] * 60
        df_short_buyer["rsi14"] = [45.0] * 60
        df_short_buyer["swing_low_5"] = [99.0] * 60
        self.assertIsNone(signal_with_history(SqueezeMomentumBreakout, df_short_buyer, 59, timeframe="15m"))

    def test_valid_squeeze_signal_structure(self):
        """Verify that a valid squeeze signal produces tp1_price (1.50R), target_rr (3.50R default), sl_price, and complete pre-trade context."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        
        # Valid LONG squeeze setup
        df_long = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [95.0] * 59 + [98.0],
            "high": [98.0] * 59 + [100.5],
            "low": [94.0] * 59 + [97.5],
            "close": [96.0] * 59 + [100.0],
            "volume": np.full(60, 1000.0),
            "squeeze_on": [True] * 58 + [False, False],
            "bb_upper": [99.0] * 60,
            "bb_lower": [85.0] * 60,
            "ema20": [96.0] * 60,
            "ema50": [92.0] * 60,
            "ema200": [85.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [55.0] * 60,
            "momentum": [1.2] * 60,
            "rvol": [2.2] * 60,
            "buyer_ratio": [62.0] * 60,
            "bb_width_percentile": [18.0] * 60,
            "atr_expansion": [1.25] * 60,
            "adx14": [28.0] * 60,
            "hurst": [0.58] * 60,
            "swing_high_5": [99.0] * 60
        })
        sig_long = signal_with_history(SqueezeMomentumBreakout, df_long, 59, timeframe="15m")
        self.assertIsNotNone(sig_long)
        self.assertEqual(sig_long["strategy"], "Squeeze_Momentum_Breakout")
        self.assertEqual(sig_long["direction"], "LONG")
        self.assertEqual(sig_long["timeframe"], "15m")
        self.assertEqual(sig_long["target_rr"], 3.5)
        self.assertEqual(sig_long["tp1_rr"], 1.5)
        self.assertEqual(sig_long["entry_price"], 100.0)
        
        # Risk distance and prices
        risk_dist = sig_long["risk_distance"]
        expected_sl = format_price_precision(100.0 - risk_dist)
        expected_tp1 = format_price_precision(100.0 + 1.5 * risk_dist)
        expected_tp = format_price_precision(100.0 + 3.5 * risk_dist)
        self.assertEqual(sig_long["sl_price"], expected_sl)
        self.assertEqual(sig_long["tp1_price"], expected_tp1)
        self.assertEqual(sig_long["tp_price"], expected_tp)
        self.assertLess(sig_long["sl_price"], sig_long["entry_price"])
        self.assertGreater(sig_long["tp1_price"], sig_long["entry_price"])
        self.assertGreater(sig_long["tp_price"], sig_long["tp1_price"])
        
        # Pre-trade context verification
        ctx = sig_long["pre_trade_context"]
        self.assertEqual(ctx["rvol"], 2.2)
        self.assertEqual(ctx["buyer_ratio"], 62.0)
        self.assertEqual(ctx["bb_width_percentile"], 18.0)
        self.assertEqual(ctx["atr_expansion"], 1.25)
        self.assertEqual(ctx["body_ratio"], 0.67)
        self.assertEqual(ctx["upper_wick_ratio"], 0.17)

        # Valid SHORT squeeze setup
        df_short = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [105.0] * 59 + [100.0],
            "high": [106.0] * 59 + [100.5],
            "low": [102.0] * 59 + [97.5],
            "close": [104.0] * 59 + [98.0],
            "volume": np.full(60, 1000.0),
            "squeeze_on": [True] * 58 + [False, False],
            "bb_upper": [115.0] * 60,
            "bb_lower": [99.0] * 60,
            "ema20": [102.0] * 60,
            "ema50": [105.0] * 60,
            "ema200": [110.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [46.0] * 60,
            "momentum": [-1.2] * 60,
            "rvol": [2.0] * 60,
            "buyer_ratio": [42.0] * 60,
            "bb_width_percentile": [22.0] * 60,
            "atr_expansion": [1.15] * 60,
            "adx14": [28.0] * 60,
            "hurst": [0.58] * 60,
            "swing_low_5": [99.0] * 60
        })
        sig_short = signal_with_history(SqueezeMomentumBreakout, df_short, 59, timeframe="15m")
        self.assertIsNotNone(sig_short)
        self.assertEqual(sig_short["strategy"], "Squeeze_Momentum_Breakout")
        self.assertEqual(sig_short["direction"], "SHORT")
        self.assertEqual(sig_short["target_rr"], 3.5)
        self.assertEqual(sig_short["tp1_rr"], 1.5)
        self.assertEqual(sig_short["entry_price"], 98.0)
        
        risk_dist_s = sig_short["risk_distance"]
        expected_sl_s = format_price_precision(98.0 + risk_dist_s)
        expected_tp1_s = format_price_precision(98.0 - 1.5 * risk_dist_s)
        expected_tp_s = format_price_precision(98.0 - 3.5 * risk_dist_s)
        self.assertEqual(sig_short["sl_price"], expected_sl_s)
        self.assertEqual(sig_short["tp1_price"], expected_tp1_s)
        self.assertEqual(sig_short["tp_price"], expected_tp_s)
        self.assertGreater(sig_short["sl_price"], sig_short["entry_price"])
        self.assertLess(sig_short["tp1_price"], sig_short["entry_price"])
        self.assertLess(sig_short["tp_price"], sig_short["tp1_price"])

    def test_trend_pullback_and_sweep_signals(self):
        """Verify TrendPullbackConfluence and LiquiditySweepReversal generate 1:3.50 RR signals with tp1_price and rejection filters."""
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")

        # 1. TrendPullbackConfluence LONG
        df_pb_long = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [95.0] * 59 + [97.0],
            "high": [98.0] * 59 + [100.0],
            "low": [94.0] * 59 + [97.5],  # Touches EMA20 (98.0)
            "close": [96.0] * 59 + [99.0], # Closes above Open and >= EMA20
            "volume": np.full(60, 1000.0),
            "ema20": [98.0] * 60,
            "ema50": [95.0] * 60,
            "ema200": [90.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [48.0] * 60,
            "rvol": [1.4] * 60,
            "buyer_ratio": [54.0] * 60,
            "adx14": [26.0] * 60,
            "hurst": [0.55] * 60,
            "swing_low_5": [94.0] * 60
        })
        sig_pb_long = signal_with_history(TrendPullbackConfluence, df_pb_long, 59, timeframe="15m")
        self.assertIsNotNone(sig_pb_long)
        self.assertEqual(sig_pb_long["direction"], "LONG")
        self.assertEqual(sig_pb_long["target_rr"], 3.5)
        self.assertEqual(sig_pb_long["tp1_rr"], 1.5)
        r_dist = sig_pb_long["risk_distance"]
        self.assertEqual(sig_pb_long["tp1_price"], format_price_precision(99.0 + 1.5 * r_dist))
        self.assertEqual(sig_pb_long["tp_price"], format_price_precision(99.0 + 3.5 * r_dist))

        # Rejection when rvol < 1.25
        df_pb_low_rvol = df_pb_long.copy()
        df_pb_low_rvol.loc[59, "rvol"] = 1.10
        self.assertIsNone(signal_with_history(TrendPullbackConfluence, df_pb_low_rvol, 59, timeframe="15m"))

        # Rejection when buyer_ratio < 50.0 for Long
        df_pb_low_buyer = df_pb_long.copy()
        df_pb_low_buyer.loc[59, "buyer_ratio"] = 46.0
        self.assertIsNone(signal_with_history(TrendPullbackConfluence, df_pb_low_buyer, 59, timeframe="15m"))

        # 2. TrendPullbackConfluence SHORT
        df_pb_short = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [105.0] * 59 + [103.0],
            "high": [106.0] * 59 + [102.5], # Touches EMA20 (102.0)
            "low": [103.0] * 59 + [100.0],
            "close": [104.0] * 59 + [101.0], # Closes below Open and <= EMA20
            "volume": np.full(60, 1000.0),
            "ema20": [102.0] * 60,
            "ema50": [105.0] * 60,
            "ema200": [110.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [52.0] * 60,
            "rvol": [1.35] * 60,
            "buyer_ratio": [44.0] * 60,
            "adx14": [25.0] * 60,
            "hurst": [0.54] * 60,
            "swing_high_5": [106.0] * 60
        })
        sig_pb_short = signal_with_history(TrendPullbackConfluence, df_pb_short, 59, timeframe="15m")
        self.assertIsNotNone(sig_pb_short)
        self.assertEqual(sig_pb_short["direction"], "SHORT")
        self.assertEqual(sig_pb_short["target_rr"], 3.5)
        self.assertEqual(sig_pb_short["tp1_rr"], 1.5)
        r_dist_s = sig_pb_short["risk_distance"]
        self.assertEqual(sig_pb_short["tp1_price"], format_price_precision(101.0 - 1.5 * r_dist_s))
        self.assertEqual(sig_pb_short["tp_price"], format_price_precision(101.0 - 3.5 * r_dist_s))

        # 3. LiquiditySweepReversal LONG
        # Candle sweeps below 20-bar swing low (98.0) down to 96.0, rejects up to close at 99.0 (open 98.5, high 99.5)
        # lower_wick = 98.5 - 96.0 = 2.5, total_range = 99.5 - 96.0 = 3.5 -> ratio = 2.5 / 3.5 = 0.714 >= 0.50
        df_sw_long = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [100.0] * 59 + [98.5],
            "high": [102.0] * 59 + [99.5],
            "low": [98.0] * 59 + [96.0],
            "close": [101.0] * 59 + [99.0],
            "volume": np.full(60, 1000.0),
            "swing_high_20": [105.0] * 60,
            "swing_low_20": [98.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [45.0] * 60,
            "rvol": [1.30] * 60
        })
        sig_sw_long = signal_with_history(LiquiditySweepReversal, df_sw_long, 59, timeframe="15m")
        self.assertIsNotNone(sig_sw_long)
        self.assertEqual(sig_sw_long["strategy"], "Liquidity_Sweep_Reversal")
        self.assertEqual(sig_sw_long["direction"], "LONG")
        self.assertEqual(sig_sw_long["target_rr"], 3.5)
        self.assertEqual(sig_sw_long["tp1_rr"], 1.5)
        r_dist_sw = sig_sw_long["risk_distance"]
        self.assertEqual(sig_sw_long["tp1_price"], format_price_precision(99.0 + 1.5 * r_dist_sw))
        self.assertEqual(sig_sw_long["tp_price"], format_price_precision(99.0 + 3.5 * r_dist_sw))

        # Rejection when lower wick ratio < 0.50
        df_sw_bad_wick = df_sw_long.copy()
        df_sw_bad_wick.loc[59, "low"] = 97.8 # lower wick = 98.5 - 97.8 = 0.7 / 1.7 = 0.41 (< 0.50)
        self.assertIsNone(signal_with_history(LiquiditySweepReversal, df_sw_bad_wick, 59, timeframe="15m"))

        # Rejection when rvol < 1.20
        df_sw_low_rvol = df_sw_long.copy()
        df_sw_low_rvol.loc[59, "rvol"] = 1.05
        self.assertIsNone(signal_with_history(LiquiditySweepReversal, df_sw_low_rvol, 59, timeframe="15m"))

        # 4. LiquiditySweepReversal SHORT
        # Candle sweeps above 20-bar swing high (102.0) up to 104.0, rejects down to close at 101.0 (open 101.5, low 100.5)
        # upper_wick = 104.0 - 101.5 = 2.5, total_range = 104.0 - 100.5 = 3.5 -> ratio = 2.5 / 3.5 = 0.714 >= 0.50
        df_sw_short = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [100.0] * 59 + [101.5],
            "high": [102.0] * 59 + [104.0],
            "low": [98.0] * 59 + [100.5],
            "close": [101.0] * 59 + [101.0],
            "volume": np.full(60, 1000.0),
            "swing_high_20": [102.0] * 60,
            "swing_low_20": [95.0] * 60,
            "atr14": [2.0] * 60,
            "rsi14": [55.0] * 60,
            "rvol": [1.35] * 60
        })
        sig_sw_short = signal_with_history(LiquiditySweepReversal, df_sw_short, 59, timeframe="15m")
        self.assertIsNotNone(sig_sw_short)
        self.assertEqual(sig_sw_short["strategy"], "Liquidity_Sweep_Reversal")
        self.assertEqual(sig_sw_short["direction"], "SHORT")
        self.assertEqual(sig_sw_short["target_rr"], 3.5)
        self.assertEqual(sig_sw_short["tp1_rr"], 1.5)
        r_dist_sws = sig_sw_short["risk_distance"]
        self.assertEqual(sig_sw_short["tp1_price"], format_price_precision(101.0 - 1.5 * r_dist_sws))
        self.assertEqual(sig_sw_short["tp_price"], format_price_precision(101.0 - 3.5 * r_dist_sws))

    def _simulate_path(self, path, direction="LONG", target_rr=3.5, **options):
        class OneSignal(StrategyBase):
            name = "DeterministicExecutionFixture"

            @staticmethod
            def generate_signal(df, idx, target_rr=3.5, **kwargs):
                if idx != 199:
                    return None
                return {"direction": direction, "risk_distance": 2.0,
                        "target_rr": target_rr, "pre_trade_context": {"fixture": True}}

        frame, anchors = simulation_fixture(path)
        settings = {"fee_pct": 0.0, "slippage_pct": 0.0, **options}
        result = simulate_strategy_on_dataframe(frame, OneSignal, target_rr=target_rr,
                    timeframe="15m", htf_data=anchors, **settings)
        self.assertEqual(result["total_trades"], 1)
        trade = result["trades"][0]
        self.assertEqual(trade["entry_time"], int(frame.iloc[200]["time"]))
        self.assertEqual(trade["original_risk_distance"], 2.0)
        return trade

    def test_sim_engine_correctly_calculates_trailing_and_breakeven_pnl(self):
        """Causal fills retain their actual protected, loss, and timeout PnL."""
        trail_path = [(100, 105, 100, 104), (104, 104.5, 102, 102.5)]
        trail = self._simulate_path(trail_path)
        self.assertEqual(trail["exit_reason"], "PROTECTED_STOP")
        self.assertEqual(trail["exit_price"], 103.0)
        self.assertTrue(trail["tp1_hit"])
        self.assertAlmostEqual(trail["raw_r"], 1.5)

        protected = self._simulate_path([(100, 102.2, 99.5, 101.8),
                                         (101.8, 102, 100.1, 100.2)])
        self.assertFalse(protected["tp1_hit"])
        self.assertEqual(protected["exit_reason"], "PROTECTED_STOP")
        self.assertAlmostEqual(protected["raw_r"], .15)

        loss = self._simulate_path([(100, 100.5, 97, 97.5)])
        self.assertFalse(loss["tp1_hit"])
        self.assertEqual(loss["exit_reason"], "STOP_LOSS")
        self.assertAlmostEqual(loss["raw_r"], -1.0)
        self.assertEqual(loss["outcome"], "LOSS")

        timeout = self._simulate_path([(100, 100.8, 99.2, 100.4)] * 5,
                                       max_holding_bars=5, stagnation_bars=20)
        self.assertEqual(timeout["exit_reason"], "MAX_HOLD")
        self.assertAlmostEqual(timeout["raw_r"], .2)
        self.assertEqual(timeout["outcome"], "WIN")

        costed = self._simulate_path(trail_path, fee_pct=.05, slippage_pct=.02)
        actual_gross = sum((fill["price"] - costed["entry_price"]) * fill["quantity"]
                           for fill in costed["fills"] if fill["kind"] != "ENTRY")
        actual_fees = sum(fill["notional_usd"] * .0005 for fill in costed["fills"])
        self.assertAlmostEqual(costed["gross_pnl_usd"], actual_gross)
        self.assertAlmostEqual(costed["pnl_usd"], actual_gross - actual_fees)
        self.assertLess(costed["net_r"], costed["raw_r"])
        self.assertAlmostEqual(sum(fill["cash_delta_usd"] for fill in costed["fills"]), costed["pnl_usd"])

    def test_sim_engine_dual_stage_scale_out(self):
        """Partial and final fills use preserved quantity and the live +0.5R lock."""
        for direction, path, expected_tp1, expected_exit in (
            ("LONG", [(100, 103.2, 99.5, 102.5), (102.5, 102.6, 100.1, 100.2)], 103, 101),
            ("SHORT", [(100, 100.5, 96.8, 97.5), (97.5, 99.9, 97, 99.8)], 97, 99),
        ):
            with self.subTest(direction=direction):
                trade = self._simulate_path(path, direction=direction)
                self.assertTrue(trade["tp1_hit"])
                self.assertEqual(trade["tp1_price"], expected_tp1)
                self.assertEqual(trade["exit_price"], expected_exit)
                self.assertAlmostEqual(trade["raw_r"], 1.0)  # .5*1.5R + .5*.5R
                exits = [fill for fill in trade["fills"] if fill["kind"] != "ENTRY"]
                self.assertEqual([fill["quantity"] for fill in exits], [.25, .25])
                self.assertEqual(trade["position_qty"], 0)
                self.assertEqual(trade["diagnostic"]["catalyst_type"], "PROTECTED_STOP")

        target = self._simulate_path([(100, 103.2, 99.5, 103),
                                      (103, 106.5, 102.5, 106)], target_rr=3.0)
        self.assertEqual(target["exit_reason"], "TAKE_PROFIT")
        self.assertEqual(target["exit_price"], 106)
        self.assertAlmostEqual(target["raw_r"], 2.25)

        # A 5R target is still standing when 3.5R starts the runner. A 3.5R
        # target would already have filled and cannot be retroactively canceled.
        runner = self._simulate_path([(100, 108, 99.5, 107),
                                      (107, 107.2, 104, 104.5)], target_rr=5.0)
        self.assertTrue(runner["is_unlimited_runner"])
        self.assertEqual(runner["exit_reason"], "PROTECTED_STOP")
        self.assertAlmostEqual(runner["exit_price"], 106.2)
        self.assertAlmostEqual(runner["raw_r"], 2.3)

    def test_live_bot_partial_take_profit_and_breakeven(self):
        """Verify LiveCryptoBot dual-stage position management: +1.0R BE defense (+0.15R fee shield), +1.50R TP1 harvest (+0.75R banked, position halved, SL @ +0.50R), and dual-stage close accounting."""
        import tempfile
        import shutil
        import asyncio
        from live_bot import LiveCryptoBot

        tmpdir = tempfile.mkdtemp()
        try:
            bot = LiveCryptoBot(initial_capital=100.0, fixed_risk_usd=1.0, data_dir=tmpdir)
            bot.open_positions = {}
            bot.closed_trades = []
            bot.current_balance = 100.0

            # 1. Open mock LONG position with tp1_price and default fields
            entry_p = 100.0
            risk_d = 10.0
            bot.open_positions["BTCUSDT"] = {
                "trade_id": 1,
                "symbol": "BTCUSDT",
                "strategy": "Trend_Pullback_Confluence",
                "direction": "LONG",
                "entry_time": 1700000000,
                "entry_time_str": "2026-08-20 12:00:00",
                "entry_price": entry_p,
                "current_price": entry_p,
                "sl_price": entry_p - risk_d,        # 90.0
                "tp_price": entry_p + (3.5 * risk_d), # 135.0
                "tp1_price": entry_p + (1.5 * risk_d),# 115.0
                "risk_distance": risk_d,
                "risk_amount_usd": 1.0,
                "position_qty": 0.10,
                "initial_qty": 0.10,
                "position_value_usd": 10.0,
                "target_rr": 3.5,
                "tp1_hit": False,
                "realized_partial_r": 0.0,
                "is_breakeven_protected": False,
                "is_profit_locked": False,
                "is_unlimited_runner": False,
                "bars_held": 0,
                "pre_trade_context": {"reason": "Test setup"}
            }

            # Step A: High = 111.0 (+1.10R MFE >= 1.0R) -> Stage 1 Breakeven Defense (+0.15R)
            df_step1 = pd.DataFrame([{
                'time': 1700000900,
                'close': 110.5,
                'high': 111.0,
                'low': 100.0,
                'volume': 1000,
                'atr14': 6.0,
                'momentum': 4.0,
                'rsi14': 58.0
            }])
            asyncio.run(bot._update_open_positions({"BTCUSDT": df_step1}))
            pos = bot.open_positions.get("BTCUSDT")
            self.assertIsNotNone(pos)
            self.assertTrue(pos['is_breakeven_protected'])
            self.assertTrue(pos['is_breakeven'])
            self.assertEqual(float(pos['sl_price']), 101.5)  # 100 + 0.15 * 10
            self.assertEqual(pos['exit_status'], "Breakeven Protected 🛡️ (+0.15R fee shield)")

            # Step B: High = 116.0 (+1.60R MFE >= 1.50R) -> Stage 2 Partial Profit Harvest (+0.75R Banked, SL @ +0.50R)
            df_step2 = pd.DataFrame([{
                'time': 1700001800,
                'close': 115.5,
                'high': 116.0,
                'low': 105.0,
                'volume': 1200,
                'atr14': 6.0,
                'momentum': 6.0,
                'rsi14': 64.0
            }])
            asyncio.run(bot._update_open_positions({"BTCUSDT": df_step2}))
            pos = bot.open_positions.get("BTCUSDT")
            self.assertIsNotNone(pos)
            self.assertTrue(pos['tp1_hit'])
            self.assertTrue(pos['is_profit_locked'])
            self.assertEqual(pos['realized_partial_r'], 0.75)
            self.assertEqual(pos['position_qty'], 0.05)  # Halved position size
            self.assertEqual(float(pos['sl_price']), 105.0)  # 100 + 0.50 * 10
            self.assertEqual(pos['exit_status'], "TP1 Booked 🎯 (+0.75R Banked, SL @ +0.50R)")
            self.assertEqual(bot.current_balance, 100.75)

            # Step C: Reversal stopping out at +0.50R SL (Low = 104.5 <= 105.0)
            df_step3 = pd.DataFrame([{
                'time': 1700002700,
                'close': 104.8,
                'high': 112.0,
                'low': 104.5,
                'volume': 800,
                'atr14': 6.0,
                'momentum': -2.0,
                'rsi14': 45.0
            }])
            asyncio.run(bot._update_open_positions({"BTCUSDT": df_step3}))
            self.assertNotIn("BTCUSDT", bot.open_positions)
            self.assertEqual(len(bot.closed_trades), 1)
            t = bot.closed_trades[-1]
            self.assertTrue(t['tp1_hit'])
            self.assertEqual(t['outcome'], "WIN")
            # runner_raw_r = (105.0 - 100.0) / 10.0 = 0.50
            # total_net_r = round(0.75 + (0.5 * (0.50 - 0.08)), 2) = round(0.75 + 0.21, 2) = 0.96
            self.assertEqual(t['net_r'], 0.96)
            self.assertEqual(t['pnl_usd'], 0.96)
            self.assertEqual(bot.current_balance, 100.96)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_live_bot_partial_take_profit_and_breakeven_target_rr_2(self):
        """Verify LiveCryptoBot dual-stage position management under strict 1:2.0 RR: +0.80R BE defense, +1.00R TP1 harvest (+0.50R banked, SL @ +0.50R), and mathematical balance parity."""
        import tempfile
        import shutil
        import asyncio
        from live_bot import LiveCryptoBot

        tmpdir = tempfile.mkdtemp()
        try:
            bot = LiveCryptoBot(initial_capital=100.0, fixed_risk_usd=1.0, target_rr=2.0, data_dir=tmpdir)
            bot.open_positions = {}
            bot.closed_trades = []
            bot.current_balance = 100.0

            # 1. Open mock LONG position with target_rr=2.0, tp1_price=110.0 (+1.0R), tp_price=120.0 (+2.0R)
            entry_p = 100.0
            risk_d = 10.0
            bot.open_positions["BTCUSDT"] = {
                "trade_id": 1,
                "symbol": "BTCUSDT",
                "strategy": "Trend_Pullback_Confluence",
                "direction": "LONG",
                "entry_time": 1700000000,
                "entry_time_str": "2026-08-20 12:00:00",
                "entry_price": entry_p,
                "current_price": entry_p,
                "sl_price": entry_p - risk_d,        # 90.0
                "tp_price": entry_p + (2.0 * risk_d), # 120.0
                "tp1_price": entry_p + (1.0 * risk_d),# 110.0
                "risk_distance": risk_d,
                "risk_amount_usd": 1.0,
                "position_qty": 0.10,
                "initial_qty": 0.10,
                "position_value_usd": 10.0,
                "target_rr": 2.0,
                "tp1_hit": False,
                "realized_partial_r": 0.0,
                "is_breakeven_protected": False,
                "is_profit_locked": False,
                "is_unlimited_runner": False,
                "bars_held": 0,
                "pre_trade_context": {"reason": "1:2.0 RR test setup"}
            }

            # Step A: High = 108.5 (+0.85R MFE >= 0.80R) -> Stage 1 Breakeven Defense (+0.15R)
            df_step1 = pd.DataFrame([{
                'time': 1700000900,
                'close': 108.0,
                'high': 108.5,
                'low': 100.0,
                'volume': 1000,
                'atr14': 6.0,
                'momentum': 4.0,
                'rsi14': 58.0
            }])
            asyncio.run(bot._update_open_positions({"BTCUSDT": df_step1}))
            pos = bot.open_positions.get("BTCUSDT")
            self.assertIsNotNone(pos)
            self.assertTrue(pos['is_breakeven_protected'])
            self.assertTrue(pos['is_breakeven'])
            self.assertEqual(float(pos['sl_price']), 101.5)  # 100 + 0.15 * 10
            self.assertEqual(pos['exit_status'], "Breakeven Protected 🛡️ (+0.15R fee shield)")

            # Step B: High = 110.5 (+1.05R MFE >= 1.00R) -> Stage 2 Partial Profit Harvest (+0.50R Banked, SL @ +0.50R)
            df_step2 = pd.DataFrame([{
                'time': 1700001800,
                'close': 110.2,
                'high': 110.5,
                'low': 105.0,
                'volume': 1200,
                'atr14': 6.0,
                'momentum': 6.0,
                'rsi14': 64.0
            }])
            asyncio.run(bot._update_open_positions({"BTCUSDT": df_step2}))
            pos = bot.open_positions.get("BTCUSDT")
            self.assertIsNotNone(pos)
            self.assertTrue(pos['tp1_hit'])
            self.assertTrue(pos['is_profit_locked'])
            self.assertEqual(pos['realized_partial_r'], 0.50)
            self.assertEqual(pos['position_qty'], 0.05)  # Halved position size
            self.assertEqual(float(pos['sl_price']), 105.0)  # 100 + 0.50 * 10
            self.assertEqual(pos['exit_status'], "TP1 Booked 🎯 (+0.50R Banked, SL @ +0.50R)")
            self.assertEqual(bot.current_balance, 100.50)

            # Step C: Reversal stopping out at +0.50R SL (Low = 104.5 <= 105.0)
            df_step3 = pd.DataFrame([{
                'time': 1700002700,
                'close': 104.8,
                'high': 109.0,
                'low': 104.5,
                'volume': 800,
                'atr14': 6.0,
                'momentum': -2.0,
                'rsi14': 45.0
            }])
            asyncio.run(bot._update_open_positions({"BTCUSDT": df_step3}))
            self.assertNotIn("BTCUSDT", bot.open_positions)
            self.assertEqual(len(bot.closed_trades), 1)
            t = bot.closed_trades[-1]
            self.assertTrue(t['tp1_hit'])
            self.assertEqual(t['outcome'], "WIN")
            # runner_raw_r = (105.0 - 100.0) / 10.0 = 0.50
            # total_net_r = round(0.50 + (0.5 * (0.50 - 0.08)), 2) = round(0.50 + 0.21, 2) = 0.71
            self.assertEqual(t['raw_r'], 0.75)
            self.assertEqual(t['net_r'], 0.71)
            self.assertEqual(t['pnl_usd'], 0.71)
            self.assertEqual(bot.current_balance, 100.71)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_live_bot_smart_stagnation_exit(self):
        """Verify LiveCryptoBot Smart Stagnation Exit requires bars >= stagnation_bars, |unrealized| < 0.25R, and momentum flipped against trade direction."""
        import tempfile
        import shutil
        import asyncio
        from live_bot import LiveCryptoBot

        tmpdir = tempfile.mkdtemp()
        try:
            bot = LiveCryptoBot(initial_capital=100.0, timeframe="15m", data_dir=tmpdir)
            bot.open_positions = {}
            bot.closed_trades = []

            # 1. Long position held for 16 bars (stagnation threshold for 15m), but momentum is positive (+0.5 > 0)
            bot.open_positions["STAG_LONG"] = {
                "trade_id": 10,
                "symbol": "STAG_LONG",
                "timeframe": "15m",
                "direction": "LONG",
                "entry_price": 100.0,
                "sl_price": 90.0,
                "tp_price": 135.0,
                "risk_distance": 10.0,
                "bars_held": 16,
                "entry_candle_time": 1000
            }
            df_positive_mom = pd.DataFrame([{
                'time': 2000,
                'close': 100.5,
                'high': 101.0,  # MFE = 0.10R (< 0.8R), unrealized = 0.05R (< 0.25R)
                'low': 99.5,
                'volume': 500,
                'atr14': 2.0,
                'momentum': 0.5,  # Momentum positive -> NOT flipped against LONG
                'rsi14': 50.0
            }])
            asyncio.run(bot._update_open_positions({"STAG_LONG": df_positive_mom}))
            # Should REMAIN OPEN because momentum did not flip
            self.assertIn("STAG_LONG", bot.open_positions)

            # 2. Same position with momentum flipped negative (-0.5 < 0) -> Exits on TIME_EXIT
            df_neg_mom = pd.DataFrame([{
                'time': 2000,
                'close': 100.5,
                'high': 101.0,
                'low': 99.5,
                'volume': 500,
                'atr14': 2.0,
                'momentum': -0.5,  # Momentum flipped against LONG
                'rsi14': 50.0
            }])
            asyncio.run(bot._update_open_positions({"STAG_LONG": df_neg_mom}))
            self.assertNotIn("STAG_LONG", bot.open_positions)
            self.assertEqual(bot.closed_trades[-1]['outcome'], "TIME_EXIT")

            # 3. SHORT position on 5m (stagnation_bars = 18)
            bot.open_positions["STAG_SHORT"] = {
                "trade_id": 11,
                "symbol": "STAG_SHORT",
                "timeframe": "5m",
                "direction": "SHORT",
                "entry_price": 100.0,
                "sl_price": 110.0,
                "tp_price": 65.0,
                "risk_distance": 10.0,
                "bars_held": 18,
                "entry_candle_time": 1000
            }
            # Negative momentum is favorable for short -> should NOT exit
            df_short_favorable = pd.DataFrame([{
                'time': 3000,
                'close': 99.5,
                'high': 100.5,
                'low': 99.0,
                'volume': 500,
                'atr14': 2.0,
                'momentum': -0.5,  # Favorable for SHORT
                'rsi14': 50.0
            }])
            asyncio.run(bot._update_open_positions({"STAG_SHORT": df_short_favorable}))
            self.assertIn("STAG_SHORT", bot.open_positions)

            # Positive momentum is against short -> should EXIT on TIME_EXIT
            df_short_flipped = pd.DataFrame([{
                'time': 3000,
                'close': 99.5,
                'high': 100.5,
                'low': 99.0,
                'volume': 500,
                'atr14': 2.0,
                'momentum': 0.5,  # Flipped against SHORT
                'rsi14': 50.0
            }])
            asyncio.run(bot._update_open_positions({"STAG_SHORT": df_short_flipped}))
            self.assertNotIn("STAG_SHORT", bot.open_positions)
            self.assertEqual(bot.closed_trades[-1]['outcome'], "TIME_EXIT")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_trade_journal_dual_stage_scale_out_breakdown(self):
        """Verify create_trade_journal_md outputs TP1 status, +0.75R banked profit, Net R breakdown, and diagnostic factors."""
        from trade_journal import create_trade_journal_md, format_trade_markdown

        trade_win_scale_out = {
            "trade_id": 101,
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "strategy": "Trend_Pullback_Confluence",
            "target_rr": 3.5,
            "entry_price": 60000.0,
            "exit_price": 63000.0,
            "sl_price": 59000.0,
            "tp1_price": 61500.0,
            "tp_price": 63500.0,
            "tp1_hit": True,
            "raw_r": 2.25,
            "net_r": 2.17,
            "mae_r": 0.2,
            "mfe_r": 3.0,
            "bars_held": 12,
            "outcome": "WIN",
            "pre_trade_context": {
                "regime": "TRENDING_EXPANSION",
                "reason": "15m Bullish Pullback with 1h HTF EMA Alignment",
                "rvol": 2.1,
                "rsi": 52.0,
                "volatility_atr": 500.0
            },
            "diagnostic": {
                "catalyst_type": "Clean Momentum Trend Continuation",
                "summary": "Dual-stage scale-out secured early target, runner captured extended trend move.",
                "key_factors": ["Strong institutional order flow"]
            }
        }

        md_output = create_trade_journal_md(trade_win_scale_out)
        self.assertIn("Dual-Stage Scale-Out Execution", md_output)
        self.assertIn("TP1 Hit @ $61500.0", md_output)
        self.assertIn("+0.75R", md_output)
        self.assertIn("Net R Breakdown", md_output)
        self.assertIn("Dual-Stage Scale-Out executed: Banked +0.75R guaranteed profit", md_output)

        # Verify format_trade_markdown is identical
        md_format = format_trade_markdown(trade_win_scale_out)
        self.assertEqual(md_output, md_format)

        # Test trade without TP1 hit
        trade_loss = {
            "trade_id": 102,
            "symbol": "ETHUSDT",
            "direction": "SHORT",
            "strategy": "Squeeze_Momentum_Breakout",
            "target_rr": 3.0,
            "entry_price": 3000.0,
            "exit_price": 3050.0,
            "sl_price": 3050.0,
            "tp1_price": 2925.0,
            "tp_price": 2850.0,
            "tp1_hit": False,
            "raw_r": -1.0,
            "net_r": -1.08,
            "mae_r": 1.0,
            "mfe_r": 0.3,
            "bars_held": 4,
            "outcome": "LOSS",
            "pre_trade_context": {"reason": "Short squeeze breakout"},
            "diagnostic": {"catalyst_type": "Immediate Liquidity Trap", "summary": "Quick stop out."}
        }
        md_loss = create_trade_journal_md(trade_loss)
        self.assertIn("TP1 Not Reached", md_loss)
        self.assertIn("-1.08R Net", md_loss)

    def test_configured_strategy_is_unvalidated_until_measured(self):
        """Synthetic execution examples cannot establish a strategy win rate."""
        import tempfile
        from live_bot import LiveCryptoBot

        with tempfile.TemporaryDirectory() as directory:
            bot = LiveCryptoBot(data_dir=directory)
            self.assertEqual(bot.active_strategy_name, "Trend_Pullback_Confluence")
            self.assertEqual(bot.target_rr, 2.0)
            self.assertEqual(bot.active_params["target_rr"], 2.0)
            self.assertGreaterEqual(bot.active_params["rvol_min"], 1.45)
            self.assertEqual(bot.champion_stats["validation_status"], "NOT_VALIDATED")
            self.assertIsNone(bot.champion_stats["win_rate"])
            self.assertIsNone(bot.champion_stats["expectancy_r"])
            self.assertIsNone(bot.champion_stats["score"])

        # Check two explicit execution paths without choosing their frequency or
        # claiming that either outcome predicts market profitability.
        take_profit = self._simulate_path([(100, 104.2, 99.5, 104)], target_rr=2.0)
        stopped = self._simulate_path([(100, 100.2, 97.5, 98)], target_rr=2.0)
        self.assertEqual(take_profit["exit_reason"], "TAKE_PROFIT")
        self.assertEqual([f["kind"] for f in take_profit["fills"]], ["ENTRY", "TP1", "EXIT"])
        self.assertAlmostEqual(take_profit["raw_r"], 1.5)  # half at 1R, half at 2R
        self.assertEqual(stopped["exit_reason"], "STOP_LOSS")
        self.assertAlmostEqual(stopped["raw_r"], -1.0)

if __name__ == "__main__":
    unittest.main()
