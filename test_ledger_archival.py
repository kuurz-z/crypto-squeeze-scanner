import os
import json
import tempfile
import shutil
import unittest
from trade_journal import archive_and_reset_ledger
from live_bot import LiveCryptoBot
from db import DatabaseManager

class TestLedgerArchival(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.reports_dir = os.path.join(self.test_dir, "reports")
        self.trades_file = os.path.join(self.test_dir, "live_trades.json")
        self.positions_file = os.path.join(self.test_dir, "live_positions.json")
        self.state_file = os.path.join(self.test_dir, "bot_state.json")
        self.archive_file = os.path.join(self.reports_dir, "archive_pre_optimization_trades.json")

    def tearDown(self):
        try:
            shutil.rmtree(self.test_dir)
        except Exception:
            pass

    def test_archive_creation_with_historical_trades(self):
        # 1. Create mock historical trades
        mock_trades = [
            {
                "trade_id": 1,
                "symbol": "BTCUSDT",
                "direction": "LONG",
                "entry_price": 50000.0,
                "exit_price": 51000.0,
                "outcome": "WIN",
                "net_r": 2.0,
                "pnl_usd": 2.0
            },
            {
                "trade_id": 2,
                "symbol": "ETHUSDT",
                "direction": "SHORT",
                "entry_price": 3000.0,
                "exit_price": 3050.0,
                "outcome": "LOSS",
                "net_r": -1.0,
                "pnl_usd": -1.0
            }
        ]
        with open(self.trades_file, "w", encoding="utf-8") as f:
            json.dump(mock_trades, f, indent=2)

        # 2. Create mock positions
        mock_positions = {
            "SOLUSDT": {
                "symbol": "SOLUSDT",
                "direction": "LONG",
                "entry_price": 140.0
            }
        }
        with open(self.positions_file, "w", encoding="utf-8") as f:
            json.dump(mock_positions, f, indent=2)

        # 3. Create mock dirty bot state
        dirty_state = {
            "initial_capital": 100.0,
            "current_balance": 101.0,
            "active_strategy": "Old_Strategy",
            "timeframe": "30m",
            "target_rr": 2.0,
            "open_positions": mock_positions,
            "symbol_loss_cooldowns": {"ETHUSDT": "2026-08-28 01:00:00"},
            "circuit_breaker_until": "2026-08-28 02:00:00"
        }
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(dirty_state, f, indent=2)

        # Execute archive and reset
        archive_res = archive_and_reset_ledger(self.test_dir)

        # Verify archive file
        self.assertEqual(os.path.normpath(archive_res), os.path.normpath(self.archive_file))
        self.assertTrue(os.path.exists(self.archive_file))
        with open(self.archive_file, "r", encoding="utf-8") as f:
            archived_trades = json.load(f)
        self.assertEqual(len(archived_trades), 2)
        self.assertEqual(archived_trades[0]["symbol"], "BTCUSDT")
        self.assertEqual(archived_trades[1]["symbol"], "ETHUSDT")

        # Verify live_trades.json reset
        self.assertTrue(os.path.exists(self.trades_file))
        with open(self.trades_file, "r", encoding="utf-8") as f:
            live_trades = json.load(f)
        self.assertEqual(live_trades, [])

        # Verify live_positions.json reset
        self.assertTrue(os.path.exists(self.positions_file))
        with open(self.positions_file, "r", encoding="utf-8") as f:
            live_pos = json.load(f)
        self.assertEqual(live_pos, {})

        # Verify bot_state.json clean benchmark reset
        self.assertTrue(os.path.exists(self.state_file))
        with open(self.state_file, "r", encoding="utf-8") as f:
            clean_state = json.load(f)
        self.assertEqual(clean_state["initial_capital"], 100.0)
        self.assertEqual(clean_state["current_balance"], 100.0)
        self.assertEqual(clean_state["active_strategy"], "Trend_Pullback_Confluence")
        self.assertEqual(clean_state["timeframe"], "15m")
        self.assertEqual(clean_state["target_rr"], 3.0)
        self.assertEqual(clean_state["open_positions"], {})
        self.assertEqual(clean_state["symbol_loss_cooldowns"], {})
        self.assertIsNone(clean_state["circuit_breaker_until"])
        self.assertIn("last_reset", clean_state)
        self.assertTrue(isinstance(clean_state["last_reset"], str))

    def test_archive_when_empty_or_nonexistent_files(self):
        # Run on empty directory
        archive_res = archive_and_reset_ledger(self.test_dir)
        self.assertTrue(os.path.exists(self.trades_file))
        self.assertTrue(os.path.exists(self.positions_file))
        self.assertTrue(os.path.exists(self.state_file))

        with open(self.trades_file, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), [])

        with open(self.positions_file, "r", encoding="utf-8") as f:
            self.assertEqual(json.load(f), {})

        with open(self.state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
            self.assertEqual(state["initial_capital"], 100.0)
            self.assertEqual(state["current_balance"], 100.0)
            self.assertEqual(state["active_strategy"], "Trend_Pullback_Confluence")
            self.assertEqual(state["timeframe"], "15m")
            self.assertEqual(state["target_rr"], 3.0)

    def test_live_bot_archive_and_reset_method(self):
        bot = LiveCryptoBot(
            initial_capital=100.0,
            fixed_risk_usd=1.0,
            timeframe="30m",
            data_dir=self.test_dir
        )
        bot.closed_trades = [
            {"trade_id": 1, "symbol": "DOGEUSDT", "outcome": "WIN", "net_r": 3.0, "pnl_usd": 3.0}
        ]
        bot.open_positions = {
            "DOGEUSDT": {"symbol": "DOGEUSDT", "direction": "LONG"}
        }
        bot.current_balance = 103.0
        bot.save_state()

        # Call archive_and_reset_ledger on bot instance
        archive_res = bot.archive_and_reset_ledger()
        self.assertTrue(os.path.exists(archive_res))

        # Check bot in-memory attributes reloaded cleanly
        self.assertEqual(bot.closed_trades, [])
        self.assertEqual(bot.open_positions, {})
        self.assertEqual(bot.current_balance, 100.0)
        self.assertEqual(bot.timeframe, "15m")
        self.assertEqual(bot.target_rr, 3.0)
        self.assertEqual(bot.active_strategy_name, "Trend_Pullback_Confluence")

    def test_database_cleanup_on_archival(self):
        db = DatabaseManager(data_dir=self.test_dir)
        db.save_trade({
            "trade_id": 10,
            "symbol": "SOLUSDT",
            "sector": "LAYER_1",
            "strategy": "Trend_Pullback_Confluence",
            "timeframe": "15m",
            "direction": "LONG",
            "entry_time": 1700000000,
            "entry_time_str": "2026-08-28 00:00:00",
            "exit_time": 1700003600,
            "exit_time_str": "2026-08-28 01:00:00",
            "entry_price": 100.0,
            "exit_price": 110.0,
            "sl_price": 95.0,
            "tp_price": 115.0,
            "target_rr": 3.0,
            "risk_amount_usd": 1.0,
            "position_qty": 0.2,
            "position_value_usd": 20.0,
            "outcome": "WIN",
            "raw_r": 2.0,
            "net_r": 1.95,
            "pnl_usd": 1.95,
            "account_balance": 101.95,
            "mfe_r": 2.0,
            "mae_r": 0.2,
            "bars_held": 4,
            "friction_breakdown": "",
            "trade_efficiency": "",
            "diagnostic": {},
            "pre_trade_context": {}
        })
        db.save_positions({"SOLUSDT": {"symbol": "SOLUSDT"}})
        self.assertEqual(len(db.get_trades()), 1)
        self.assertEqual(len(db.get_positions()), 1)

        # Run archive_and_reset_ledger
        archive_and_reset_ledger(self.test_dir)

        # Verify DB is reset
        self.assertEqual(db.get_trades(), [])
        self.assertEqual(db.get_positions(), {})

if __name__ == "__main__":
    unittest.main()
