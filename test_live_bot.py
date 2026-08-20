import unittest
import asyncio
import os
import json
import pandas as pd
import numpy as np
from live_bot import LiveCryptoBot

class TestLiveBotEngine(unittest.TestCase):

    def setUp(self):
        self.bot = LiveCryptoBot(
            initial_capital=100.0,
            fixed_risk_usd=1.0,
            timeframe="15m", 
            max_open_positions=3, 
            target_rr=2.0, 
            scan_interval_sec=5
        )
        self.bot.open_positions = {}
        self.bot.closed_trades = []
        self.bot.current_balance = 100.0

    def test_bot_initialization(self):
        self.assertEqual(self.bot.initial_capital, 100.0)
        self.assertEqual(self.bot.current_balance, 100.0)
        self.assertEqual(self.bot.fixed_risk_usd, 1.0)
        self.assertEqual(self.bot.target_rr, 2.0)
        self.assertFalse(self.bot.is_depleted)

    def test_bot_telemetry_format(self):
        telemetry = self.bot.get_telemetry()
        self.assertIn("status", telemetry)
        self.assertIn("initial_capital", telemetry)
        self.assertIn("current_balance", telemetry)
        self.assertIn("fixed_risk_usd", telemetry)
        self.assertIn("is_depleted", telemetry)
        self.assertIn("target_rr", telemetry)
        self.assertIn("open_positions", telemetry)
        self.assertIn("win_rate_pct", telemetry)
        self.assertIn("total_net_r", telemetry)

    def test_depletion_auto_stop_and_report_generation(self):
        # Simulate balance dropping below $1.00 USD
        self.bot.current_balance = 0.50
        asyncio.run(self.bot._handle_capital_depleted())

        self.assertTrue(self.bot.is_depleted)
        self.assertFalse(self.bot.is_running)
        self.assertIsNotNone(self.bot.depletion_report_file)
        self.assertTrue(os.path.exists(self.bot.depletion_report_file))

        # Check telemetry reports DEPLETED_STOPPED
        t = self.bot.get_telemetry()
        self.assertEqual(t['status'], 'DEPLETED_STOPPED')

    def test_account_reset(self):
        self.bot.current_balance = 0.0
        self.bot.is_depleted = True
        self.bot.reset_account(100.0)

        self.assertEqual(self.bot.current_balance, 100.0)
        self.assertFalse(self.bot.is_depleted)
        self.assertIsNone(self.bot.depletion_report_file)

    def test_dynamic_exit_breakeven_and_trailing(self):
        # Open a mock LONG position
        self.bot.open_positions["BTCUSDT"] = {
            "trade_id": 1,
            "symbol": "BTCUSDT",
            "strategy": "Squeeze_Momentum_Breakout",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 100.0,
            "current_price": 100.0,
            "sl_price": 90.0,
            "tp_price": 120.0,
            "risk_distance": 10.0,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0,
            "pre_trade_context": {"reason": "Test setup"}
        }

        # Mock candle advancing to +1.1R (High = 111.0, Close = 110.5, Low = 105.0)
        df_step1 = pd.DataFrame([{
            'time': 1700000900,
            'close': 110.5,
            'high': 111.0,
            'low': 105.0,
            'volume': 1000,
            'atr14': 7.0,
            'momentum': 5.0,
            'rsi14': 60.0
        }])

        asyncio.run(self.bot._update_open_positions({"BTCUSDT": df_step1}))
        pos = self.bot.open_positions.get("BTCUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_breakeven'))
        self.assertGreater(pos['sl_price'], 100.0)  # SL raised to entry + fees

        # Mock candle advancing to +1.6R (High = 116.5, Close = 116.0, Low = 114.0)
        df_step2 = pd.DataFrame([{
            'time': 1700001800,
            'close': 116.0,
            'high': 116.5,
            'low': 114.0,
            'volume': 1200,
            'atr14': 7.0,
            'momentum': 8.0,
            'rsi14': 65.0
        }])

        asyncio.run(self.bot._update_open_positions({"BTCUSDT": df_step2}))
        pos = self.bot.open_positions.get("BTCUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_trailing'))
        self.assertEqual(pos.get('exit_status'), "Trailing Active ⚡")
        self.assertEqual(pos['sl_price'], 109.5)  # 116.5 - 7.0 ATR

        # Mock candle triggering trailing stop (Low = 108.0 <= 109.5 SL)
        df_step3 = pd.DataFrame([{
            'time': 1700002700,
            'close': 108.5,
            'high': 112.0,
            'low': 108.0,
            'volume': 800,
            'atr14': 7.0,
            'momentum': -1.0,
            'rsi14': 50.0
        }])

        asyncio.run(self.bot._update_open_positions({"BTCUSDT": df_step3}))
        self.assertNotIn("BTCUSDT", self.bot.open_positions)
        self.assertEqual(len(self.bot.closed_trades), 1)
        last_trade = self.bot.closed_trades[-1]
        self.assertEqual(last_trade['outcome'], "TRAILING_STOP_WIN")
        self.assertGreater(last_trade['net_r'], 0.0)

    def test_btc_macro_gatekeeper_blocks_counter_trend_alts(self):
        # Set BTC Macro state to Flash Dump / Bearish
        self.bot.btc_macro_status = {
            "regime": "FLASH_DUMP",
            "gate_status": "BLOCK_LONGS"
        }

        # Mock synthetic breakout candle for an Altcoin (SOLUSDT)
        dates = pd.date_range(start='2026-08-01', periods=60, freq='15min')
        mock_df = pd.DataFrame({
            'time': [int(d.timestamp()) for d in dates],
            'open': np.linspace(100, 150, 60),
            'high': np.linspace(101, 152, 60),
            'low': np.linspace(99, 149, 60),
            'close': np.linspace(100, 151, 60),
            'volume': [1000] * 59 + [5000],
            'squeeze_on': [True] * 58 + [False, False],
            'bb_upper': [140] * 60,
            'bb_lower': [100] * 60,
            'ema50': [120] * 60,
            'atr14': [5.0] * 60,
            'rsi14': [65.0] * 60,
            'momentum': [2.0] * 60,
            'rvol': [2.5] * 60
        })

        asyncio.run(self.bot._scan_new_entries({"SOLUSDT": mock_df}))
        # SOLUSDT Long must be BLOCKED by BTC Macro Gatekeeper
        self.assertNotIn("SOLUSDT", self.bot.open_positions)

        # But BTCUSDT itself should bypass gatekeeper
        asyncio.run(self.bot._scan_new_entries({"BTCUSDT": mock_df}))
        self.assertIn("BTCUSDT", self.bot.open_positions)

    def test_sector_correlation_cap_blocks_second_meme(self):
        self.bot.btc_macro_status = {
            "regime": "BULLISH",
            "gate_status": "ALLOW_ALL"
        }

        # Open 2 active Meme positions (DOGEUSDT, SHIBUSDT) to hit sector cap of 2
        self.bot.open_positions["DOGEUSDT"] = {
            "trade_id": 1,
            "symbol": "DOGEUSDT",
            "sector": "MEMES",
            "direction": "LONG",
            "entry_price": 0.10,
            "current_price": 0.10,
            "sl_price": 0.09,
            "tp_price": 0.12,
            "risk_distance": 0.01,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0
        }
        self.bot.open_positions["SHIBUSDT"] = {
            "trade_id": 2,
            "symbol": "SHIBUSDT",
            "sector": "MEMES",
            "direction": "LONG",
            "entry_price": 0.00002,
            "current_price": 0.00002,
            "sl_price": 0.000018,
            "tp_price": 0.000024,
            "risk_distance": 0.000002,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0
        }

        dates = pd.date_range(start='2026-08-01', periods=60, freq='15min')
        mock_df = pd.DataFrame({
            'time': [int(d.timestamp()) for d in dates],
            'open': np.linspace(10, 15, 60),
            'high': np.linspace(10.1, 15.2, 60),
            'low': np.linspace(9.9, 14.9, 60),
            'close': np.linspace(10, 15.1, 60),
            'volume': [1000] * 59 + [5000],
            'squeeze_on': [True] * 58 + [False, False],
            'bb_upper': [14] * 60,
            'bb_lower': [10] * 60,
            'ema50': [12] * 60,
            'atr14': [0.5] * 60,
            'rsi14': [65.0] * 60,
            'momentum': [2.0] * 60,
            'rvol': [2.5] * 60
        })

        # Try to open PEPEUSDT (3rd MEMES sector trade)
        asyncio.run(self.bot._scan_new_entries({"PEPEUSDT": mock_df}))
        # PEPEUSDT must be BLOCKED by Sector Correlation Limit
        self.assertNotIn("PEPEUSDT", self.bot.open_positions)

        # But FETUSDT (AI_COMPUTE sector) should be ALLOWED
        asyncio.run(self.bot._scan_new_entries({"FETUSDT": mock_df}))
        self.assertIn("FETUSDT", self.bot.open_positions)
        self.assertEqual(self.bot.open_positions["FETUSDT"]["sector"], "AI_COMPUTE")

    def test_archive_entry_and_persistence(self):
        """Verify that trade and optimization data are permanently archived in JSON format."""
        mock_trade = {
            "trade_id": 999,
            "symbol": "BTCUSDT",
            "direction": "LONG",
            "entry_price": 60000.0,
            "exit_price": 62000.0,
            "net_r": 2.0,
            "pnl_usd": 2.0,
            "outcome": "WIN"
        }
        self.bot._archive_entry("trades", mock_trade)
        
        archive_path = os.path.join("reports", "historical_archive.json")
        self.assertTrue(os.path.exists(archive_path))
        with open(archive_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.assertIn("trades", data)
            self.assertTrue(any(t.get("trade_id") == 999 for t in data["trades"]))

    def test_unlimited_profit_runner_expands_beyond_2r(self):
        """Verify that positions reaching >= +2.0R with strong momentum engage Unlimited Runner mode."""
        self.bot.open_positions["SOLUSDT"] = {
            "trade_id": 101,
            "symbol": "SOLUSDT",
            "sector": "LAYER_1",
            "strategy": "Squeeze_Momentum_Breakout",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_price": 100.0,
            "current_price": 100.0,
            "sl_price": 99.0,
            "tp_price": 102.0,
            "risk_distance": 1.0,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0,
            "unrealized_r": 0.0,
            "mfe_r": 0.0,
            "mae_r": 0.0,
            "bars_held": 2
        }

        # Simulate breakout surging to 103.5 (+3.5R) with continuing momentum and higher low
        mock_df = pd.DataFrame([{
            'time': 1700000300,
            'open': 102.8,
            'high': 103.5,
            'low': 102.9,
            'close': 103.2,
            'volume': 5000,
            'atr14': 0.8,
            'rsi14': 64.0,
            'momentum': 1.5,
            'rvol': 2.2,
            'squeeze_on': False
        }])

        asyncio.run(self.bot._update_open_positions({"SOLUSDT": mock_df}))

        # Position should still be OPEN in Unlimited Runner Mode
        self.assertIn("SOLUSDT", self.bot.open_positions)
        pos = self.bot.open_positions["SOLUSDT"]
        self.assertTrue(pos.get("is_unlimited_runner"))
        self.assertGreater(pos["sl_price"], 100.0)  # SL raised well above entry to lock in runner profit

    def test_daily_snapshot_generation(self):
        """Verify that Daily Strategy Snapshot generates markdown report and JSON archive."""
        res = asyncio.run(self.bot.run_daily_strategy_snapshot())
        self.assertIn("date", res)
        self.assertTrue(os.path.exists(res["report_file"]))
        self.assertIsNotNone(self.bot.last_daily_snapshot_time)

    def test_monthly_tournament_and_champions_gauntlet(self):
        """Verify that Monthly Strategy Tournament crowns champion and updates Hall of Fame."""
        res = asyncio.run(self.bot.run_monthly_strategy_tournament())
        self.assertIn("strategy_name", res)
        self.assertIn("win_rate_pct", res)
        self.assertIsNotNone(self.bot.all_time_grand_champion)

        hof_path = os.path.join("reports", "monthly_champions_hall_of_fame.json")
        self.assertTrue(os.path.exists(hof_path))

    def test_server_restart_persistence_and_state_recovery(self):
        """Verify that open positions, trade journal, and balance survive a server restart."""
        # 1. Populate bot state
        self.bot.current_balance = 105.42
        self.bot.open_positions["BTCUSDT"] = {
            "trade_id": 50,
            "symbol": "BTCUSDT",
            "sector": "LAYER_1",
            "strategy": "Squeeze_Momentum_Breakout",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_price": 60000.0,
            "current_price": 60500.0,
            "sl_price": 59000.0,
            "tp_price": 62000.0,
            "risk_distance": 1000.0,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0
        }
        self.bot.closed_trades = [{
            "trade_id": 49,
            "symbol": "ETHUSDT",
            "direction": "LONG",
            "outcome": "WIN",
            "net_r": 1.92,
            "pnl_usd": 1.92
        }]
        self.bot.save_state()

        # 2. Simulate server restart by creating a new instance
        bot_rebooted = LiveCryptoBot(initial_capital=100.0, fixed_risk_usd=1.0)
        
        # 3. Assert full recovery
        self.assertEqual(bot_rebooted.current_balance, 105.42)
        self.assertIn("BTCUSDT", bot_rebooted.open_positions)
        self.assertTrue(any(t.get("symbol") == "ETHUSDT" for t in bot_rebooted.closed_trades))

if __name__ == '__main__':
    unittest.main()
