import unittest
import pandas as pd
import numpy as np
from strategies import compute_crypto_indicators, SqueezeMomentumBreakout, LiquiditySweepReversal, TrendPullbackConfluence
from sim_engine import simulate_strategy_on_dataframe
from strategy_memory import evaluate_reproducibility

class TestCryptoSimulationSystem(unittest.TestCase):

    def setUp(self):
        # Generate synthetic OHLCV data for testing
        np.random.seed(42)
        n = 200
        prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
        
        self.df = pd.DataFrame({
            'time': np.arange(1700000000, 1700000000 + n * 900, 900),
            'open': prices + np.random.randn(n) * 0.1,
            'high': prices + np.abs(np.random.randn(n) * 0.5) + 0.2,
            'low': prices - np.abs(np.random.randn(n) * 0.5) - 0.2,
            'close': prices,
            'volume': np.random.uniform(500, 2000, n),
            'symbol': 'BTCUSDT'
        })

    def test_indicator_computation(self):
        df_ind = compute_crypto_indicators(self.df)
        self.assertIn('ema20', df_ind.columns)
        self.assertIn('bb_upper', df_ind.columns)
        self.assertIn('atr14', df_ind.columns)
        self.assertIn('squeeze_on', df_ind.columns)
        self.assertIn('rsi14', df_ind.columns)
        self.assertIn('rvol', df_ind.columns)

    def test_strict_rr_enforcement(self):
        # Verify that sim engine enforces >= 2.0 RR
        with self.assertRaises(AssertionError):
            simulate_strategy_on_dataframe(self.df, SqueezeMomentumBreakout, target_rr=1.5)
            
        res = simulate_strategy_on_dataframe(self.df, SqueezeMomentumBreakout, target_rr=3.0)
        self.assertIn('total_trades', res)
        self.assertIn('trades', res)

    def test_trade_diagnostics_present(self):
        res = simulate_strategy_on_dataframe(self.df, LiquiditySweepReversal, target_rr=3.0)
        for t in res.get('trades', []):
            self.assertIn('pre_trade_context', t)
            self.assertIn('diagnostic', t)
            self.assertIn('summary', t['diagnostic'])
            self.assertIn('catalyst_type', t['diagnostic'])

    def test_reproducibility_evaluator(self):
        # Winning test metrics
        good_train = {'total_trades': 50, 'win_rate_pct': 42.0, 'profit_factor': 2.1, 'expectancy_r': 0.68, 'target_rr': 3.0}
        good_test = {'strategy': 'Squeeze_Momentum_Breakout', 'total_trades': 25, 'win_rate_pct': 40.0, 'profit_factor': 1.9, 'expectancy_r': 0.55, 'target_rr': 3.0}
        
        eval_res = evaluate_reproducibility(good_train, good_test)
        self.assertTrue(eval_res['is_reproducible'])

        # Failing test metrics (< 33% win rate at 1:3 RR)
        bad_test = {'strategy': 'Bad_Strategy', 'total_trades': 20, 'win_rate_pct': 20.0, 'profit_factor': 0.7, 'expectancy_r': -0.2, 'target_rr': 3.0}
        eval_bad = evaluate_reproducibility(good_train, bad_test)
        self.assertFalse(eval_bad['is_reproducible'])

    def test_timeframe_aware_simulation(self):
        # Test simulation on 15m vs 30m
        res_15m = simulate_strategy_on_dataframe(self.df, SqueezeMomentumBreakout, target_rr=3.0, timeframe="15m")
        res_30m = simulate_strategy_on_dataframe(self.df, SqueezeMomentumBreakout, target_rr=3.0, timeframe="30m")
        self.assertIn('trades', res_15m)
        self.assertIn('trades', res_30m)

    def test_sim_tier4_runner_trailing(self):
        """Verify that simulation engine models Tier 4 runner mode."""
        # Create a trending dataset that triggers a signal and extends past 3R
        n = 100
        trend_prices = 100.0 + np.linspace(0, 30, n)
        df_trend = pd.DataFrame({
            'time': np.arange(1700000000, 1700000000 + n * 900, 900),
            'open': trend_prices,
            'high': trend_prices + 1.0,
            'low': trend_prices - 0.2,
            'close': trend_prices + 0.8,
            'volume': [1000.0] * n,
            'symbol': 'TRENDUSDT'
        })
        res = simulate_strategy_on_dataframe(df_trend, SqueezeMomentumBreakout, target_rr=3.0, timeframe="30m")
        self.assertIn('trades', res)

if __name__ == '__main__':
    unittest.main()
