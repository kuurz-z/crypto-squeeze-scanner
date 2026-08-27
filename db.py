"""
Database Persistence Layer (Supabase PostgreSQL / SQLite / JSON Fallback)
Provides persistent cloud storage for live trades, active open positions,
bot state, strategy tournaments, and evolution logs.
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional

DATABASE_URL = os.environ.get("DATABASE_URL")

class DatabaseManager:
    def __init__(self, db_url: Optional[str] = None, data_dir: Optional[str] = None):
        self.db_url = db_url or os.environ.get("DATABASE_URL", DATABASE_URL)
        self.data_dir = data_dir
        self.is_postgres = bool(self.db_url and ("postgres://" in self.db_url or "postgresql://" in self.db_url))
        self.sqlite_file = os.path.join(data_dir, "local_crypto_bot.db") if data_dir else "local_crypto_bot.db"
        self._init_db()

    def _get_connection(self):
        if self.is_postgres:
            try:
                import psycopg2
                url = self.db_url
                if url.startswith("postgres://"):
                    url = url.replace("postgres://", "postgresql://", 1)
                return psycopg2.connect(url)
            except Exception as e:
                print(f"[Database] Notice: PostgreSQL connection fallback to SQLite: {e}")
                return sqlite3.connect(self.sqlite_file)
        else:
            return sqlite3.connect(self.sqlite_file)

    def _init_db(self):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_trades (
                    trade_id INTEGER PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    sector TEXT,
                    strategy TEXT,
                    timeframe TEXT,
                    direction TEXT,
                    entry_time BIGINT,
                    entry_time_str TEXT,
                    exit_time BIGINT,
                    exit_time_str TEXT,
                    entry_price REAL,
                    exit_price REAL,
                    sl_price REAL,
                    tp_price REAL,
                    target_rr REAL,
                    risk_amount_usd REAL,
                    position_qty REAL,
                    position_value_usd REAL,
                    outcome TEXT,
                    raw_r REAL,
                    net_r REAL,
                    pnl_usd REAL,
                    account_balance REAL,
                    mfe_r REAL,
                    mae_r REAL,
                    bars_held INTEGER,
                    friction_breakdown TEXT,
                    trade_efficiency TEXT,
                    diagnostic TEXT,
                    pre_trade_context TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_positions (
                    symbol TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bot_state_store (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            cur.close()
            conn.close()
            db_type = "Supabase PostgreSQL" if self.is_postgres else "SQLite"
            print(f"[Database] Initialized successfully ({db_type}).")
        except Exception as e:
            print(f"[Database] Warning: DB init error: {e}")

    def save_trade(self, t: Dict[str, Any]):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            diag_str = json.dumps(t.get("diagnostic", {})) if isinstance(t.get("diagnostic"), dict) else str(t.get("diagnostic", ""))
            ctx_str = json.dumps(t.get("pre_trade_context", {})) if isinstance(t.get("pre_trade_context"), dict) else str(t.get("pre_trade_context", ""))
            vals = (
                t.get("trade_id", 1), t.get("symbol", "UNKNOWN"), t.get("sector", "ALT"),
                t.get("strategy", "Squeeze_Momentum_Breakout"), t.get("timeframe", "15m"),
                t.get("direction", "LONG"), t.get("entry_time", 0), t.get("entry_time_str", ""),
                t.get("exit_time", 0), t.get("exit_time_str", ""),
                t.get("entry_price", 0.0), t.get("exit_price", 0.0),
                t.get("sl_price", 0.0), t.get("tp_price", 0.0), t.get("target_rr", 2.0),
                t.get("risk_amount_usd", 1.0), t.get("position_qty", 1.0),
                t.get("position_value_usd", 0.0), t.get("outcome", "WIN"),
                t.get("raw_r", 0.0), t.get("net_r", 0.0), t.get("pnl_usd", 0.0),
                t.get("account_balance", 100.0), t.get("mfe_r", 0.0), t.get("mae_r", 0.0),
                t.get("bars_held", 1), t.get("friction_breakdown", ""),
                t.get("trade_efficiency", ""), diag_str, ctx_str
            )
            if self.is_postgres:
                query = """
                    INSERT INTO bot_trades (
                        trade_id, symbol, sector, strategy, timeframe, direction,
                        entry_time, entry_time_str, exit_time, exit_time_str,
                        entry_price, exit_price, sl_price, tp_price, target_rr,
                        risk_amount_usd, position_qty, position_value_usd, outcome,
                        raw_r, net_r, pnl_usd, account_balance, mfe_r, mae_r,
                        bars_held, friction_breakdown, trade_efficiency, diagnostic, pre_trade_context
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (trade_id) DO UPDATE SET
                        exit_price = EXCLUDED.exit_price,
                        outcome = EXCLUDED.outcome,
                        net_r = EXCLUDED.net_r,
                        pnl_usd = EXCLUDED.pnl_usd,
                        account_balance = EXCLUDED.account_balance,
                        diagnostic = EXCLUDED.diagnostic;
                """
            else:
                query = """
                    INSERT OR REPLACE INTO bot_trades (
                        trade_id, symbol, sector, strategy, timeframe, direction,
                        entry_time, entry_time_str, exit_time, exit_time_str,
                        entry_price, exit_price, sl_price, tp_price, target_rr,
                        risk_amount_usd, position_qty, position_value_usd, outcome,
                        raw_r, net_r, pnl_usd, account_balance, mfe_r, mae_r,
                        bars_held, friction_breakdown, trade_efficiency, diagnostic, pre_trade_context
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    );
                """
            cur.execute(query, vals)
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Database] Error saving trade: {e}")

    def get_trades(self) -> List[Dict[str, Any]]:
        trades = []
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT trade_id, symbol, sector, strategy, timeframe, direction,
                       entry_time, entry_time_str, exit_time, exit_time_str,
                       entry_price, exit_price, sl_price, tp_price, target_rr,
                       risk_amount_usd, position_qty, position_value_usd, outcome,
                       raw_r, net_r, pnl_usd, account_balance, mfe_r, mae_r,
                       bars_held, friction_breakdown, trade_efficiency, diagnostic, pre_trade_context
                FROM bot_trades
                ORDER BY trade_id ASC;
            """)
            rows = cur.fetchall()
            for r in rows:
                diag = {}
                try:
                    diag = json.loads(r[28]) if r[28] else {}
                except Exception:
                    diag = {"summary": r[28]} if r[28] else {}
                ctx = {}
                try:
                    ctx = json.loads(r[29]) if r[29] else {}
                except Exception:
                    pass
                trades.append({
                    "trade_id": r[0], "symbol": r[1], "sector": r[2], "strategy": r[3],
                    "timeframe": r[4], "direction": r[5], "entry_time": r[6],
                    "entry_time_str": r[7], "exit_time": r[8], "exit_time_str": r[9],
                    "entry_price": r[10], "exit_price": r[11], "sl_price": r[12],
                    "tp_price": r[13], "target_rr": r[14], "risk_amount_usd": r[15],
                    "position_qty": r[16], "position_value_usd": r[17], "outcome": r[18],
                    "raw_r": r[19], "net_r": r[20], "pnl_usd": r[21], "account_balance": r[22],
                    "mfe_r": r[23], "mae_r": r[24], "bars_held": r[25],
                    "friction_breakdown": r[26], "trade_efficiency": r[27],
                    "diagnostic": diag, "pre_trade_context": ctx
                })
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Database] Error getting trades: {e}")
        return trades

    def save_positions(self, positions: Dict[str, Dict[str, Any]]):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM bot_positions;")
            for sym, pos in positions.items():
                pos_json = json.dumps(pos)
                if self.is_postgres:
                    cur.execute("INSERT INTO bot_positions (symbol, data) VALUES (%s, %s);", (sym, pos_json))
                else:
                    cur.execute("INSERT INTO bot_positions (symbol, data) VALUES (?, ?);", (sym, pos_json))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Database] Error saving positions: {e}")

    def get_positions(self) -> Dict[str, Dict[str, Any]]:
        positions = {}
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("SELECT symbol, data FROM bot_positions;")
            for row in cur.fetchall():
                try:
                    positions[row[0]] = json.loads(row[1])
                except Exception:
                    pass
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Database] Error loading positions: {e}")
        return positions

    def save_state(self, key: str, value: Any):
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            val_str = json.dumps(value)
            if self.is_postgres:
                cur.execute("""
                    INSERT INTO bot_state_store (key, value) VALUES (%s, %s)
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP;
                """, (key, val_str))
            else:
                cur.execute("INSERT OR REPLACE INTO bot_state_store (key, value) VALUES (?, ?);", (key, val_str))
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Database] Error saving state {key}: {e}")

    def get_state(self, key: str, default: Any = None) -> Any:
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            if self.is_postgres:
                cur.execute("SELECT value FROM bot_state_store WHERE key = %s;", (key,))
            else:
                cur.execute("SELECT value FROM bot_state_store WHERE key = ?;", (key,))
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                return json.loads(row[0])
        except Exception as e:
            print(f"[Database] Error loading state {key}: {e}")
        return default

    def clear_all(self):
        """Clear all stored trades, positions, and state."""
        try:
            conn = self._get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM bot_trades;")
            cur.execute("DELETE FROM bot_positions;")
            cur.execute("DELETE FROM bot_state_store;")
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[Database] Error clearing tables: {e}")

