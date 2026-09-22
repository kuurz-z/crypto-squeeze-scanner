"""Isolated persistence tests: never import the app or its global trading bot."""

import copy
import json
import os
import sqlite3
import tempfile
import types
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock, patch

from db import DatabaseManager, TRADE_COLUMNS, TRADE_DEFAULTS
from persistence import atomic_write_json, load_portfolio_snapshot, validate_portfolio_snapshot
from trade_journal import archive_and_reset_ledger, create_trade_journal_md


def example_trade():
    return {
        "schema_version": 2, "trade_id": 7, "symbol": "BTCUSDT", "strategy": "Example",
        "strategy_version": "example-v2", "forward_run_id": "run-1", "cost_model_version": "fills_v1",
        "strategy_params": {"target_rr": 2.0}, "direction": "LONG", "initial_qty": 0.1,
        "remaining_qty": 0.0, "position_qty": 0.0, "tp1_hit": True, "tp1_rr": 1.0,
        "tp1_price": 110.0, "realized_partial_r": 0.49, "gross_pnl_usd": 0.75,
        "fees_usd": 0.01, "slippage_usd": 0.004, "pnl_usd": 0.74,
        "raw_r": 0.75, "net_r": 0.74, "exit_reason": "STOP", "outcome": "WIN",
        "fills": [{"fill_id": 2, "kind": "TP1", "timestamp": 1700000000,
                   "reference_price": 110.0, "price": 109.978, "quantity": 0.03,
                   "gross_pnl_usd": 0.29934, "fee_usd": 0.00164967,
                   "slippage_usd": 0.00066, "cash_delta_usd": 0.29769033}],
        "diagnostic": {"summary": "Recorded exit"}, "pre_trade_context": {"anchor": "1h"},
    }


def example_snapshot(revision=1):
    return {
        "schema_version": 2, "revision": revision,
        "state": {"current_balance": 100.74, "forward_run_id": "run-1",
                  "symbol_last_entry_candle": {"BTCUSDT": 1700000000}},
        "open_positions": {"ETHUSDT": {"initial_qty": 1.0, "position_qty": 0.5,
                                      "realized_partial_r": 0.5, "tp1_hit": True,
                                      "fills": [{"fill_id": 2, "kind": "TP1"}]}},
        "closed_trades": [example_trade()],
    }


class TestPersistenceRepair(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="persistence-test-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)

    def test_local_directory_overrides_ambient_remote_url(self):
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://never-connect.invalid/prod"}):
            manager = DatabaseManager(data_dir=self.temp.name)
        self.assertFalse(manager.is_postgres)
        self.assertTrue((self.path / "local_crypto_bot.db").is_file())

    def test_additive_legacy_migration_preserves_original_values(self):
        database_path = self.path / "local_crypto_bot.db"
        columns = []
        for name, default in TRADE_DEFAULTS.items():
            sql_type = "TEXT" if isinstance(default, (str, dict)) else "REAL"
            columns.append("trade_id INTEGER PRIMARY KEY" if name == "trade_id" else f"{name} {sql_type}")
        with closing(sqlite3.connect(database_path)) as conn, conn:
            conn.execute("CREATE TABLE bot_trades (" + ", ".join(columns) + ")")
            conn.execute("INSERT INTO bot_trades (trade_id, symbol, pnl_usd, diagnostic) VALUES (1, 'LEGACY', -1.08, 'old diagnosis')")
            before = conn.execute("SELECT * FROM bot_trades").fetchall()
        manager = DatabaseManager(data_dir=self.temp.name)
        DatabaseManager(data_dir=self.temp.name)  # Migration must be repeatable.
        with closing(sqlite3.connect(database_path)) as conn, conn:
            after = conn.execute("SELECT " + ", ".join(TRADE_COLUMNS) + " FROM bot_trades").fetchall()
            self.assertIsNone(conn.execute("SELECT record_json FROM bot_trades").fetchone()[0])
        self.assertEqual(before, after)
        legacy = manager.get_trades()[0]
        self.assertEqual(legacy["pnl_usd"], -1.08)
        self.assertEqual(legacy["diagnostic"], {"summary": "old diagnosis"})
        self.assertNotIn("schema_version", legacy)

    def test_full_payload_round_trip_and_update_preserve_all_fields(self):
        manager = DatabaseManager(data_dir=self.temp.name)
        trade = example_trade()
        manager.save_trade(trade)
        self.assertEqual(manager.get_trades(), [trade])
        trade["fills"][0]["quantity"] = 0.04
        trade["gross_pnl_usd"] = 0.8
        trade["raw_r"] = 0.8
        manager.save_trade(trade)
        restarted = DatabaseManager(data_dir=self.temp.name)
        self.assertEqual(restarted.get_trades(), [trade])
        with closing(sqlite3.connect(manager.sqlite_file)) as conn, conn:
            self.assertEqual(conn.execute("SELECT raw_r FROM bot_trades").fetchone()[0], 0.8)

    def test_invalid_record_payload_falls_back_to_original_columns(self):
        manager = DatabaseManager(data_dir=self.temp.name)
        manager.save_trade(example_trade())
        with closing(sqlite3.connect(manager.sqlite_file)) as conn, conn:
            conn.execute("UPDATE bot_trades SET record_json = 'broken json'")
        loaded = manager.get_trades()[0]
        self.assertEqual(loaded["pnl_usd"], 0.74)
        self.assertEqual(loaded["diagnostic"], {"summary": "Recorded exit"})

    def test_snapshot_round_trip_commits_compatible_tables(self):
        manager = DatabaseManager(data_dir=self.temp.name)
        self.assertIsNone(manager.get_portfolio_snapshot())
        snapshot = example_snapshot()
        manager.save_portfolio_snapshot(snapshot)
        manager.save_portfolio_snapshot(snapshot)  # Retrying a persisted event changes no money.
        restarted = DatabaseManager(data_dir=self.temp.name)
        self.assertEqual(restarted.get_portfolio_snapshot(), snapshot)
        self.assertEqual(restarted.get_positions(), snapshot["open_positions"])
        self.assertEqual(restarted.get_trades(), snapshot["closed_trades"])
        self.assertEqual(restarted.get_state("bot_state"), snapshot["state"])

    def test_snapshot_failure_rolls_back_entire_portfolio(self):
        manager = DatabaseManager(data_dir=self.temp.name)
        original = example_snapshot()
        manager.save_portfolio_snapshot(original)
        newer = copy.deepcopy(original)
        newer["revision"] = 2
        newer["state"]["current_balance"] = 999.0
        newer["open_positions"] = {}
        newer["closed_trades"][0]["pnl_usd"] = 99.0
        original_save_state = manager._save_state

        def fail_final_write(cur, key, value):
            if key == "portfolio_snapshot":
                raise sqlite3.OperationalError("simulated storage failure")
            original_save_state(cur, key, value)

        with patch.object(manager, "_save_state", side_effect=fail_final_write):
            with self.assertRaises(sqlite3.OperationalError):
                manager.save_portfolio_snapshot(newer)
        self.assertEqual(manager.get_portfolio_snapshot(), original)
        self.assertEqual(manager.get_positions(), original["open_positions"])
        self.assertEqual(manager.get_trades(), original["closed_trades"])
        self.assertEqual(manager.get_state("bot_state"), original["state"])

    def test_clear_failure_propagates_and_preserves_portfolio(self):
        manager = DatabaseManager(data_dir=self.temp.name)
        original = example_snapshot()
        manager.save_portfolio_snapshot(original)
        with closing(sqlite3.connect(manager.sqlite_file)) as conn, conn:
            conn.execute("""CREATE TRIGGER reject_position_delete
                            BEFORE DELETE ON bot_positions
                            BEGIN SELECT RAISE(ABORT, 'simulated reset failure'); END""")
        with self.assertRaisesRegex(sqlite3.IntegrityError, "simulated reset failure"):
            manager.clear_all()
        self.assertEqual(manager.get_portfolio_snapshot(), original)
        self.assertEqual(manager.get_positions(), original["open_positions"])
        self.assertEqual(manager.get_trades(), original["closed_trades"])
        self.assertEqual(manager.get_state("bot_state"), original["state"])

    def test_snapshot_rejects_partial_or_nonfinite_data(self):
        for field in ("state", "open_positions", "closed_trades", "revision", "schema_version"):
            snapshot = example_snapshot()
            del snapshot[field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_portfolio_snapshot(snapshot)
        snapshot = example_snapshot()
        snapshot["state"]["current_balance"] = float("nan")
        with self.assertRaises(ValueError):
            validate_portfolio_snapshot(snapshot)

    def test_snapshot_requires_recorded_wallet_balance(self):
        snapshot = example_snapshot()
        snapshot["state"] = {}
        with self.assertRaisesRegex(ValueError, "current_balance"):
            validate_portfolio_snapshot(snapshot)
        for invalid in (None, "100.0", True, [], float("nan"), float("inf")):
            snapshot["state"] = {"current_balance": invalid}
            with self.subTest(balance=invalid), self.assertRaisesRegex(ValueError, "current_balance"):
                validate_portfolio_snapshot(snapshot)
        # A depleted wallet can be negative; never rewrite it or require unrelated
        # optional configuration fields from an earlier snapshot producer.
        snapshot["state"] = {"current_balance": -0.12}
        self.assertEqual(validate_portfolio_snapshot(snapshot)["state"]["current_balance"], -0.12)

    def test_incomplete_db_snapshot_is_not_reported_as_missing(self):
        manager = DatabaseManager(data_dir=self.temp.name)
        snapshot = example_snapshot()
        del snapshot["state"]["current_balance"]
        manager.save_state("portfolio_snapshot", snapshot)
        with self.assertRaisesRegex(ValueError, "current_balance"):
            manager.get_portfolio_snapshot()

    def test_atomic_json_failure_preserves_previous_snapshot(self):
        target = self.path / "portfolio_snapshot.json"
        first = example_snapshot()
        self.assertIsNone(load_portfolio_snapshot(target))
        atomic_write_json(target, first)
        before = target.read_bytes()
        with patch("persistence.os.replace", side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):
                atomic_write_json(target, example_snapshot(2))
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(load_portfolio_snapshot(target), first)
        self.assertEqual(list(self.path.glob("*.tmp")), [])
        target.write_text("{broken", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_portfolio_snapshot(target)

    def test_explicit_remote_uses_postgres_sql_and_never_sqlite_fallback(self):
        connection = MagicMock()
        cursor = connection.cursor.return_value
        cursor.fetchone.return_value = None
        fake_driver = types.SimpleNamespace(connect=MagicMock(return_value=connection))
        with patch.dict("sys.modules", {"psycopg2": fake_driver}):
            manager = DatabaseManager(db_url="postgres://example.invalid/test", data_dir=self.temp.name)
            self.assertTrue(manager.is_postgres)
            manager.save_portfolio_snapshot(example_snapshot())
            queries = [args[0] for args, _ in cursor.execute.call_args_list]
            self.assertIn("ALTER TABLE bot_trades ADD COLUMN IF NOT EXISTS record_json TEXT;", queries)
            insert = next(query for query in queries if query.startswith("INSERT INTO bot_trades"))
            self.assertEqual(insert.count("%s"), 31)
            self.assertIn("record_json = excluded.record_json", insert)
            self.assertIn("raw_r = excluded.raw_r", insert)
            fake_driver.connect.side_effect = ConnectionError("remote offline")
            with patch("db.sqlite3.connect") as local_connect:
                with self.assertRaises(ConnectionError):
                    manager.save_portfolio_snapshot(example_snapshot(2))
                local_connect.assert_not_called()
        self.assertFalse((self.path / "local_crypto_bot.db").exists())

    def test_schema_two_journal_uses_recorded_values_without_assumed_half(self):
        journal = create_trade_journal_md(example_trade())
        self.assertIn("0.03", journal)
        self.assertIn("0.29769033", journal)
        self.assertIn("0.00164967", journal)
        self.assertIn("not deducted again", journal)
        self.assertNotIn("50%", journal)
        self.assertNotIn("guaranteed", journal)
        minimal = create_trade_journal_md({"schema_version": 2})
        self.assertIn("No recorded fills", minimal)
        self.assertIn("N/A", minimal)
        self.assertNotIn("0.08", minimal)

    def test_legacy_journal_still_uses_legacy_renderer(self):
        trade = {"trade_id": 1, "symbol": "OLD", "tp1_hit": True, "target_rr": 3.0,
                 "raw_r": 2.25, "net_r": 2.17, "tp1_price": 103.0}
        journal = create_trade_journal_md(trade)
        self.assertIn("Dual-Stage Scale-Out", journal)
        self.assertIn("+0.75R", journal)

    def test_explicit_reset_archives_and_clears_canonical_snapshot(self):
        manager = DatabaseManager(data_dir=self.temp.name)
        snapshot = example_snapshot()
        manager.save_portfolio_snapshot(snapshot)
        target = self.path / "portfolio_snapshot.json"
        atomic_write_json(target, snapshot)
        snapshot_bytes = target.read_bytes()
        archive_and_reset_ledger(self.temp.name)
        self.assertFalse(target.exists())
        archived = list((self.path / "reports").glob("portfolio_snapshot_*.json"))
        self.assertEqual(len(archived), 1)
        self.assertEqual(archived[0].read_bytes(), snapshot_bytes)
        self.assertIsNone(manager.get_portfolio_snapshot())


if __name__ == "__main__":
    unittest.main()
