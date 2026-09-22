"""Acceptance tests for the runtime adapter, with isolated paper accounts."""
import asyncio
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import pandas as pd

from execution import create_position, process_price
from live_bot import LiveCryptoBot


class BotRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="paper-bot-test-")
        self.addCleanup(self.temp.cleanup)
        self.bot = LiveCryptoBot(data_dir=self.temp.name)
        self.start = 1787644800

    def position(self, symbol="BTCUSDT", timestamp=None):
        timestamp = self.start + 100 if timestamp is None else timestamp
        pos = create_position("LONG", 100, 10, 1, 2, timestamp,
                              self.bot.fee_pct, self.bot.slippage_pct)
        pos.update(trade_id=1, symbol=symbol, strategy=self.bot.active_strategy_name,
                   timeframe="15m", sector="LAYER_1", entry_candle_time=self.start,
                   last_completed_candle_time=self.start - 900,
                   forward_run_id=self.bot.forward_run_id, pre_trade_context={},
                   configuration=copy.deepcopy(self.bot.forward_run_config))
        self.bot.open_positions[symbol] = pos
        self.bot.current_balance += pos["entry_cash_delta_usd"]
        return pos

    def frame(self, times, close=100, high=101, low=99):
        return pd.DataFrame([dict(time=t, close_time=t+899.999, open=100,
                                  close=close, high=high, low=low,
                                  atr14=2, momentum=1, rsi14=50) for t in times])

    def test_imports_do_not_construct_or_persist_production_bot(self):
        root = str(Path(__file__).resolve().parent)
        env = dict(os.environ, PYTHONPATH=root, DATABASE_URL="")
        script = "from pathlib import Path; before=set(Path('.').rglob('*')); import live_bot, app; assert live_bot.bot_instance is None; assert app.app.state.bot is None; assert set(Path('.').rglob('*')) == before"
        with tempfile.TemporaryDirectory() as directory:
            subprocess.run([sys.executable, "-B", "-c", script], cwd=directory, env=env, check=True)

    def test_same_candle_polls_and_old_wicks_do_not_count_or_close(self):
        pos = self.position()
        data = {"BTCUSDT": self.frame([self.start], high=120, low=80)}
        with patch("live_bot.time.time", return_value=self.start + 500):
            for _ in range(100):
                asyncio.run(self.bot._update_open_positions(data))
        self.assertEqual(pos["bars_held"], 0)
        self.assertEqual(len(pos["fills"]), 1)
        self.assertFalse(pos["closed"])
        self.bot.save_state()
        rebooted = LiveCryptoBot(data_dir=self.temp.name)
        data = {"BTCUSDT": self.frame([self.start, self.start + 900])}
        with patch("live_bot.time.time", return_value=self.start + 901):
            asyncio.run(rebooted._update_open_positions(data))
            asyncio.run(rebooted._update_open_positions(data))
        self.assertEqual(rebooted.open_positions["BTCUSDT"]["bars_held"], 1)

    def test_missed_completed_candles_are_processed_in_order(self):
        pos = self.position()
        times = [self.start + i * 900 for i in range(5)]
        with patch("live_bot.time.time", return_value=self.start + 3601):
            asyncio.run(self.bot._update_open_positions({"BTCUSDT": self.frame(times)}))
        self.assertEqual(pos["bars_held"], 4)
        with patch("live_bot.time.time", return_value=self.start + 3601):
            asyncio.run(self.bot._update_open_positions({"BTCUSDT": self.frame(times[:2])}))
        self.assertEqual(pos["bars_held"], 4)

    def test_long_restart_fetch_retains_missed_bars_and_warmup(self):
        pos = self.position()
        request = self.bot._position_history_request("BTCUSDT", "15m", self.start + 1000 * 900 + 1)
        self.assertGreater(request["limit"], 1000)
        self.assertEqual(request["start_time"], pos["last_completed_candle_time"] - 199 * 900)
        self.assertEqual(request["end_time"], self.start + 1000 * 900 + 1)
        self.assertEqual(self.bot._position_history_request("BTCUSDT", "1h", self.start + 1), {"limit": 300})
        self.assertEqual(self.bot._position_history_request("BTCUSDT", "15m", self.start + 901), {"limit": 300})

    def test_old_feed_cannot_become_a_fresh_executable_price(self):
        pos = self.position()
        current = self.frame([self.start + 900], close=101)
        with patch("live_bot.time.time", return_value=self.start + 901):
            asyncio.run(self.bot._update_open_positions({"BTCUSDT": current}))
        old = self.frame([self.start - 900], close=70, low=70)
        with patch("live_bot.time.time", return_value=self.start + 902):
            asyncio.run(self.bot._update_open_positions({"BTCUSDT": old}))
        self.assertIn("BTCUSDT", self.bot.open_positions)
        self.assertEqual(len(pos["fills"]), 1)
        self.assertEqual(pos["current_price"], 101)

    def test_partial_restart_final_close_reconcile_once(self):
        pos = self.position()
        event = process_price(pos, 111, self.start + 200)
        self.bot.current_balance += event["cash_delta_usd"]
        self.bot.symbol_last_entry_candle["BTCUSDT:15m"] = self.start - 900
        self.bot.save_state()
        balance = self.bot.current_balance
        rebooted = LiveCryptoBot(data_dir=self.temp.name)
        self.assertAlmostEqual(rebooted.current_balance, balance)
        self.assertEqual(rebooted.open_positions["BTCUSDT"]["fills"], pos["fills"])
        self.assertEqual(rebooted.symbol_last_entry_candle["BTCUSDT:15m"], self.start - 900)
        record = asyncio.run(rebooted._close_position("BTCUSDT", 106, self.start + 300, "MANUAL_CLOSE"))
        self.assertAlmostEqual(rebooted.current_balance - 100, record["pnl_usd"], places=7)
        self.assertEqual(len(record["fills"]), 3)
        self.assertEqual(record["position_qty"], 0)
        again = LiveCryptoBot(data_dir=self.temp.name)
        self.assertEqual(again.closed_trades[0]["fills"], record["fills"])
        self.assertAlmostEqual(again.current_balance, rebooted.current_balance)
        self.assertIsNone(asyncio.run(again._close_position("BTCUSDT", 106, self.start+301, "MANUAL_CLOSE")))
        metrics = again.get_telemetry()["forward_test"]
        self.assertEqual(metrics["closed_trades"], 1)
        self.assertAlmostEqual(metrics["net_pnl_usd"], record["pnl_usd"], places=7)

    def test_snapshot_recovery_never_mixes_compatibility_files(self):
        self.position()
        self.bot.save_state()
        Path(self.bot.state_file).write_text(json.dumps({"current_balance": 9999}))
        Path(self.bot.positions_file).write_text("{}")
        again = LiveCryptoBot(data_dir=self.temp.name)
        self.assertAlmostEqual(again.current_balance, self.bot.current_balance)
        self.assertIn("BTCUSDT", again.open_positions)

    def test_optimizers_report_without_mutating_frozen_configuration(self):
        self.bot.symbol_consecutive_losses = {"BTCUSDT": 2}
        frozen = copy.deepcopy((self.bot.active_params, self.bot.timeframe, self.bot.active_strategy_name,
                                self.bot.symbol_consecutive_losses, self.bot.symbol_loss_cooldowns,
                                self.bot.circuit_breaker_until, self.bot.forward_run_id))
        result = {"status": "NO_VALIDATED_CANDIDATE", "final_results": {}}
        with patch("validation.run_report_only_evaluation", new=AsyncMock(return_value=result)):
            asyncio.run(self.bot.run_self_optimization())
            asyncio.run(self.bot.run_macro_optimization())
            asyncio.run(self.bot.run_monthly_strategy_tournament())
            historical = asyncio.run(self.bot.run_champions_of_champions_gauntlet())
        self.assertEqual(frozen, (self.bot.active_params, self.bot.timeframe, self.bot.active_strategy_name,
                                 self.bot.symbol_consecutive_losses, self.bot.symbol_loss_cooldowns,
                                 self.bot.circuit_breaker_until, self.bot.forward_run_id))
        self.assertIsNone(self.bot.champion_stats["win_rate"])
        self.assertEqual(historical["status"], "HISTORICAL_COMPARISON")

    def test_missing_anchor_blocks_entries_and_records_reason(self):
        now = self.start + 901
        df = self.frame([self.start - (200-i)*900 for i in range(202)])
        with patch("live_bot.time.time", return_value=now), patch.object(self.bot, "_evaluate_active_strategy") as evaluate:
            asyncio.run(self.bot._scan_new_entries({"BTCUSDT": df}))
        evaluate.assert_not_called()
        self.assertEqual(self.bot.open_positions, {})
        self.assertEqual(self.bot.rejected_entries["MISSING_ANCHOR"], 1)

    def test_closed_trade_cannot_reenter_same_signal_after_restart(self):
        now = self.start + 901
        df = self.frame([self.start - (200-i)*900 for i in range(202)])
        anchor_end = (self.start + 900) // 3600 * 3600
        anchor = pd.DataFrame([dict(time=anchor_end-(200-i)*3600,
                                   close_time=anchor_end-(199-i)*3600-0.001,
                                   open=100, high=101, low=99, close=100) for i in range(200)])
        self.bot.mtf_data = {"BTCUSDT": {"1h": anchor}}
        signal = {"direction": "LONG", "risk_distance": 10, "target_rr": 2,
                  "pre_trade_context": {}}
        with patch("live_bot.time.time", return_value=now), \
             patch.object(self.bot, "_evaluate_active_strategy", return_value=signal):
            asyncio.run(self.bot._scan_new_entries({"BTCUSDT": df}))
        self.assertIn("BTCUSDT", self.bot.open_positions)
        asyncio.run(self.bot._close_position("BTCUSDT", 106, now + 1, "MANUAL_CLOSE"))
        self.bot.symbol_loss_cooldowns = {}
        self.bot.save_state()
        again = LiveCryptoBot(data_dir=self.temp.name)
        again.mtf_data = {"BTCUSDT": {"1h": anchor}}
        with patch("live_bot.time.time", return_value=now + 2), \
             patch.object(again, "_evaluate_active_strategy", return_value=signal) as evaluate:
            for _ in range(3):
                asyncio.run(again._scan_new_entries({"BTCUSDT": df}))
            evaluate.assert_not_called()
        self.assertEqual(again.open_positions, {})
        self.assertEqual(len(again.closed_trades), 1)

    def test_api_exposes_complete_fill_record_and_net_outcome(self):
        from fastapi.testclient import TestClient
        import app as api
        self.position()
        with patch.object(api.app.state, "bot", self.bot), \
             patch("live_bot.fetch_symbol_klines", new=AsyncMock(return_value=None)):
            client = TestClient(api.app)
            try:
                result = client.post("/api/bot/positions/BTCUSDT/close", json={"exit_price": 100})
                self.assertEqual(result.status_code, 200)
                trade = result.json()["trade"]
                self.assertEqual(trade["outcome"], "LOSS")
                self.assertEqual(trade["exit_reason"], "FORCED_CLOSE")
                self.assertEqual(trade["position_qty"], 0)
                self.assertEqual(len(trade["fills"]), 2)
                self.assertEqual(trade["forward_run_id"], self.bot.forward_run_id)
                self.assertAlmostEqual(sum(f["cash_delta_usd"] for f in trade["fills"]), trade["pnl_usd"])
                status = client.get("/api/bot/status").json()
                self.assertAlmostEqual(status["current_balance"] - 100, trade["pnl_usd"])
            finally:
                client.close()

    def test_empty_forward_cohort_does_not_include_legacy_history(self):
        self.bot.closed_trades = [{"trade_id": 1, "net_r": -1, "pnl_usd": -1, "outcome": "LOSS"}]
        telemetry = self.bot.get_telemetry()
        self.assertEqual(telemetry["legacy_history"]["trades"], 1)
        self.assertEqual(telemetry["forward_test"]["closed_trades"], 0)
        self.assertIsNone(telemetry["forward_test"]["expectancy_r"])
        self.assertIsNone(telemetry["total_pnl_pct"])

    def test_unreadable_canonical_sources_never_load_legacy_balances(self):
        Path(self.bot.snapshot_file).unlink()
        with patch.object(self.bot.db, "get_portfolio_snapshot", side_effect=ValueError("corrupt remote snapshot")), \
             patch.object(self.bot, "_load_legacy_state") as legacy:
            with self.assertRaises(RuntimeError):
                self.bot.load_state()
            legacy.assert_not_called()

    def test_journal_failure_does_not_lose_durable_close(self):
        self.position()
        blocked = Path(self.temp.name, "not-a-directory")
        blocked.write_text("occupied")
        self.bot.reports_dir = str(blocked)
        record = asyncio.run(self.bot._close_position("BTCUSDT", 102, self.start + 300, "MANUAL_CLOSE"))
        again = LiveCryptoBot(data_dir=self.temp.name)
        self.assertEqual(len(again.closed_trades), 1)
        self.assertEqual(again.open_positions, {})
        self.assertAlmostEqual(again.current_balance - 100, record["pnl_usd"], places=7)


if __name__ == "__main__":
    unittest.main()
