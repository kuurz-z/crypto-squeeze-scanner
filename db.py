"""SQLite/PostgreSQL persistence with complete records and atomic snapshots."""

import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from persistence import validate_portfolio_snapshot


DATABASE_URL = os.environ.get("DATABASE_URL")
PORTFOLIO_SNAPSHOT_KEY = "portfolio_snapshot"

# Retain the original columns for existing dashboards and legacy databases.
TRADE_DEFAULTS = {
    "trade_id": 1, "symbol": "UNKNOWN", "sector": "ALT",
    "strategy": "Squeeze_Momentum_Breakout", "timeframe": "15m", "direction": "LONG",
    "entry_time": 0, "entry_time_str": "", "exit_time": 0, "exit_time_str": "",
    "entry_price": 0.0, "exit_price": 0.0, "sl_price": 0.0, "tp_price": 0.0,
    "target_rr": 2.0, "risk_amount_usd": 1.0, "position_qty": 1.0,
    "position_value_usd": 0.0, "outcome": "WIN", "raw_r": 0.0, "net_r": 0.0,
    "pnl_usd": 0.0, "account_balance": 100.0, "mfe_r": 0.0, "mae_r": 0.0,
    "bars_held": 1, "friction_breakdown": "", "trade_efficiency": "",
    "diagnostic": {}, "pre_trade_context": {},
}
TRADE_COLUMNS = tuple(TRADE_DEFAULTS)


class DatabaseManager:
    def __init__(self, db_url: Optional[str] = None, data_dir: Optional[str] = None):
        # Explicit local directories cannot inherit a production database URL.
        self.db_url = db_url if db_url is not None else (
            None if data_dir is not None else os.environ.get("DATABASE_URL", DATABASE_URL)
        )
        self.data_dir = data_dir
        self.is_postgres = bool(self.db_url and self.db_url.startswith(("postgres://", "postgresql://")))
        self.sqlite_file = os.path.join(data_dir, "local_crypto_bot.db") if data_dir else "local_crypto_bot.db"
        self._init_db()

    def _get_connection(self):
        if self.is_postgres:
            import psycopg2
            url = self.db_url.replace("postgres://", "postgresql://", 1)
            # Let failure reach the complete JSON fallback. Returning SQLite here
            # would retain the wrong SQL dialect and silently lose writes.
            return psycopg2.connect(url)
        return sqlite3.connect(self.sqlite_file)

    @contextmanager
    def _cursor(self):
        conn = self._get_connection()
        cur = None
        try:
            cur = conn.cursor()
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if cur is not None:
                cur.close()
            conn.close()

    @property
    def _placeholder(self):
        return "%s" if self.is_postgres else "?"

    def _init_db(self):
        try:
            with self._cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bot_trades (
                        trade_id INTEGER PRIMARY KEY, symbol TEXT NOT NULL,
                        sector TEXT, strategy TEXT, timeframe TEXT, direction TEXT,
                        entry_time BIGINT, entry_time_str TEXT, exit_time BIGINT, exit_time_str TEXT,
                        entry_price REAL, exit_price REAL, sl_price REAL, tp_price REAL,
                        target_rr REAL, risk_amount_usd REAL, position_qty REAL,
                        position_value_usd REAL, outcome TEXT, raw_r REAL, net_r REAL,
                        pnl_usd REAL, account_balance REAL, mfe_r REAL, mae_r REAL,
                        bars_held INTEGER, friction_breakdown TEXT, trade_efficiency TEXT,
                        diagnostic TEXT, pre_trade_context TEXT, record_json TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                if self.is_postgres:
                    cur.execute("ALTER TABLE bot_trades ADD COLUMN IF NOT EXISTS record_json TEXT;")
                else:
                    cur.execute("PRAGMA table_info(bot_trades);")
                    columns = {row[1] for row in cur.fetchall()}
                    if "record_json" not in columns:
                        cur.execute("ALTER TABLE bot_trades ADD COLUMN record_json TEXT;")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bot_positions (
                        symbol TEXT PRIMARY KEY, data TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS bot_state_store (
                        key TEXT PRIMARY KEY, value TEXT NOT NULL,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
        except Exception as exc:
            print(f"[Database] Warning: DB init error: {exc}")

    def _save_trade(self, cur, trade):
        columns = TRADE_COLUMNS + ("record_json",)
        values = []
        for key, default in TRADE_DEFAULTS.items():
            value = trade.get(key, default)
            if key in ("diagnostic", "pre_trade_context"):
                value = json.dumps(value, allow_nan=False) if isinstance(value, dict) else str(value or "")
            values.append(value)
        values.append(json.dumps(trade, allow_nan=False))
        query = (
            "INSERT INTO bot_trades (" + ", ".join(columns) + ") VALUES ("
            + ", ".join([self._placeholder] * len(columns))
            + ") ON CONFLICT (trade_id) DO UPDATE SET "
            + ", ".join(f"{column} = excluded.{column}" for column in columns if column != "trade_id")
        )
        cur.execute(query, tuple(values))

    def save_trade(self, trade: Dict[str, Any]):
        try:
            with self._cursor() as cur:
                self._save_trade(cur, trade)
        except Exception as exc:
            print(f"[Database] Error saving trade: {exc}")

    def get_trades(self) -> List[Dict[str, Any]]:
        trades = []
        try:
            with self._cursor() as cur:
                cur.execute("SELECT " + ", ".join(TRADE_COLUMNS) + ", record_json FROM bot_trades ORDER BY trade_id ASC;")
                for row in cur.fetchall():
                    if row[-1]:
                        try:
                            payload = json.loads(row[-1])
                            if isinstance(payload, dict):
                                trades.append(payload)
                                continue
                        except (ValueError, TypeError):
                            pass
                    trade = dict(zip(TRADE_COLUMNS, row[:-1]))
                    for key in ("diagnostic", "pre_trade_context"):
                        raw = trade[key]
                        try:
                            trade[key] = json.loads(raw) if raw else {}
                        except (ValueError, TypeError):
                            trade[key] = {"summary": raw} if key == "diagnostic" and raw else {}
                    trades.append(trade)
        except Exception as exc:
            print(f"[Database] Error getting trades: {exc}")
        return trades

    def _save_positions(self, cur, positions):
        cur.execute("DELETE FROM bot_positions;")
        placeholder = self._placeholder
        for symbol, position in positions.items():
            cur.execute(
                f"INSERT INTO bot_positions (symbol, data) VALUES ({placeholder}, {placeholder});",
                (symbol, json.dumps(position, allow_nan=False)),
            )

    def save_positions(self, positions: Dict[str, Dict[str, Any]]):
        try:
            with self._cursor() as cur:
                self._save_positions(cur, positions)
        except Exception as exc:
            print(f"[Database] Error saving positions: {exc}")

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        positions = {}
        try:
            with self._cursor() as cur:
                cur.execute("SELECT symbol, data FROM bot_positions;")
                for symbol, payload in cur.fetchall():
                    try:
                        positions[symbol] = json.loads(payload)
                    except (ValueError, TypeError):
                        pass
        except Exception as exc:
            print(f"[Database] Error loading positions: {exc}")
        return positions

    def _save_state(self, cur, key, value):
        placeholder = self._placeholder
        cur.execute(
            f"INSERT INTO bot_state_store (key, value) VALUES ({placeholder}, {placeholder}) "
            "ON CONFLICT (key) DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP;",
            (key, json.dumps(value, allow_nan=False)),
        )

    def save_state(self, key: str, value: Any):
        try:
            with self._cursor() as cur:
                self._save_state(cur, key, value)
        except Exception as exc:
            print(f"[Database] Error saving state {key}: {exc}")

    def get_state(self, key: str, default: Any = None) -> Any:
        try:
            with self._cursor() as cur:
                cur.execute(f"SELECT value FROM bot_state_store WHERE key = {self._placeholder};", (key,))
                row = cur.fetchone()
                if row is not None:
                    return json.loads(row[0])
        except Exception as exc:
            print(f"[Database] Error loading state {key}: {exc}")
        return default

    def save_portfolio_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Commit a complete portfolio and compatibility tables in one transaction.

        Errors propagate so callers can use a complete JSON fallback deliberately.
        Historical trade rows outside this snapshot are never deleted.
        """
        validate_portfolio_snapshot(snapshot)
        with self._cursor() as cur:
            for trade in snapshot["closed_trades"]:
                self._save_trade(cur, trade)
            self._save_positions(cur, snapshot["open_positions"])
            self._save_state(cur, "bot_state", snapshot["state"])
            self._save_state(cur, PORTFOLIO_SNAPSHOT_KEY, snapshot)

    def get_portfolio_snapshot(self) -> Optional[Dict[str, Any]]:
        """Return a validated whole snapshot; None means no snapshot exists."""
        with self._cursor() as cur:
            cur.execute(
                f"SELECT value FROM bot_state_store WHERE key = {self._placeholder};",
                (PORTFOLIO_SNAPSHOT_KEY,),
            )
            row = cur.fetchone()
            if row is None:
                return None
            return validate_portfolio_snapshot(json.loads(row[0]))

    def clear_all(self):
        """Explicit reset; failures propagate so callers cannot claim success."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM bot_trades;")
            cur.execute("DELETE FROM bot_positions;")
            cur.execute("DELETE FROM bot_state_store;")
