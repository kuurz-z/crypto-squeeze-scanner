import unittest
import asyncio
import os
import json
import tempfile
import shutil
import pandas as pd
import numpy as np
from live_bot import LiveCryptoBot

class TestLiveBotEngine(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.bot = LiveCryptoBot(
            initial_capital=100.0,
            fixed_risk_usd=1.0,
            timeframe="15m", 
            max_open_positions=3, 
            target_rr=2.0, 
            scan_interval_sec=5,
            data_dir=self.test_dir
        )
        self.bot.open_positions = {}
        self.bot.closed_trades = []
        self.bot.current_balance = 100.0

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

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
        # Simulate having previous losing trades
        self.bot.closed_trades = [
            {"trade_id": 1, "symbol": "BONKUSDT", "outcome": "LOSS", "net_r": -1.08, "pnl_usd": -1.08},
            {"trade_id": 2, "symbol": "BONKUSDT", "outcome": "LOSS", "net_r": -1.08, "pnl_usd": -1.08}
        ]
        self.bot.current_balance = 0.50
        self.bot.is_depleted = True
        self.bot.reset_account(100.0)

        # Balance must be $100.00
        self.assertEqual(self.bot.current_balance, 100.0)
        self.assertFalse(self.bot.is_depleted)
        self.assertIsNone(self.bot.depletion_report_file)
        # Trade history must be strictly preserved
        self.assertEqual(len(self.bot.closed_trades), 2)

        # Telemetry must report $100.00 balance and not overwrite it with historical losses
        t = self.bot.get_telemetry()
        self.assertEqual(t['current_balance'], 100.0)
        self.assertEqual(t['total_closed_trades'], 2)

    def test_dynamic_exit_breakeven_and_trailing(self):
        """Verify the 3-Stage Milestone Exit Ladder (+1.0R BE defense, +1.8R Profit Lock at +1.0R, +3.0R Runner at +2.2R)."""
        # Open a mock LONG position
        self.bot.open_positions["BTCUSDT"] = {
            "trade_id": 1,
            "symbol": "BTCUSDT",
            "strategy": "Trend_Pullback_Confluence",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 100.0,
            "current_price": 100.0,
            "sl_price": 90.0,
            "tp_price": 130.0,
            "risk_distance": 10.0,
            "risk_amount_usd": 1.0,
            "target_rr": 3.0,
            "pre_trade_context": {"reason": "Test setup"}
        }

        # Step 1: Candle advancing to +1.2R (High = 112.0, Close = 111.0, Low = 100.0) -> Stage 1 Breakeven Defense (+0.08R)
        df_step1 = pd.DataFrame([{
            'time': 1700000900,
            'close': 111.0,
            'high': 112.0,
            'low': 100.0,
            'volume': 1000,
            'atr14': 7.0,
            'momentum': 5.0,
            'rsi14': 60.0
        }])

        asyncio.run(self.bot._update_open_positions({"BTCUSDT": df_step1}))
        pos = self.bot.open_positions.get("BTCUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_breakeven'))
        self.assertTrue(pos.get('is_breakeven_protected'))
        self.assertEqual(pos.get('exit_status'), "Breakeven Protected 🛡️")
        self.assertEqual(float(pos['sl_price']), 100.8)  # 100 + 0.08 * 10

        # Step 2: Candle advancing to +1.9R (High = 119.0, Close = 118.5, Low = 108.0) -> Stage 2 Guaranteed Profit Lock (+1.0R)
        df_step2 = pd.DataFrame([{
            'time': 1700001800,
            'close': 118.5,
            'high': 119.0,
            'low': 108.0,
            'volume': 1200,
            'atr14': 7.0,
            'momentum': 8.0,
            'rsi14': 65.0
        }])

        asyncio.run(self.bot._update_open_positions({"BTCUSDT": df_step2}))
        pos = self.bot.open_positions.get("BTCUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_profit_locked'))
        self.assertEqual(pos.get('exit_status'), "Profit Locked 🔒 (+1.0R)")
        self.assertEqual(float(pos['sl_price']), 110.0)  # 100 + 1.0 * 10

        # Step 3: Candle advancing to +3.2R (High = 132.0, Close = 131.0, Low = 118.0) -> Stage 3 Unlimited Runner Mode (+2.2R lock & 0.8x ATR trailing)
        # Lock price = 100 + 2.2 * 10 = 122.0. Trail SL = 131.0 - 0.8 * 5.0 = 127.0. Best SL = 127.0.
        df_step3 = pd.DataFrame([{
            'time': 1700002700,
            'close': 131.0,
            'high': 132.0,
            'low': 118.0,
            'volume': 1500,
            'atr14': 5.0,
            'momentum': 10.0,
            'rsi14': 70.0
        }])

        asyncio.run(self.bot._update_open_positions({"BTCUSDT": df_step3}))
        pos = self.bot.open_positions.get("BTCUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_unlimited_runner'))
        self.assertEqual(pos.get('exit_status'), "Profit Runner 🚀 (+2.2R+)")
        self.assertEqual(float(pos['sl_price']), 127.0)

        # Step 4: Pullback triggering trailing stop (Low = 126.5 <= 127.0)
        df_step4 = pd.DataFrame([{
            'time': 1700003600,
            'close': 126.8,
            'high': 129.0,
            'low': 126.5,
            'volume': 800,
            'atr14': 5.0,
            'momentum': -1.0,
            'rsi14': 55.0
        }])

        asyncio.run(self.bot._update_open_positions({"BTCUSDT": df_step4}))
        self.assertNotIn("BTCUSDT", self.bot.open_positions)
        self.assertEqual(len(self.bot.closed_trades), 1)
        last_trade = self.bot.closed_trades[-1]
        self.assertEqual(last_trade['outcome'], "TRAILING_STOP_WIN")
        self.assertGreaterEqual(last_trade['net_r'], 2.6)

    def test_three_stage_milestone_ladder_short(self):
        """Verify 3-Stage Milestone Exit Ladder for SHORT positions."""
        self.bot.open_positions["ETHUSDT"] = {
            "trade_id": 2,
            "symbol": "ETHUSDT",
            "strategy": "Trend_Pullback_Confluence",
            "direction": "SHORT",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 100.0,
            "current_price": 100.0,
            "sl_price": 110.0,
            "tp_price": 70.0,
            "risk_distance": 10.0,
            "risk_amount_usd": 1.0,
            "target_rr": 3.0,
            "pre_trade_context": {"reason": "Test short setup"}
        }

        # Step 1: Low = 88.0 (+1.2R MFE) -> Stage 1 Breakeven Defense (SL = 100 - 0.08*10 = 99.2)
        df_step1 = pd.DataFrame([{
            'time': 1700000900,
            'close': 89.0,
            'high': 100.0,
            'low': 88.0,
            'volume': 1000,
            'atr14': 5.0,
            'momentum': -5.0,
            'rsi14': 40.0
        }])
        asyncio.run(self.bot._update_open_positions({"ETHUSDT": df_step1}))
        pos = self.bot.open_positions.get("ETHUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_breakeven'))
        self.assertEqual(float(pos['sl_price']), 99.2)

        # Step 2: Low = 81.0 (+1.9R MFE) -> Stage 2 Profit Lock (SL = 100 - 1.0*10 = 90.0)
        df_step2 = pd.DataFrame([{
            'time': 1700001800,
            'close': 81.5,
            'high': 92.0,
            'low': 81.0,
            'volume': 1200,
            'atr14': 5.0,
            'momentum': -8.0,
            'rsi14': 35.0
        }])
        asyncio.run(self.bot._update_open_positions({"ETHUSDT": df_step2}))
        pos = self.bot.open_positions.get("ETHUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_profit_locked'))
        self.assertEqual(float(pos['sl_price']), 90.0)

        # Step 3: Low = 67.0 (+3.3R MFE), Close = 68.0, ATR = 4.0 -> Stage 3 Runner Mode
        # Lock price = 100 - 2.2*10 = 78.0. Trail SL = 68.0 + 0.8*4.0 = 71.2. Best SL = min(90.0, 78.0, 71.2) = 71.2
        df_step3 = pd.DataFrame([{
            'time': 1700002700,
            'close': 68.0,
            'high': 82.0,
            'low': 67.0,
            'volume': 1500,
            'atr14': 4.0,
            'momentum': -10.0,
            'rsi14': 25.0
        }])
        asyncio.run(self.bot._update_open_positions({"ETHUSDT": df_step3}))
        pos = self.bot.open_positions.get("ETHUSDT")
        self.assertIsNotNone(pos)
        self.assertTrue(pos.get('is_unlimited_runner'))
        self.assertEqual(float(pos['sl_price']), 71.2)

        # Step 4: Rebound triggering trailing stop (High = 72.0 >= 71.2)
        df_step4 = pd.DataFrame([{
            'time': 1700003600,
            'close': 71.5,
            'high': 72.0,
            'low': 70.0,
            'volume': 800,
            'atr14': 4.0,
            'momentum': 2.0,
            'rsi14': 40.0
        }])
        asyncio.run(self.bot._update_open_positions({"ETHUSDT": df_step4}))
        self.assertNotIn("ETHUSDT", self.bot.open_positions)
        self.assertEqual(len(self.bot.closed_trades), 1)
        self.assertEqual(self.bot.closed_trades[-1]['outcome'], "TRAILING_STOP_WIN")
        self.assertGreaterEqual(self.bot.closed_trades[-1]['net_r'], 2.7)

    def test_four_hour_loss_quarantine_enforcement(self):
        """Verify that a loss enforces a 4-hour anti-churn quarantine while BE/Time exits enforce 2 hours."""
        from datetime import timedelta
        from live_bot import ph_now

        # 1. Test Single LOSS -> 4-hour quarantine
        self.bot.open_positions["LTCUSDT"] = {
            "trade_id": 10,
            "symbol": "LTCUSDT",
            "direction": "LONG",
            "entry_price": 50.0,
            "sl_price": 45.0,
            "risk_distance": 5.0,
            "risk_amount_usd": 1.0,
            "target_rr": 3.0
        }
        asyncio.run(self.bot._close_position("LTCUSDT", exit_price=45.0, exit_time=1700000000, outcome="LOSS"))
        
        self.assertIn("LTCUSDT", self.bot.symbol_loss_cooldowns)
        cooldown_expiry = self.bot.symbol_loss_cooldowns["LTCUSDT"]
        time_diff = cooldown_expiry - ph_now()
        # Cooldown should be ~4 hours (e.g. between 3.9h and 4.1h)
        self.assertGreater(time_diff.total_seconds(), 3.9 * 3600)
        self.assertLess(time_diff.total_seconds(), 4.1 * 3600)

        # 2. Test BE_EXIT / TIME_EXIT -> 2-hour consolidation cooldown
        self.bot.open_positions["AVAXUSDT"] = {
            "trade_id": 11,
            "symbol": "AVAXUSDT",
            "direction": "LONG",
            "entry_price": 20.0,
            "sl_price": 18.0,
            "risk_distance": 2.0,
            "risk_amount_usd": 1.0,
            "target_rr": 3.0
        }
        asyncio.run(self.bot._close_position("AVAXUSDT", exit_price=20.16, exit_time=1700000000, outcome="BE_EXIT"))
        self.assertIn("AVAXUSDT", self.bot.symbol_loss_cooldowns)
        be_diff = self.bot.symbol_loss_cooldowns["AVAXUSDT"] - ph_now()
        self.assertGreater(be_diff.total_seconds(), 1.9 * 3600)
        self.assertLess(be_diff.total_seconds(), 2.1 * 3600)

        # 3. Test 2 consecutive losses -> 24-hour lockout
        self.bot.open_positions["LTCUSDT"] = {
            "trade_id": 12,
            "symbol": "LTCUSDT",
            "direction": "LONG",
            "entry_price": 50.0,
            "sl_price": 45.0,
            "risk_distance": 5.0,
            "risk_amount_usd": 1.0,
            "target_rr": 3.0
        }
        asyncio.run(self.bot._close_position("LTCUSDT", exit_price=45.0, exit_time=1700000000, outcome="LOSS"))
        lockout_diff = self.bot.symbol_loss_cooldowns["LTCUSDT"] - ph_now()
        self.assertGreater(lockout_diff.total_seconds(), 23.9 * 3600)

    def test_stagnation_exit_behavior_and_exemptions(self):
        """Verify stagnation exit triggers after 12 bars on 15m in dead chop, but exempts >= +0.8R MFE or profit locked."""
        self.bot.set_timeframe("15m")
        
        # 1. Stagnant position with MFE < 0.8R and bars_held >= 12 -> exits on TIME_EXIT
        self.bot.open_positions["STAG1"] = {
            "trade_id": 20,
            "symbol": "STAG1",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_price": 100.0,
            "sl_price": 95.0,
            "tp_price": 115.0,
            "risk_distance": 5.0,
            "bars_held": 12,
            "entry_candle_time": 1000
        }
        df_chop = pd.DataFrame([{
            'time': 2000,
            'close': 100.5,
            'high': 101.0,  # MFE = 1.0 / 5.0 = 0.2R (< 0.8R)
            'low': 99.5,
            'volume': 500,
            'atr14': 2.0,
            'momentum': 0.0,
            'rsi14': 50.0
        }])
        asyncio.run(self.bot._update_open_positions({"STAG1": df_chop}))
        self.assertNotIn("STAG1", self.bot.open_positions)
        self.assertEqual(self.bot.closed_trades[-1]['outcome'], "TIME_EXIT")

        # 2. Position with MFE >= 0.8R held for 12 bars -> EXEMPT from stagnation exit
        self.bot.open_positions["STAG2"] = {
            "trade_id": 21,
            "symbol": "STAG2",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_price": 100.0,
            "sl_price": 95.0,
            "tp_price": 115.0,
            "risk_distance": 5.0,
            "bars_held": 12,
            "highest_since_entry": 104.5, # MFE = 4.5 / 5.0 = 0.9R (>= 0.8R)
            "entry_candle_time": 1000
        }
        df_pullback = pd.DataFrame([{
            'time': 2000,
            'close': 100.5,
            'high': 101.0,
            'low': 99.5,
            'volume': 500,
            'atr14': 2.0,
            'momentum': 0.0,
            'rsi14': 50.0
        }])
        asyncio.run(self.bot._update_open_positions({"STAG2": df_pullback}))
        self.assertIn("STAG2", self.bot.open_positions)

        # 3. Position with is_profit_locked = True -> EXEMPT from stagnation exit
        self.bot.open_positions["STAG3"] = {
            "trade_id": 22,
            "symbol": "STAG3",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_price": 100.0,
            "sl_price": 95.0,
            "tp_price": 115.0,
            "risk_distance": 5.0,
            "bars_held": 12,
            "is_profit_locked": True,
            "entry_candle_time": 1000
        }
        asyncio.run(self.bot._update_open_positions({"STAG3": df_chop}))
        self.assertIn("STAG3", self.bot.open_positions)

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
            'open': [120.0] * 59 + [146.0],
            'high': [125.0] * 59 + [152.0],
            'low': [118.0] * 59 + [144.5],
            'close': [122.0] * 59 + [148.0],
            'volume': [1000] * 59 + [5000],
            'squeeze_on': [False] * 60,
            'bb_upper': [160] * 60,
            'bb_lower': [100] * 60,
            'ema20': [145.0] * 60,
            'ema50': [140.0] * 60,
            'ema200': [120.0] * 60,
            'atr14': [5.0] * 60,
            'rsi14': [48.0] * 60,
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
            'open': [12.0] * 59 + [14.0],
            'high': [13.0] * 59 + [15.2],
            'low': [11.0] * 59 + [13.9],
            'close': [12.5] * 59 + [15.0],
            'volume': [1000] * 59 + [5000],
            'squeeze_on': [False] * 60,
            'bb_upper': [16] * 60,
            'bb_lower': [10] * 60,
            'ema20': [14.0] * 60,
            'ema50': [13.0] * 60,
            'ema200': [11.0] * 60,
            'atr14': [0.5] * 60,
            'rsi14': [48.0] * 60,
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
        
        archive_path = self.bot.archive_file
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
        bot_rebooted = LiveCryptoBot(initial_capital=100.0, fixed_risk_usd=1.0, data_dir=self.test_dir)
        
        # 3. Assert full recovery
        self.assertEqual(bot_rebooted.current_balance, 105.42)
        self.assertIn("BTCUSDT", bot_rebooted.open_positions)
        self.assertTrue(any(t.get("symbol") == "ETHUSDT" for t in bot_rebooted.closed_trades))

    def test_signals_only_mode_blocks_trade_execution(self):
        """Verify that when auto_trading_enabled is False, scanner discovers signals but opens 0 trades."""
        self.bot.auto_trading_enabled = False
        
        # Mock dataframe with squeeze breakout
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        df = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": np.linspace(100, 110, 60),
            "high": np.linspace(101, 112, 60),
            "low": np.linspace(99, 109, 60),
            "close": np.linspace(100, 111, 60),
            "volume": np.full(60, 5000.0)
        })
        
        data_map = {"SOLUSDT": df}
        asyncio.run(self.bot._scan_new_entries(data_map))
        
        # Assert no positions were opened because auto-trading was disabled
        self.assertEqual(len(self.bot.open_positions), 0)

    def test_toggle_auto_trading(self):
        """Verify toggle_auto_trading toggles state and persists."""
        self.assertTrue(self.bot.auto_trading_enabled)
        new_state = self.bot.toggle_auto_trading()
        self.assertFalse(new_state)
        self.assertFalse(self.bot.auto_trading_enabled)
        
        re_enabled = self.bot.toggle_auto_trading()
        self.assertTrue(re_enabled)
        self.assertTrue(self.bot.auto_trading_enabled)

    def test_database_persistence_layer(self):
        """Verify that DatabaseManager saves and loads trades, positions, and state correctly."""
        from db import DatabaseManager
        db_mgr = DatabaseManager(data_dir=self.test_dir)
        
        # 1. Test Trade Save/Load
        sample_trade = {
            "trade_id": 501,
            "symbol": "LINKUSDT",
            "sector": "INFRASTRUCTURE",
            "strategy": "Squeeze_Momentum_Breakout",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "exit_time": 1700003600,
            "exit_time_str": "2026-08-20 13:00:00",
            "entry_price": 20.0,
            "exit_price": 22.0,
            "sl_price": 19.0,
            "tp_price": 22.0,
            "target_rr": 2.0,
            "risk_amount_usd": 1.0,
            "position_qty": 1.0,
            "position_value_usd": 20.0,
            "outcome": "WIN",
            "raw_r": 2.0,
            "net_r": 2.0,
            "pnl_usd": 2.0,
            "account_balance": 102.0,
            "mfe_r": 2.1,
            "mae_r": 0.2,
            "bars_held": 4,
            "diagnostic": {"catalyst_type": "CLEAN_EXPANSION", "summary": "Reached TP"},
            "pre_trade_context": {"rvol": 1.8, "rsi": 58.0}
        }
        db_mgr.save_trade(sample_trade)
        loaded = db_mgr.get_trades()
        self.assertTrue(any(t["trade_id"] == 501 and t["symbol"] == "LINKUSDT" for t in loaded))
        
        # 2. Test Position Save/Load
        db_mgr.save_positions({"LINKUSDT": {"symbol": "LINKUSDT", "entry_price": 20.0}})
        pos = db_mgr.get_positions()
        self.assertIn("LINKUSDT", pos)
        self.assertEqual(pos["LINKUSDT"]["entry_price"], 20.0)

        # 3. Test Bot State Save/Load
        db_mgr.save_state("bot_state", {"current_balance": 102.0, "active_strategy_name": "Squeeze_Momentum_Breakout"})
        state = db_mgr.get_state("bot_state")
        self.assertIsNotNone(state)
        self.assertEqual(state.get("current_balance"), 102.0)

    def test_symbol_loss_cooldown_blocks_immediate_reentry(self):
        """Verify that losing on a symbol sets a cooldown that blocks immediate repetitive re-entries."""
        from datetime import timedelta
        from live_bot import ph_now
        
        # 1. Open mock position on HOMEUSDT
        self.bot.open_positions["HOMEUSDT"] = {
            "trade_id": 101,
            "symbol": "HOMEUSDT",
            "strategy": "Squeeze_Momentum_Breakout",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 0.01,
            "current_price": 0.01,
            "sl_price": 0.009,
            "tp_price": 0.012,
            "risk_distance": 0.001,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0,
            "pre_trade_context": {"reason": "Test setup"}
        }

        # 2. Close with LOSS
        mock_df = pd.DataFrame([{
            'time': 1700000100,
            'open': 0.01,
            'high': 0.0101,
            'low': 0.0089,
            'close': 0.0089,
            'volume': 1000,
            'atr14': 0.001,
            'momentum': -1.0,
            'rsi14': 40.0
        }])
        asyncio.run(self.bot._close_position("HOMEUSDT", exit_price=0.0089, exit_time=1700000100, outcome="LOSS", df=mock_df))

        # Check that HOMEUSDT is now under cooldown
        self.assertIn("HOMEUSDT", self.bot.symbol_loss_cooldowns)
        self.assertGreater(self.bot.symbol_loss_cooldowns["HOMEUSDT"], ph_now())

        # 3. Simulate another scan immediately with pullback signal
        dates = pd.date_range("2026-01-01", periods=60, freq="15min")
        df_entry = pd.DataFrame({
            "time": [int(d.timestamp()) for d in dates],
            "open": [0.015] * 59 + [0.017],
            "high": [0.016] * 59 + [0.021],
            "low": [0.014] * 59 + [0.0169],
            "close": [0.0155] * 59 + [0.020],
            "volume": np.full(60, 5000.0),
            "squeeze_on": [False] * 60,
            "bb_upper": [0.025] * 60,
            "bb_lower": [0.010] * 60,
            "ema20": [0.017] * 60,
            "ema50": [0.015] * 60,
            "ema200": [0.012] * 60,
            "atr14": [0.001] * 60,
            "rsi14": [48.0] * 60,
            "momentum": [1.0] * 60,
            "rvol": [2.5] * 60
        })
        asyncio.run(self.bot._scan_new_entries({"HOMEUSDT": df_entry}))
        # Must be blocked by anti-churn quarantine
        self.assertNotIn("HOMEUSDT", self.bot.open_positions)

        # 4. Fast-forward past cooldown
        self.bot.symbol_loss_cooldowns["HOMEUSDT"] = ph_now() - timedelta(seconds=1)
        self.bot.symbol_last_entry_candle.clear()
        asyncio.run(self.bot._scan_new_entries({"HOMEUSDT": df_entry}))
        # Now allowed to re-enter
        self.assertIn("HOMEUSDT", self.bot.open_positions)

    def test_failure_diagnostics_and_defensive_adaptation(self):
        """Verify that systemic wick trap failures trigger defensive biasing and quarantine."""
        # Inject 6 consecutive fast wick losses
        for i in range(1, 7):
            self.bot.closed_trades.append({
                "trade_id": i,
                "symbol": "SNXXBUSDT",
                "outcome": "LOSS",
                "net_r": -1.08,
                "bars_held": 1,
                "diagnostic": {"catalyst_type": "Immediate Liquidity Wick / Trap"}
            })

        diag = self.bot._analyze_recent_trade_failures()
        self.assertTrue(diag["wick_defense_active"])
        self.assertGreaterEqual(diag["min_atr_mult"], 1.60)
        self.assertIn("SNXXBUSDT", diag["quarantined_symbols"])

        # Check candidate parameters reflect defensive minimums
        candidates = self.bot._generate_candidate_parameters(diag)
        self.assertGreater(len(candidates), 5)
        for c in candidates:
            self.assertGreaterEqual(c["atr_sl_mult"], 1.60)
            self.assertGreaterEqual(c["rvol_min"], 1.30)

    def test_dynamic_walk_forward_optimization_run(self):
        """Verify that run_self_optimization completes with structured diagnostic reporting."""
        # Mock symbols
        self.bot.symbols = ["BTCUSDT", "ETHUSDT"]
        
        opt_entry = asyncio.run(self.bot.run_self_optimization())
        self.assertIsNotNone(opt_entry)
        self.assertIn("status", opt_entry)
        self.assertIn("champion_stats", opt_entry)
        self.assertIn("challenger_summary", opt_entry)
        self.assertIn("failure_diagnostic", opt_entry)
        self.assertIn("summary", opt_entry)
        self.assertIn("report_file", opt_entry)
        self.assertTrue(os.path.exists(opt_entry["report_file"]))

    def test_timeframe_profiles_and_switching(self):
        """Verify that timeframe profiles load correctly, set_timeframe allows 15m and 30m, and blocks 1h/4h/1d."""
        # 1. Default profile on 15m (1h MTF Anchor)
        self.assertEqual(self.bot.timeframe, "15m")
        self.assertEqual(self.bot.timeframe_profile["anchor_tf"], "1h")
        self.assertEqual(self.bot.timeframe_profile["max_holding_bars"], 64)
        self.assertEqual(self.bot.timeframe_profile["stagnation_bars"], 12)
        self.assertEqual(self.bot.cooldown_minutes, 45)

        # 2. Switch to 30m (4h MTF Anchor)
        res = self.bot.set_timeframe("30m")
        self.assertTrue(res)
        self.assertEqual(self.bot.timeframe, "30m")
        self.assertEqual(self.bot.timeframe_profile["anchor_tf"], "4h")
        self.assertEqual(self.bot.timeframe_profile["max_holding_bars"], 64)
        self.assertEqual(self.bot.timeframe_profile["stagnation_bars"], 10)
        self.assertEqual(self.bot.cooldown_minutes, 90)

        # 3. 1h, 4h, 1d, 99m are strictly rejected
        self.assertFalse(self.bot.set_timeframe("1h"))
        self.assertFalse(self.bot.set_timeframe("4h"))
        self.assertFalse(self.bot.set_timeframe("1d"))
        self.assertFalse(self.bot.set_timeframe("99m"))
        self.assertEqual(self.bot.timeframe, "30m")

    def test_timeframe_stagnation_and_horizon_exit(self):
        """Verify that time stagnation and max horizon exits trigger at timeframe-specific bar thresholds."""
        self.bot.set_timeframe("15m")
        self.bot.open_positions["ETHUSDT"] = {
            "trade_id": 99,
            "symbol": "ETHUSDT",
            "strategy": "Squeeze_Momentum_Breakout",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 2000.0,
            "current_price": 2002.0,
            "sl_price": 1950.0,
            "tp_price": 2100.0,
            "risk_distance": 50.0,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0,
            "bars_held": 23,
            "pre_trade_context": {"reason": "Test stagnation"}
        }

        # Mock candle with negligible progress (< 0.4R = < $20 move)
        df_chop = pd.DataFrame([{
            'time': 1700000900,
            'close': 2003.0,
            'high': 2005.0,
            'low': 1995.0,
            'volume': 500,
            'atr14': 30.0,
            'momentum': 0.1,
            'rsi14': 50.0
        }])

        # Advance to 24 bars held -> should trigger stagnation exit on 15m
        asyncio.run(self.bot._update_open_positions({"ETHUSDT": df_chop}))
        self.assertNotIn("ETHUSDT", self.bot.open_positions)
        self.assertEqual(len(self.bot.closed_trades), 1)
        self.assertEqual(self.bot.closed_trades[-1]['outcome'], "TIME_EXIT")

    def test_force_close_position_long_profit(self):
        """Verify manual forced closing of a profitable LONG position."""
        self.bot.open_positions["BTCUSDT"] = {
            "trade_id": 101,
            "symbol": "BTCUSDT",
            "sector": "LAYER_1",
            "strategy": "Squeeze_Momentum_Breakout",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 50000.0,
            "current_price": 51000.0,
            "sl_price": 49000.0,
            "tp_price": 52000.0,
            "risk_distance": 1000.0,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0,
            "bars_held": 5,
            "pre_trade_context": {"reason": "Test setup"}
        }

        # Force close at 51000 (+1.0R gross, -0.08R friction = +0.92R net)
        trade = asyncio.run(self.bot.force_close_position("BTCUSDT", exit_price=51000.0))

        self.assertIsNotNone(trade)
        self.assertNotIn("BTCUSDT", self.bot.open_positions)
        self.assertEqual(len(self.bot.closed_trades), 1)
        self.assertEqual(trade['outcome'], "FORCED_CLOSE")
        self.assertEqual(trade['exit_price'], 51000.0)
        self.assertEqual(trade['raw_r'], 1.0)
        self.assertEqual(trade['net_r'], 0.92)
        self.assertEqual(trade['pnl_usd'], 0.92)
        self.assertEqual(self.bot.current_balance, 100.92)
        self.assertIn("Manual Forced Close", trade['diagnostic']['catalyst_type'])

    def test_force_close_position_short_loss(self):
        """Verify manual forced closing of a losing SHORT position."""
        self.bot.open_positions["SOLUSDT"] = {
            "trade_id": 102,
            "symbol": "SOLUSDT",
            "sector": "LAYER_1",
            "strategy": "Squeeze_Momentum_Breakout",
            "timeframe": "15m",
            "direction": "SHORT",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 100.0,
            "current_price": 105.0,
            "sl_price": 110.0,
            "tp_price": 80.0,
            "risk_distance": 10.0,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0,
            "bars_held": 3,
            "pre_trade_context": {"reason": "Test short setup"}
        }

        # Short entered at 100, price rose to 105 (-0.5R gross, -0.08R friction = -0.58R net)
        trade = asyncio.run(self.bot.force_close_position("SOLUSDT", exit_price=105.0))

        self.assertIsNotNone(trade)
        self.assertNotIn("SOLUSDT", self.bot.open_positions)
        self.assertEqual(len(self.bot.closed_trades), 1)
        self.assertEqual(trade['outcome'], "FORCED_CLOSE")
        self.assertEqual(trade['exit_price'], 105.0)
        self.assertEqual(trade['raw_r'], -0.5)
        self.assertEqual(trade['net_r'], -0.58)
        self.assertEqual(trade['pnl_usd'], -0.58)
        self.assertEqual(self.bot.current_balance, 99.42)

    def test_force_close_nonexistent_position(self):
        """Verify attempting to force close a position that does not exist returns None safely."""
        trade = asyncio.run(self.bot.force_close_position("NONEXISTENT"))
        self.assertIsNone(trade)

    def test_force_close_position_api_endpoint(self):
        """Verify the FastAPI HTTP POST /api/bot/positions/{symbol}/close endpoint."""
        from fastapi.testclient import TestClient
        from app import app
        from live_bot import bot_instance

        # Seed an open position in the global bot_instance
        bot_instance.open_positions["TESTUSDT"] = {
            "trade_id": 999,
            "symbol": "TESTUSDT",
            "sector": "MEMES",
            "strategy": "Squeeze_Momentum_Breakout",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-20 12:00:00",
            "entry_price": 1.0,
            "current_price": 1.10,
            "sl_price": 0.90,
            "tp_price": 1.20,
            "risk_distance": 0.10,
            "risk_amount_usd": 1.0,
            "target_rr": 2.0,
            "bars_held": 2,
            "pre_trade_context": {"reason": "API test"}
        }

        client = TestClient(app)

        # 1. Close active position
        response = client.post("/api/bot/positions/TESTUSDT/close", json={"exit_price": 1.10})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["trade"]["symbol"], "TESTUSDT")
        self.assertEqual(data["trade"]["outcome"], "FORCED_CLOSE")
        self.assertNotIn("TESTUSDT", bot_instance.open_positions)

        # 2. 404 when closing again
        response_404 = client.post("/api/bot/positions/TESTUSDT/close", json={})
        self.assertEqual(response_404.status_code, 404)

    def test_telemetry_returns_all_closed_trades_unlimited(self):
        # Populate bot with 25 closed trades
        self.bot.closed_trades = [
            {
                "trade_id": i,
                "symbol": f"COIN{i}USDT",
                "direction": "LONG",
                "entry_time_str": "2026-08-20 12:00:00",
                "exit_time_str": "2026-08-20 13:00:00",
                "entry_price": 10.0,
                "exit_price": 11.0,
                "outcome": "WIN",
                "net_r": 1.0,
                "pnl_usd": 1.0,
                "bars_held": 2
            }
            for i in range(1, 26)
        ]
        telemetry = self.bot.get_telemetry()
        self.assertEqual(len(telemetry["recent_journal"]), 25)
        self.assertEqual(telemetry["total_closed_trades"], 25)
        # Verify newest trade is first
        self.assertEqual(telemetry["recent_journal"][0]["trade_id"], 25)
        self.assertEqual(telemetry["recent_journal"][-1]["trade_id"], 1)

    def test_triple_and_dual_timeframe_switching_and_profiles(self):
        """Verify that setting timeframe to 5m, dual, and triple sets up proper profiles."""
        # 1. Test 5m
        self.assertTrue(self.bot.set_timeframe("5m"))
        self.assertEqual(self.bot.timeframe, "5m")
        self.assertEqual(self.bot.timeframe_profile["anchor_tf"], "30m")
        self.assertEqual(self.bot.scan_interval_sec, 15)

        # 2. Test dual
        self.assertTrue(self.bot.set_timeframe("dual"))
        self.assertEqual(self.bot.timeframe, "dual")
        self.assertEqual(self.bot.scan_interval_sec, 20)

        # 3. Test triple
        self.assertTrue(self.bot.set_timeframe("triple"))
        self.assertEqual(self.bot.timeframe, "triple")
        self.assertEqual(self.bot.scan_interval_sec, 15)

        # 4. Telemetry reflects triple mode
        t = self.bot.get_telemetry()
        self.assertEqual(t["timeframe"], "triple")

    def test_mixed_timeframe_dynamic_holding_rules(self):
        """Verify that open positions with 5m, 15m, and 30m adhere to their respective max holding bars and stagnation limits."""
        # Create a mock dataframe
        df = pd.DataFrame({
            "close": [100.0] * 70,
            "open": [100.0] * 70,
            "high": [100.5] * 70,
            "low": [99.5] * 70,
            "atr14": [1.0] * 70,
            "momentum": [0.0] * 70,
            "rsi14": [50.0] * 70
        })

        # 5m position held for 25 bars in dead chop -> should exit on stagnation (stagnation_bars: 24)
        self.bot.open_positions["SCALP_COIN"] = {
            "trade_id": 101,
            "symbol": "SCALP_COIN",
            "timeframe": "5m",
            "direction": "LONG",
            "entry_price": 100.0,
            "sl_price": 98.0,
            "tp_price": 104.0,
            "risk_distance": 2.0,
            "bars_held": 25,
            "entry_candle_time": 1000
        }

        asyncio.run(self.bot._update_open_positions({"SCALP_COIN": df}))
        self.assertNotIn("SCALP_COIN", self.bot.open_positions)
        self.assertEqual(self.bot.closed_trades[-1]["outcome"], "TIME_EXIT")

if __name__ == '__main__':
    unittest.main()


