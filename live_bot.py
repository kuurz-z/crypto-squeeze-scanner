import asyncio
import os
import json
import time
import copy
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
import aiohttp
import pandas as pd
import numpy as np

# Philippine Standard Time (PHT, UTC+8 / Asia/Manila)
PHT = timezone(timedelta(hours=8))

def ph_now() -> datetime:
    """Return current timestamp in Philippine Standard Time (PHT, UTC+8)."""
    return datetime.now(timezone.utc).astimezone(PHT).replace(tzinfo=None)

def ph_fromtimestamp(ts: float) -> datetime:
    """Convert Unix epoch timestamp (seconds) to Philippine Standard Time (PHT, UTC+8)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(PHT).replace(tzinfo=None)

from data_loader import fetch_top_crypto_pairs, fetch_symbol_klines, fetch_symbol_mtf_klines, split_train_test, rate_limit_manager, completed_candles, interval_seconds, ANCHOR_TIMEFRAMES
from strategies import (
    compute_crypto_indicators, 
    evaluate_tf_trend,
    evaluate_mtf_alignment,
    format_price_precision,
    SqueezeMomentumBreakout, 
    LiquiditySweepReversal, 
    TrendPullbackConfluence,
    AVAILABLE_STRATEGIES
)
from sim_engine import diagnose_trade_outcome, compile_simulation_metrics, simulate_strategy_on_dataframe
from strategy_memory import evaluate_reproducibility, save_strategy_to_catalog, load_saved_strategies
from db import DatabaseManager
from trade_journal import archive_and_reset_ledger, create_trade_journal_md
from persistence import atomic_write_json, load_portfolio_snapshot
from execution import create_position, process_price, process_bar, close_position, summarize_position, EXIT_TIMEFRAME_PROFILES


LIVE_TRADES_FILE = "live_trades.json"
LIVE_POSITIONS_FILE = "live_positions.json"
BOT_STATE_FILE = "bot_state.json"
REPORTS_DIR = "reports"
HISTORICAL_ARCHIVE_FILE = os.path.join(REPORTS_DIR, "historical_archive.json")
HALL_OF_FAME_FILE = os.path.join(REPORTS_DIR, "monthly_champions_hall_of_fame.json")

CRYPTO_SECTOR_MAP = {
    "AI_COMPUTE": ["FETUSDT", "RENDERUSDT", "TAOUSDT", "NEARUSDT", "ICPUSDT", "AGIXUSDT", "WLDUSDT", "ARKMUSDT", "IOUSDT", "ATHUSDT"],
    "MEMES": ["DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "BONKUSDT", "FLOKIUSDT", "BOMEUSDT", "MEMEUSDT", "POPCATUSDT", "NEIROUSDT", "TURBOUSDT"],
    "LAYER_1": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "AVAXUSDT", "DOTUSDT", "ATOMUSDT", "SUIUSDT", "SEIUSDT", "APTUSDT", "KASUSDT", "TONUSDT", "ALGOUSDT", "FTMUSDT", "HBARUSDT", "KAVAUSDT"],
    "LAYER_2": ["MATICUSDT", "POLUSDT", "ARBUSDT", "OPUSDT", "STXUSDT", "IMXUSDT", "MANTAUSDT", "STRKUSDT", "ZKUSDT", "METISUSDT"],
    "DEFI": ["UNIUSDT", "AAVEUSDT", "MKRUSDT", "LINKUSDT", "CRVUSDT", "PENDLEUSDT", "ONDOUSDT", "JUPUSDT", "PYTHUSDT", "RUNEUSDT", "LDOUSDT", "ENAUSDT", "DYDXUSDT", "SNXUSDT", "INJUSDT", "CAKEUSDT", "COMPUSDT"],
    "INFRA_ORACLE": ["FILUSDT", "GRTUSDT", "THETAUSDT", "TIAUSDT", "ARUSDT", "JASMYUSDT", "WUSDT"],
    "GAMING_METAVERSE": ["GALAUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT", "BEAMUSDT", "NOTUSDT", "RONINUSDT", "ENJUSDT"]
}

def get_crypto_sector(symbol: str) -> str:
    """Return the categorized sector for a given crypto symbol."""
    for sector, coins in CRYPTO_SECTOR_MAP.items():
        if symbol in coins:
            return sector
    return "GENERAL_ALT"

ALLOWED_ENTRY_TIMEFRAMES = ["5m", "15m", "30m", "triple", "dual"]

TIMEFRAME_PROFILES: Dict[str, Dict[str, Any]] = {
    "5m": {
        "name": "5m Scalp (30m MTF Anchor)",
        "anchor_tf": "30m",
        "expected_hold_str": "25m - 2.5h",
        "max_holding_bars": 64,       # ~5.3 hours
        "stagnation_bars": 18,        # ~1.5 hours smart stagnation
        "cooldown_minutes": 20,       # 4 bars
        "scan_interval_sec": 15,
    },
    "15m": {
        "name": "15m Intraday (1h MTF Anchor)",
        "anchor_tf": "1h",
        "expected_hold_str": "1.5h - 8h",
        "max_holding_bars": 64,       # ~16 hours
        "stagnation_bars": 16,        # ~4 hours smart stagnation
        "cooldown_minutes": 45,       # 3 bars
        "scan_interval_sec": 20,
    },
    "30m": {
        "name": "30m Swing (4h MTF Anchor)",
        "anchor_tf": "4h",
        "expected_hold_str": "3h - 16h",
        "max_holding_bars": 64,       # ~32 hours
        "stagnation_bars": 16,        # ~8 hours smart stagnation
        "cooldown_minutes": 90,       # 3 bars
        "scan_interval_sec": 30,
    },
    "dual": {
        "name": "Dual Multi-Timeframe (15m/1h + 30m/4h)",
        "anchor_tf": "1h/4h",
        "expected_hold_str": "Dynamic (1.5h - 16h)",
        "max_holding_bars": 64,
        "stagnation_bars": 16,
        "cooldown_minutes": 45,
        "scan_interval_sec": 20,
    },
    "triple": {
        "name": "Triple Multi-Timeframe (5m/30m + 15m/1h + 30m/4h)",
        "anchor_tf": "30m/1h/4h",
        "expected_hold_str": "Dynamic (25m - 32h)",
        "max_holding_bars": 64,
        "stagnation_bars": 16,
        "cooldown_minutes": 30,
        "scan_interval_sec": 15,
    }
}

for _timeframe, _exit_profile in EXIT_TIMEFRAME_PROFILES.items():
    TIMEFRAME_PROFILES[_timeframe].update(_exit_profile)


class LiveCryptoBot:
    """
    Continuous automated paper-trading bot with fixed $1.00 USD risk per trade,
    dynamic >= 1:2.0 RR unlimited profit runners, real-time trade diagnosis, BTC Macro Gatekeeper, Sector Correlation Limits,
    Persistent forward cohorts, fill accounting, and report-only research.
    
    RULE: Trade entries are permitted across 5m (anchored to 30m), 15m (anchored to 1h), and 30m (anchored to 4h).
    """
    def __init__(
        self,
        initial_capital: float = 100.0,
        fixed_risk_usd: float = 1.0,
        timeframe: str = "15m",
        max_open_positions: int = 5,
        target_rr: float = 2.0,
        scan_interval_sec: Optional[int] = None,
        optimize_every_n_trades: int = 5,
        max_positions_per_sector: int = 2,
        active_strategy_name: str = "Trend_Pullback_Confluence",
        data_dir: Optional[str] = None,
        fee_pct: float = 0.05,
        slippage_pct: float = 0.02
    ):
        self.data_dir = data_dir
        self.trades_file = os.path.join(data_dir, "live_trades.json") if data_dir else LIVE_TRADES_FILE
        self.positions_file = os.path.join(data_dir, "live_positions.json") if data_dir else LIVE_POSITIONS_FILE
        self.state_file = os.path.join(data_dir, "bot_state.json") if data_dir else BOT_STATE_FILE
        self.reports_dir = os.path.join(data_dir, "reports") if data_dir else REPORTS_DIR
        self.archive_file = os.path.join(self.reports_dir, "historical_archive.json")
        self.hall_of_fame_file = os.path.join(self.reports_dir, "monthly_champions_hall_of_fame.json")
        self.snapshot_file = os.path.join(data_dir or ".", "portfolio_snapshot.json")
        self.snapshot_revision = 0
        self.forward_run_id = None
        self.forward_run_config = None
        self.fee_pct = float(fee_pct)
        self.slippage_pct = float(slippage_pct)
        if not (np.isfinite(self.fee_pct) and np.isfinite(self.slippage_pct)) or min(self.fee_pct, self.slippage_pct) < 0:
            raise ValueError("Fee and slippage percentages must be finite and nonnegative")
        self.optimizer_mode = "report_only"
        self.rejected_entries = {}
        self._evaluation_lock = asyncio.Lock()

        self.db = DatabaseManager(db_url=os.environ.get("DATABASE_URL") if not data_dir else None, data_dir=data_dir)

        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.fixed_risk_usd = fixed_risk_usd
        if timeframe not in ALLOWED_ENTRY_TIMEFRAMES:
            timeframe = "15m"
        self.timeframe = timeframe
        self.timeframe_profile = TIMEFRAME_PROFILES.get(timeframe, TIMEFRAME_PROFILES["15m"])
        self.max_open_positions = max_open_positions
        self.target_rr = max(2.0, target_rr)
        self.scan_interval_sec = scan_interval_sec if scan_interval_sec is not None else self.timeframe_profile.get("scan_interval_sec", 20)
        self.optimize_every_n_trades = optimize_every_n_trades
        self.max_positions_per_sector = max_positions_per_sector
        
        self.is_running = False
        self.auto_trading_enabled = True
        self.is_depleted = False
        self.depletion_report_file: Optional[str] = None
        self.task: Optional[asyncio.Task] = None
        
        self.symbols: List[str] = []
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.closed_trades: List[Dict[str, Any]] = []
        self.latest_signals: List[Dict[str, Any]] = []
        self.optimization_logs: List[Dict[str, Any]] = []
        self.macro_audits: List[Dict[str, Any]] = []
        self.hall_of_fame: List[Dict[str, Any]] = []
        self.all_time_grand_champion: Optional[Dict[str, Any]] = None
        
        # Anti-Churn Loss Cooldown & Same-Candle Tracker
        self.symbol_loss_cooldowns: Dict[str, datetime] = {}
        self.symbol_consecutive_losses: Dict[str, int] = {}
        self.symbol_last_entry_candle: Dict[str, int] = {}
        self.cooldown_minutes: int = self.timeframe_profile.get("cooldown_minutes", 45)
        
        self.champion_stats: Dict[str, Any] = {
            "name": "Trend_Pullback_Confluence",
            "timeframe": self.timeframe,
            "win_rate": None,
            "expectancy_r": None,
            "score": None,
            "validation_status": "NOT_VALIDATED",
            "upgrades_count": 0,
            "crowned_at": ph_now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        self.mtf_data: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.btc_macro_status: Dict[str, Any] = {
            "regime": "UNKNOWN",
            "trend": "Awaiting completed BTC candles",
            "rsi": None,
            "flash_drop": False,
            "gate_status": "ALLOW_ALL",
            "btc_price": 0.0,
            "alignment_1h": "UNKNOWN",
            "alignment_4h": "UNKNOWN"
        }
        
        self.circuit_breaker_until: Optional[datetime] = None
        self.active_strategy_name = active_strategy_name
        self.active_params = {
            "rvol_min": 1.45,
            "atr_sl_mult": 2.20,
            "target_rr": self.target_rr,
            "adx_min": 22.0,
            "rsi_min_long": 38.0,
            "rsi_max_long": 58.0,
            "rsi_min_short": 42.0,
            "rsi_max_short": 62.0,
            "min_risk_dist_pct": 0.012
        }
        
        self.started_at = ph_now()
        self.last_scan_time: Optional[datetime] = None
        self.last_optimization_time: Optional[datetime] = None
        self.last_daily_snapshot_time: Optional[datetime] = None
        self.last_weekly_optimization_time: Optional[datetime] = None
        self.last_monthly_optimization_time: Optional[datetime] = None
        
        self.load_state()
        if not self.forward_run_id:
            self._new_forward_run()
        self.save_state()

    def reset_account(self, initial_capital: float = 100.0, fixed_risk_usd: float = 1.0, target_rr: float = 2.0):
        """Reset paper wallet balance to specified USD capital and clear depletion flags without wiping trade history."""
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.fixed_risk_usd = fixed_risk_usd
        self.target_rr = target_rr
        self.active_params["target_rr"] = target_rr
        self.is_depleted = False
        self.depletion_report_file = None
        self.open_positions = {}
        # Preserve self.closed_trades and optimization_logs intact
        self.symbol_loss_cooldowns = {}
        self.symbol_consecutive_losses = {}
        self.symbol_last_entry_candle = {}
        self.circuit_breaker_until = None
        self._new_forward_run()
        self.save_state()
        print(f"[LiveBot] Account balance reset to ${initial_capital:.2f} USD starting capital (Trade history preserved: {len(self.closed_trades)} trades).")

    def archive_and_reset_ledger(self) -> str:
        """Safely archive historical trade ledger and reset bot state to clean benchmark."""
        data_dir = self.data_dir or "."
        res = archive_and_reset_ledger(data_dir=data_dir)
        self.db.clear_all()
        self.load_state()
        self.snapshot_revision = 0
        self._new_forward_run()
        self.save_state()
        print(f"[LiveBot] Ledger archived to '{res}' and bot state reset to clean benchmark.")
        return res

    def set_timeframe(self, timeframe: str) -> bool:

        """Update active timeframe. Supported timeframes: 5m, 15m, 30m, dual (15m+30m), triple (5m+15m+30m)."""
        tf_clean = timeframe.lower()
        if tf_clean not in ALLOWED_ENTRY_TIMEFRAMES:
            print(f"[LiveBot] Timeframe '{timeframe}' rejected: Must be one of {ALLOWED_ENTRY_TIMEFRAMES}")
            return False
        self.timeframe = tf_clean
        self.timeframe_profile = TIMEFRAME_PROFILES[tf_clean]
        self.cooldown_minutes = self.timeframe_profile["cooldown_minutes"]
        self.scan_interval_sec = self.timeframe_profile["scan_interval_sec"]
        self.champion_stats["timeframe"] = tf_clean
        self._new_forward_run()
        self.save_state()
        print(f"[LiveBot] Timeframe updated to {tf_clean} ({self.timeframe_profile['name']}). Cooldown: {self.cooldown_minutes}m.")
        return True

    async def restart_with_capital(self, capital: float, fixed_risk_usd: float = 1.0):
        """Re-fund the bot with custom capital amount and immediately resume live scanning."""
        await self.stop()
        self.reset_account(initial_capital=capital, fixed_risk_usd=fixed_risk_usd)
        await self.start()
        print(f"[LiveBot] Bot re-funded with ${capital:.2f} USD and resumed scanning.")

    def _load_legacy_state(self):
        """Load persisted trades, balances, open positions, and audit archives from Database and disk."""
        # 1. Load Closed Trades (Database + Multi-File Redundancy)
        loaded_trades = []
        try:
            db_trades = self.db.get_trades()
            if db_trades:
                loaded_trades = db_trades
        except Exception:
            pass

        if not loaded_trades and os.path.exists(self.trades_file):
            try:
                with open(self.trades_file, "r", encoding="utf-8") as f:
                    loaded_trades = json.load(f)
            except Exception:
                loaded_trades = []

        # Sort trades by trade_id ascending
        loaded_trades.sort(key=lambda x: x.get("trade_id", 0))
        self.closed_trades = loaded_trades

        # 2. Load Active Open Positions (Database + File Fallback)
        try:
            db_pos = self.db.get_positions()
            if db_pos:
                self.open_positions = db_pos
            elif os.path.exists(self.positions_file):
                with open(self.positions_file, "r", encoding="utf-8") as f:
                    self.open_positions = json.load(f)
            else:
                self.open_positions = {}
        except Exception:
            self.open_positions = {}

        # Sanitize open positions to ensure valid timeframe
        for sym, pos in list(self.open_positions.items()):
            if pos.get("timeframe") not in ALLOWED_ENTRY_TIMEFRAMES:
                pos["timeframe"] = self.timeframe

        # 3. Load Engine State & Wallets (File + Database Fallback)
        state = None
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                state = None

        if not state:
            try:
                state = self.db.get_state("bot_state")
            except Exception:
                pass

        if state:
            try:
                self.initial_capital = state.get("initial_capital", self.initial_capital)
                self.current_balance = state.get("current_balance", self.current_balance)
                self.fixed_risk_usd = state.get("fixed_risk_usd", self.fixed_risk_usd)
                self.is_depleted = state.get("is_depleted", False)
                self.depletion_report_file = state.get("depletion_report_file", None)
                if state.get("timeframe") and state.get("timeframe") in ALLOWED_ENTRY_TIMEFRAMES:
                    self.timeframe = state["timeframe"]
                    self.timeframe_profile = TIMEFRAME_PROFILES[self.timeframe]
                    self.cooldown_minutes = self.timeframe_profile["cooldown_minutes"]
                    self.scan_interval_sec = self.timeframe_profile["scan_interval_sec"]
                self.active_strategy_name = state.get("active_strategy_name", state.get("active_strategy", self.active_strategy_name))
                self.active_params = state.get("active_params", self.active_params)
                self.auto_trading_enabled = state.get("auto_trading_enabled", True)
                self.target_rr = state.get("target_rr", self.active_params.get("target_rr", self.target_rr))

                self.optimization_logs = state.get("optimization_logs", [])
                self.macro_audits = state.get("macro_audits", [])
                self.champion_stats = state.get("champion_stats", self.champion_stats)
                if self.champion_stats.get("timeframe") not in ALLOWED_ENTRY_TIMEFRAMES:
                    self.champion_stats["timeframe"] = "triple"
                self.all_time_grand_champion = state.get("all_time_grand_champion", None)
                if self.all_time_grand_champion and self.all_time_grand_champion.get("timeframe") not in ALLOWED_ENTRY_TIMEFRAMES:
                    self.all_time_grand_champion["timeframe"] = "triple"
                if state.get("last_daily_snapshot"):
                    self.last_daily_snapshot_time = datetime.strptime(state["last_daily_snapshot"], "%Y-%m-%d %H:%M:%S")
                if state.get("last_weekly_opt"):
                    self.last_weekly_optimization_time = datetime.strptime(state["last_weekly_opt"], "%Y-%m-%d %H:%M:%S")
                if state.get("last_monthly_opt"):
                    self.last_monthly_optimization_time = datetime.strptime(state["last_monthly_opt"], "%Y-%m-%d %H:%M:%S")
                
                # Load persistent symbol loss cooldowns and loss counts
                if state.get("symbol_loss_cooldowns"):
                    now = ph_now()
                    for sym, dt_str in state["symbol_loss_cooldowns"].items():
                        try:
                            exp_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                            if exp_dt > now:
                                self.symbol_loss_cooldowns[sym] = exp_dt
                        except Exception:
                            pass
                if state.get("symbol_consecutive_losses"):
                    self.symbol_consecutive_losses = state["symbol_consecutive_losses"]

                # Load circuit breaker status
                if state.get("circuit_breaker_until"):
                    try:
                        cb_dt = datetime.strptime(state["circuit_breaker_until"], "%Y-%m-%d %H:%M:%S")
                        if cb_dt > ph_now():
                            self.circuit_breaker_until = cb_dt
                    except Exception:
                        pass
            except Exception:
                pass

        # Ensure bot timeframe is valid
        if self.timeframe not in ALLOWED_ENTRY_TIMEFRAMES:
            self.timeframe = "15m"
            self.timeframe_profile = TIMEFRAME_PROFILES["15m"]

        # 4. Load Hall of Fame Registry
        if os.path.exists(self.hall_of_fame_file):
            try:
                with open(self.hall_of_fame_file, "r", encoding="utf-8") as f:
                    self.hall_of_fame = json.load(f)
            except Exception:
                self.hall_of_fame = []

    def _new_forward_run(self):
        self.forward_run_id = uuid.uuid4().hex
        self.forward_run_config = {
            "strategy": self.active_strategy_name, "timeframe": self.timeframe,
            "params": copy.deepcopy(self.active_params), "risk_amount_usd": self.fixed_risk_usd,
            "max_open_positions": self.max_open_positions,
            "max_positions_per_sector": self.max_positions_per_sector,
            "fee_pct": self.fee_pct, "slippage_pct": self.slippage_pct,
            "engine_version": "paper_v2", "started_at": int(time.time()),
        }
        self.rejected_entries = {}

    def _state_payload(self):
        fields = ("initial_capital", "current_balance", "fixed_risk_usd", "timeframe",
                  "auto_trading_enabled", "is_depleted", "depletion_report_file",
                  "active_strategy_name", "active_params", "target_rr", "champion_stats",
                  "all_time_grand_champion", "symbol_consecutive_losses", "symbol_last_entry_candle",
                  "forward_run_id", "forward_run_config", "fee_pct", "slippage_pct",
                  "rejected_entries", "max_open_positions", "max_positions_per_sector")
        state = {key: copy.deepcopy(getattr(self, key)) for key in fields}
        state.update({
            "optimizer_mode": "report_only",
            "optimization_logs": self.optimization_logs[-20:], "macro_audits": self.macro_audits[-10:],
            "symbol_loss_cooldowns": {key: value.isoformat() for key, value in self.symbol_loss_cooldowns.items()},
            "circuit_breaker_until": self.circuit_breaker_until.isoformat() if self.circuit_breaker_until else None,
            "last_daily_snapshot": self.last_daily_snapshot_time.isoformat() if self.last_daily_snapshot_time else None,
            "last_weekly_opt": self.last_weekly_optimization_time.isoformat() if self.last_weekly_optimization_time else None,
            "last_monthly_opt": self.last_monthly_optimization_time.isoformat() if self.last_monthly_optimization_time else None,
            "updated_at": ph_now().isoformat(),
        })
        return state

    def load_state(self):
        candidates, errors = [], []
        for load in (self.db.get_portfolio_snapshot, lambda: load_portfolio_snapshot(self.snapshot_file)):
            try:
                snapshot = load()
                if snapshot is not None:
                    candidates.append(snapshot)
            except Exception as exc:
                errors.append(str(exc))
        if candidates:
            snapshot = max(candidates, key=lambda value: value["revision"])
            self.snapshot_revision = snapshot["revision"]
            self.open_positions = copy.deepcopy(snapshot["open_positions"])
            self.closed_trades = copy.deepcopy(snapshot["closed_trades"])
            state = snapshot["state"]
            for key in ("initial_capital", "current_balance", "fixed_risk_usd", "timeframe",
                        "auto_trading_enabled", "is_depleted", "depletion_report_file",
                        "active_strategy_name", "active_params", "target_rr", "champion_stats",
                        "all_time_grand_champion", "symbol_consecutive_losses", "symbol_last_entry_candle",
                        "forward_run_id", "forward_run_config", "fee_pct", "slippage_pct",
                        "rejected_entries", "max_open_positions", "max_positions_per_sector",
                        "optimization_logs", "macro_audits"):
                if key in state:
                    setattr(self, key, copy.deepcopy(state[key]))
            self.symbol_loss_cooldowns = {key: datetime.fromisoformat(value) for key, value in state.get("symbol_loss_cooldowns", {}).items()}
            for key, attr in (("circuit_breaker_until", "circuit_breaker_until"),
                              ("last_daily_snapshot", "last_daily_snapshot_time"),
                              ("last_weekly_opt", "last_weekly_optimization_time"),
                              ("last_monthly_opt", "last_monthly_optimization_time")):
                setattr(self, attr, datetime.fromisoformat(state[key]) if state.get(key) else None)
            self.timeframe_profile = TIMEFRAME_PROFILES.get(self.timeframe, TIMEFRAME_PROFILES["15m"])
            self.cooldown_minutes = self.timeframe_profile["cooldown_minutes"]
            if os.path.exists(self.hall_of_fame_file):
                with open(self.hall_of_fame_file, encoding="utf-8") as stream:
                    self.hall_of_fame = json.load(stream)
        else:
            if errors:
                raise RuntimeError("No valid portfolio snapshot: " + "; ".join(errors))
            self._load_legacy_state()
            for position in self.open_positions.values():
                position.setdefault("accounting_mode", "legacy")
        # Old generated statistics never qualify as measured forward-test results.
        if self.champion_stats.get("validation_status") != "MEASURED":
            self.champion_stats = {"name": self.active_strategy_name, "timeframe": self.timeframe,
                                   "validation_status": "NOT_VALIDATED", "win_rate": None,
                                   "expectancy_r": None, "score": None, "upgrades_count": 0}
        if self.all_time_grand_champion and not self.all_time_grand_champion.get("evaluation_id"):
            self.all_time_grand_champion = dict(self.all_time_grand_champion, validation_status="LEGACY_UNVERIFIED")
        self.optimizer_mode = "report_only"

    def save_state(self):
        state = self._state_payload()
        snapshot = {"schema_version": 2, "revision": self.snapshot_revision + 1,
                    "state": state, "open_positions": copy.deepcopy(self.open_positions),
                    "closed_trades": copy.deepcopy(self.closed_trades)}
        persisted, errors = False, []
        try:
            self.db.save_portfolio_snapshot(snapshot)
            persisted = True
        except Exception as exc:
            errors.append(str(exc))
        try:
            atomic_write_json(self.snapshot_file, snapshot)
            persisted = True
        except Exception as exc:
            errors.append(str(exc))
        if not persisted:
            self.auto_trading_enabled = False
            raise RuntimeError("Portfolio could not be persisted: " + "; ".join(errors))
        self.snapshot_revision = snapshot["revision"]
        # Compatibility exports are not recovery sources once a snapshot exists.
        for path, value in ((self.trades_file, self.closed_trades), (self.positions_file, self.open_positions), (self.state_file, state)):
            try:
                atomic_write_json(path, value)
            except OSError as exc:
                print(f"[LiveBot] Compatibility export failed: {exc}")

    def toggle_auto_trading(self) -> bool:
        """Toggle auto-trading execution between active auto-trading and signals-only mode."""
        self.auto_trading_enabled = not self.auto_trading_enabled
        self.save_state()
        mode = "AUTO-TRADING ACTIVE (Executing live trades)" if self.auto_trading_enabled else "SIGNALS-ONLY MODE (Zero automated trades)"
        print(f"[LiveBot] Execution Gateway: {mode}")
        return self.auto_trading_enabled

    async def start(self):
        """Start the continuous background live trading worker."""
        if self.is_running or self.is_depleted:
            if self.is_depleted:
                print("[LiveBot] Cannot start: Capital is depleted. Please reset account first.")
            return
        self.is_running = True
        self.symbols = await fetch_top_crypto_pairs(limit=100)
        print(f"[LiveBot] Started continuous bot on {len(self.symbols)} pairs (${self.current_balance:.2f} USD Capital, $1.00/trade, 1:{self.target_rr} RR).")
        self.task = asyncio.create_task(self._main_loop())

    async def stop(self):
        """Pause the live trading worker and flush state to disk."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        self.save_state()
        print("[LiveBot] Bot worker stopped and state flushed to disk.")

    async def _main_loop(self):
        """Continuous execution loop."""
        while self.is_running and not self.is_depleted:
            try:
                self.last_scan_time = ph_now()
                await self._process_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[LiveBot] Exception in live cycle: {e}")
            await asyncio.sleep(self.scan_interval_sec)

    async def _process_cycle(self):
        """Execute one complete live scanning, position monitoring, and execution cycle."""
        if self.current_balance < self.fixed_risk_usd and len(self.open_positions) == 0:
            await self._handle_capital_depleted()
            return

        # Determine which candle intervals need fetching for scanning and MTF anchors
        if self.timeframe == "triple":
            scan_tfs = ["5m", "15m", "30m"]
            mtf_intervals = ["30m", "1h", "4h"]
        elif self.timeframe == "dual":
            scan_tfs = ["15m", "30m"]
            mtf_intervals = ["30m", "1h", "4h"]
        elif self.timeframe == "5m":
            scan_tfs = ["5m"]
            mtf_intervals = ["30m", "1h", "4h"]
        elif self.timeframe == "30m":
            scan_tfs = ["30m"]
            mtf_intervals = ["30m", "1h", "4h"]
        else: # 15m default
            scan_tfs = ["15m"]
            mtf_intervals = ["30m", "1h", "4h"]

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=30)) as session:
            # 1. Fetch latest candles across all scan timeframes and MTF anchors with set-based deduplication
            mtf_syms = sorted(set(self.symbols) | set(self.open_positions) | {"BTCUSDT"})
            
            # Build unique set of (sym, tf) requests to eliminate cross-timeframe duplicate calls
            unique_requests = set()
            for tf in scan_tfs:
                for sym in self.symbols:
                    unique_requests.add((sym, tf))
            for sym in mtf_syms:
                for tf in scan_tfs:
                    unique_requests.add((sym, ANCHOR_TIMEFRAMES[tf]))
            for sym, position in self.open_positions.items():
                unique_requests.add((sym, position.get("timeframe", "15m")))
            for tf in ("15m", "30m", "1h", "4h"):
                unique_requests.add(("BTCUSDT", tf))

            req_list = list(unique_requests)
            fetch_tasks = []
            fetch_now = time.time()
            for sym, tf in req_list:
                options = self._position_history_request(sym, tf, fetch_now)
                fetch_tasks.append(fetch_symbol_klines(session, sym, interval=tf, **options))
            results = await asyncio.gather(*fetch_tasks, return_exceptions=True)

            # Map raw klines and pre-compute indicators only once per unique (sym, tf)
            computed_cache: Dict[tuple, pd.DataFrame] = {}
            for (sym, tf), res in zip(req_list, results):
                if isinstance(res, pd.DataFrame) and len(res) >= 30:
                    computed_cache[(sym, tf)] = compute_crypto_indicators(res)

            # Distribute pre-computed indicator DataFrames to data_maps and self.mtf_data
            data_maps: Dict[str, Dict[str, pd.DataFrame]] = {tf: {} for tf in set(scan_tfs) | {p.get("timeframe", "15m") for p in self.open_positions.values()}}
            for tf in data_maps:
                for sym in mtf_syms:
                    df = computed_cache.get((sym, tf))
                    if df is not None and len(df) >= 50:
                        data_maps[tf][sym] = df

            for sym in mtf_syms:
                self.mtf_data[sym] = {}
                for mtf_tf in mtf_intervals:
                    df = computed_cache.get((sym, mtf_tf))
                    if df is not None and len(df) >= 30:
                        self.mtf_data[sym][mtf_tf] = df

            # 2. Update Bitcoin Macro Trend Gatekeeper status with Dual/Triple Alignment
            btc_df = data_maps.get("15m", {}).get("BTCUSDT")
            if btc_df is None:
                btc_df = data_maps.get("30m", {}).get("BTCUSDT")
            if btc_df is None:
                btc_df = data_maps.get("5m", {}).get("BTCUSDT")

            btc_30m = self.mtf_data.get("BTCUSDT", {}).get("30m")
            if btc_30m is None:
                btc_30m = data_maps.get("30m", {}).get("BTCUSDT")
            btc_1h = self.mtf_data.get("BTCUSDT", {}).get("1h")
            btc_4h = self.mtf_data.get("BTCUSDT", {}).get("4h")
            now_ts = time.time()
            btc_df = computed_cache.get(("BTCUSDT", "15m"))
            if btc_df is not None:
                btc_df = completed_candles(btc_df, "15m", now_ts)
            btc_30m = completed_candles(btc_30m, "30m", now_ts) if btc_30m is not None else None
            btc_1h = completed_candles(btc_1h, "1h", now_ts) if btc_1h is not None else None
            btc_4h = completed_candles(btc_4h, "4h", now_ts) if btc_4h is not None else None
            self._evaluate_btc_macro(btc_df, btc_30m=btc_30m, btc_1h=btc_1h, btc_4h=btc_4h)

            # 3. Update and check existing open positions
            await self._update_open_positions(data_maps)

            # 4. Scan for new trade setups if capital and capacity permit
            if not self.is_depleted and self.current_balance >= self.fixed_risk_usd and len(self.open_positions) < self.max_open_positions:
                await self._scan_new_entries(data_maps, scan_tfs=scan_tfs)

            # 5. Check if scheduled Daily, Weekly, or Monthly Audits / Tournaments are due
            now = ph_now()
            if self.last_daily_snapshot_time is None or (now - self.last_daily_snapshot_time).total_seconds() >= 86400:
                asyncio.create_task(self.run_daily_strategy_snapshot())
            if self.last_weekly_optimization_time is None or (now - self.last_weekly_optimization_time).total_seconds() >= 7 * 86400:
                asyncio.create_task(self.run_macro_optimization("WEEKLY"))
            if self.last_monthly_optimization_time is None or (now - self.last_monthly_optimization_time).total_seconds() >= 30 * 86400:
                asyncio.create_task(self.run_monthly_strategy_tournament())

    def _position_history_request(self, symbol: str, timeframe: str, now_ts: float) -> dict:
        """Include every unprocessed bar after downtime plus indicator warmup."""
        position = self.open_positions.get(symbol)
        if not position or position.get("schema_version") != 2 or position.get("timeframe", "15m") != timeframe:
            return {"limit": 300}
        duration = interval_seconds(timeframe)
        last_completed = position.get("last_completed_candle_time", position["entry_candle_time"] - duration)
        rolling_start = int(now_ts // duration) * duration - 299 * duration
        start = int(last_completed) - 199 * duration
        if start >= rolling_start:
            return {"limit": 300}
        return {"limit": int((now_ts - start) // duration) + 1,
                "start_time": start, "end_time": now_ts}

    def _evaluate_btc_macro(
        self, 
        btc_df: Optional[pd.DataFrame],
        btc_1h: Optional[pd.DataFrame] = None,
        btc_4h: Optional[pd.DataFrame] = None,
        **kwargs
    ):
        """Evaluate Bitcoin real-time momentum, 1h intermediate trend, and 4h macro anchor trend."""
        btc_30m = kwargs.get("btc_30m")
        if btc_1h is None and btc_30m is not None:
            btc_1h = btc_30m

        if btc_df is None or len(btc_df) < 50:
            self.btc_macro_status = {
                "regime": "NEUTRAL",
                "trend": "Awaiting BTC Kline Feed",
                "rsi": 50.0,
                "flash_drop": False,
                "gate_status": "ALLOW_ALL",
                "btc_price": 0.0,
                "alignment_1h": "NEUTRAL",
                "alignment_4h": "NEUTRAL"
            }
            return

        last_bar = btc_df.iloc[-1]
        close = float(last_bar['close'])
        ema50 = float(last_bar.get('ema50', close))
        rsi = float(last_bar.get('rsi14', 50.0))
        mom = float(last_bar.get('momentum', 0.0))

        # Calculate 3-bar flash drop
        three_bars_ago_close = float(btc_df.iloc[-4]['close']) if len(btc_df) >= 4 else close
        pct_change_3b = ((close - three_bars_ago_close) / three_bars_ago_close) * 100.0 if three_bars_ago_close > 0 else 0.0

        # Evaluate 1h and 4h higher-timeframe trends
        t_1h = evaluate_tf_trend(btc_1h)
        t_4h = evaluate_tf_trend(btc_4h)

        is_flash_dump = (pct_change_3b <= -1.2)
        is_bullish = (close > ema50) and (rsi >= 48.0) and (mom >= 0) and not is_flash_dump
        is_bearish = (close < ema50) or (rsi <= 42.0) or is_flash_dump

        # 4h Macro Bearish override
        if t_4h["is_valid"] and t_4h["regime"] == "BEARISH":
            is_bullish = False
            is_bearish = True

        if is_flash_dump:
            regime = "FLASH_DUMP"
            gate_status = "BLOCK_LONGS"
            trend_str = f"Flash Dump ({pct_change_3b:.2f}% in 3b) | 1h:{t_1h['regime']} 4h:{t_4h['regime']}"
        elif is_bullish:
            regime = "BULLISH"
            gate_status = "ALLOW_ALL"
            trend_str = f"Bullish Structure | 1h:{t_1h['regime']} 4h:{t_4h['regime']}"
        elif is_bearish:
            regime = "BEARISH"
            gate_status = "BLOCK_LONGS"
            trend_str = f"Bearish Pressure | 1h:{t_1h['regime']} 4h:{t_4h['regime']}"
        else:
            regime = "NEUTRAL"
            gate_status = "ALLOW_ALL"
            trend_str = f"Consolidating @ ${close:,.0f} | 1h:{t_1h['regime']} 4h:{t_4h['regime']}"

        self.btc_macro_status = {
            "regime": regime,
            "trend": trend_str,
            "rsi": round(rsi, 1),
            "flash_drop": is_flash_dump,
            "gate_status": gate_status,
            "btc_price": round(close, 2),
            "alignment_1h": t_1h["regime"],
            "alignment_4h": t_4h["regime"]
        }

    async def _update_open_positions(self, data_map: Any):
        now_ts = time.time()
        for symbol, pos in list(self.open_positions.items()):
            if pos.get("schema_version") != 2:
                continue
            tf = pos.get("timeframe", "15m")
            nested = any(isinstance(value, dict) for value in data_map.values())
            df = data_map.get(tf, {}).get(symbol) if nested else data_map.get(symbol)
            if df is None or len(df) == 0:
                continue
            profile = TIMEFRAME_PROFILES[tf]
            closed_df = completed_candles(df, tf, now_ts)
            last_completed = pos.get("last_completed_candle_time", pos["entry_candle_time"] - interval_seconds(tf))
            for _, row in closed_df[closed_df["time"] > last_completed].sort_values("time").iterrows():
                bar_time = int(row["time"])
                if bar_time < pos["entry_candle_time"]:
                    continue
                bars_held = pos.get("bars_held", 0) + 1
                close_ts = float(row.get("close_time", bar_time + interval_seconds(tf) - 0.001))
                options = {"completed_bars": bars_held, "stagnation_bars": profile["stagnation_bars"],
                           "max_holding_bars": profile["max_holding_bars"]}
                if bar_time >= pos.get("last_observation_time", pos["entry_time"]):
                    event = process_bar(pos, row, timestamp=close_ts, **options)
                else:
                    event = process_price(pos, float(row["close"]), close_ts,
                                          atr=row.get("atr14"), momentum=row.get("momentum", 0),
                                          rsi=row.get("rsi14", 50), **options)
                pos["bars_held"] = bars_held
                pos["last_completed_candle_time"] = bar_time
                self.current_balance += event["cash_delta_usd"]
                if event["closed"]:
                    await self._close_position(symbol, pos["exit_price"], pos["exit_time"], event["exit_reason"])
                    break
            if symbol not in self.open_positions:
                continue
            row = df.sort_values("time").iloc[-1]
            observation_open = float(row["time"])
            # A delayed or out-of-order feed is not a new executable price.
            if (observation_open > now_ts
                    or observation_open + interval_seconds(tf) <= now_ts
                    or observation_open < pos.get("last_price_candle_time", pos["entry_candle_time"])):
                continue
            pos["last_price_candle_time"] = observation_open
            # Indicators for protective decisions come from the last completed candle.
            indicators = closed_df.iloc[-1] if len(closed_df) else row
            event = process_price(pos, float(row["close"]), now_ts,
                                  atr=indicators.get("atr14"), momentum=indicators.get("momentum", 0),
                                  rsi=indicators.get("rsi14", 50), completed_bars=pos["bars_held"],
                                  stagnation_bars=profile["stagnation_bars"], max_holding_bars=profile["max_holding_bars"])
            self.current_balance += event["cash_delta_usd"]
            if event["closed"]:
                await self._close_position(symbol, pos["exit_price"], pos["exit_time"], event["exit_reason"])
            else:
                sign = 1 if pos["direction"] == "LONG" else -1
                dist = sign * (pos["current_price"] - pos["entry_price"])
                pos["unrealized_r"] = dist / pos["risk_distance"]
                pos["unrealized_pnl_usd"] = dist * pos["position_qty"]
                pos["exit_status"] = "Partial profit taken" if pos["tp1_hit"] else ("Protected stop" if pos["is_breakeven_protected"] else "Active")
        await self._update_legacy_positions(data_map)
        self.save_state()

    async def _update_legacy_positions(self, data_map: Any):
        """
        Dual-Stage Position Management & Smart Stagnation Ladder:
        - Stage 1: Breakeven Defense at +1.00R MFE (SL moves to entry +- 0.15R fee shield).
        - Stage 2: Partial Profit Harvest at +1.50R MFE (Banks +0.75R profit, halves position, SL moves to +0.50R).
        - Stage 3: Dynamic Trailing Stop at +2.20R MFE (Locks min +1.50R profit, trails with 1.0x ATR).
        - Stage 4: Unlimited Macro Runner at >= +3.50R MFE (Locks min +2.50R profit, trails with 0.8x ATR).
        - Smart Stagnation Exit: Closes dead chop only if bars >= stagnation_bars, |unrealized| < 0.25R, and momentum flips against trade.
        """
        closed_symbols = []
        for sym, pos in list(self.open_positions.items()):
            if pos.get("schema_version") == 2:
                continue
            pos_tf = pos.get('timeframe', '15m')
            if isinstance(data_map, dict) and any(isinstance(v, dict) for v in data_map.values()):
                # Multi-timeframe map
                df = data_map.get(pos_tf, {}).get(sym)
                if df is None:
                    df = data_map.get("15m", {}).get(sym)
                if df is None:
                    df = data_map.get("30m", {}).get(sym)
                if df is None:
                    df = data_map.get("5m", {}).get(sym)
            else:
                # Single-timeframe fallback
                df = data_map.get(sym) if isinstance(data_map, dict) else None

            if df is None or len(df) == 0:
                continue

            last_bar = df.iloc[-1]
            curr_price = float(last_bar['close'])
            high_price = float(last_bar['high'])
            low_price = float(last_bar['low'])
            curr_time = int(time.time())
            candle_time = int(last_bar['time']) if 'time' in last_bar else 0
            entry_candle_time = pos.get('entry_candle_time', 0)

            # Robust Candle Bar Counting: Only increment when a new candle timestamp is observed
            last_evaluated_time = pos.get('last_evaluated_candle_time', 0)
            if candle_time > 0 and candle_time > last_evaluated_time:
                pos['bars_held'] = pos.get('bars_held', 0) + 1
                pos['last_evaluated_candle_time'] = candle_time
            elif 'bars_held' not in pos or pos.get('bars_held', 0) == 0:
                pos['bars_held'] = 1
                pos['last_evaluated_candle_time'] = candle_time

            # Prevent phantom stop-outs from historical wicks prior to trade entry
            pos['highest_since_entry'] = max(pos.get('highest_since_entry', curr_price), curr_price)
            pos['lowest_since_entry'] = min(pos.get('lowest_since_entry', curr_price), curr_price)

            is_entry_candle = (candle_time > 0 and entry_candle_time > 0 and candle_time == entry_candle_time)
            if is_entry_candle:
                eval_high = max(pos['highest_since_entry'], curr_price)
                eval_low = min(pos['lowest_since_entry'], curr_price)
            else:
                eval_high = high_price
                eval_low = low_price
                pos['highest_since_entry'] = max(pos['highest_since_entry'], high_price)
                pos['lowest_since_entry'] = min(pos['lowest_since_entry'], low_price)

            pos['current_price'] = format_price_precision(curr_price)

            is_long = (pos['direction'] == 'LONG')
            entry_price = float(pos['entry_price'])
            risk_dist = float(pos.get('risk_distance', max(abs(entry_price - float(pos['sl_price'])), 1e-6)))
            target_rr = float(pos.get('target_rr', self.target_rr))
            risk_usd = float(pos.get('risk_amount_usd', self.fixed_risk_usd))
            atr = float(last_bar.get('atr14', risk_dist))
            mom = float(last_bar.get('momentum', 0.0))
            rsi = float(last_bar.get('rsi14', 50.0))

            # Calculate MFE (Maximum Favorable Excursion) & MAE (Maximum Adverse Excursion) in R-multiples
            max_fav_dist = (pos['highest_since_entry'] - entry_price) if is_long else (entry_price - pos['lowest_since_entry'])
            max_adv_dist = (entry_price - pos['lowest_since_entry']) if is_long else (pos['highest_since_entry'] - entry_price)
            mfe = max(0.0, round(max_fav_dist / risk_dist, 2))
            mae = max(0.0, round(max_adv_dist / risk_dist, 2))
            pos['mfe_r'] = max(pos.get('mfe_r', 0.0), mfe)
            pos['mae_r'] = max(pos.get('mae_r', 0.0), mae)

            unrealized_dist = (curr_price - entry_price) if is_long else (entry_price - curr_price)

            # Hard Stop Loss Breach Evaluation
            sl_breached = (eval_low <= float(pos['sl_price'])) if is_long else (eval_high >= float(pos['sl_price']))
            if sl_breached:
                if pos.get('tp1_hit'):
                    outcome = "WIN"
                elif pos.get('is_unlimited_runner') or pos.get('is_profit_locked') or pos.get('is_trailing') or (is_long and float(pos['sl_price']) > entry_price + (0.1 * risk_dist)) or (not is_long and float(pos['sl_price']) < entry_price - (0.1 * risk_dist)):
                    outcome = "TRAILING_STOP_WIN"
                elif pos.get('is_breakeven_protected') or pos.get('is_breakeven'):
                    outcome = "BE_EXIT"
                else:
                    outcome = "LOSS"
                print(f"[LiveBot:ExitEngine] {sym} Stop-loss triggered at ${pos['sl_price']} ({outcome})")
                await self._close_position(sym, exit_price=float(pos['sl_price']), exit_time=curr_time, outcome=outcome, df=df)
                closed_symbols.append(sym)
                continue

            # STAGE 1 (Breakeven Defense at +0.80R to +1.00R MFE)
            be_trigger = 0.80 if target_rr <= 2.0 else 1.00
            if mfe >= be_trigger and not pos.get('is_breakeven_protected'):
                be_price = entry_price + (0.15 * risk_dist) if is_long else entry_price - (0.15 * risk_dist)
                curr_sl = float(pos['sl_price'])
                if (is_long and be_price > curr_sl) or (not is_long and be_price < curr_sl):
                    pos['sl_price'] = format_price_precision(be_price)
                pos['is_breakeven'] = True
                pos['is_breakeven_protected'] = True
                pos['exit_status'] = "Breakeven Protected 🛡️ (+0.15R fee shield)"
                print(f"[LiveBot:ExitEngine] {sym} reached +{be_trigger}R MFE! Activated Breakeven Defense. SL adjusted to ${pos['sl_price']} (+0.15R fee shield).")

            # STAGE 2 (Partial Profit Harvest at +1.00R MFE for 1:2.0 or +1.50R MFE for >=1:3.0)
            tp1_trigger = 1.00 if target_rr <= 2.0 else 1.50
            tp1_gain_mult = 0.50 if target_rr <= 2.0 else 0.75
            if mfe >= tp1_trigger and not pos.get('tp1_hit'):
                pos['tp1_hit'] = True
                partial_gain_usd = round(tp1_gain_mult * risk_usd, 2)
                self.current_balance = round(self.current_balance + partial_gain_usd, 2)
                pos['realized_partial_r'] = tp1_gain_mult
                pos['position_qty'] = round(pos.get('position_qty', 1.0) / 2.0, 6)
                lock_price = entry_price + (0.50 * risk_dist) if is_long else entry_price - (0.50 * risk_dist)
                curr_sl = float(pos['sl_price'])
                if (is_long and lock_price > curr_sl) or (not is_long and lock_price < curr_sl):
                    pos['sl_price'] = format_price_precision(lock_price)
                pos['is_profit_locked'] = True
                pos['exit_status'] = f"TP1 Booked 🎯 (+{tp1_gain_mult:.2f}R Banked, SL @ +0.50R)"
                print(f"[LiveBot:ExitEngine] {sym} reached +{tp1_trigger:.2f}R MFE! TP1 Booked (+{tp1_gain_mult:.2f}R banked). Remaining half runner SL moved to ${pos['sl_price']} (+0.50R).")

            # STAGE 3 (Dynamic Trailing Stop at +2.20R MFE)
            if mfe >= 2.20 and mfe < 3.50:
                pos['is_trailing'] = True
                pos['exit_status'] = "Trailing Runner 🏃 (+1.5R+)"
                trail_sl = curr_price - (1.0 * atr) if is_long else curr_price + (1.0 * atr)
                lock_price = entry_price + (1.50 * risk_dist) if is_long else entry_price - (1.50 * risk_dist)
                curr_sl = float(pos['sl_price'])
                best_sl = max(curr_sl, lock_price, trail_sl) if is_long else min(curr_sl, lock_price, trail_sl)
                pos['sl_price'] = format_price_precision(best_sl)

            # STAGE 4 (Unlimited Macro Runner at >= +3.50R MFE)
            if mfe >= 3.50:
                pos['is_unlimited_runner'] = True
                pos['exit_status'] = "Super Runner 🚀 (+2.5R+)"
                trail_sl = curr_price - (0.8 * atr) if is_long else curr_price + (0.8 * atr)
                lock_price = entry_price + (2.50 * risk_dist) if is_long else entry_price - (2.50 * risk_dist)
                curr_sl = float(pos['sl_price'])
                best_sl = max(curr_sl, lock_price, trail_sl) if is_long else min(curr_sl, lock_price, trail_sl)
                pos['sl_price'] = format_price_precision(best_sl)

            # Profit Target Hit: When target_rr is reached and not currently running as an unlimited trailing runner
            tp_hit = (eval_high >= float(pos['tp_price'])) if is_long else (eval_low <= float(pos['tp_price']))
            if tp_hit and not pos.get('is_unlimited_runner'):
                print(f"[LiveBot:ExitEngine] {sym} Target profit of 1:{target_rr} RR reached at ${pos['tp_price']}! Closing position as WIN.")
                await self._close_position(sym, exit_price=float(pos['tp_price']), exit_time=curr_time, outcome="WIN", df=df)
                closed_symbols.append(sym)
                continue

            # Momentum Exhaustion Safe-Exit: If trade reached > +1.0R and momentum sharply reverses
            if mfe >= 1.0:
                if (is_long and mom < 0 and rsi >= 72.0) or (not is_long and mom > 0 and rsi <= 28.0):
                    print(f"[LiveBot:ExitEngine] {sym} Momentum Exhaustion detected. Securing profits at market.")
                    await self._close_position(sym, exit_price=curr_price, exit_time=curr_time, outcome="MOMENTUM_EXIT", df=df)
                    closed_symbols.append(sym)
                    continue

            # Timeframe-aware dynamic holding parameters
            pos_tf = pos.get('timeframe', '15m')
            tf_profile = TIMEFRAME_PROFILES.get(pos_tf, TIMEFRAME_PROFILES["15m"])
            stagnation_bars = tf_profile.get("stagnation_bars", 16)
            max_hold_bars = tf_profile.get("max_holding_bars", 64)

            # SMART STAGNATION EXIT:
            # A trade is only closed for stagnation if:
            # pos.get('bars_held', 0) >= stagnation_bars and abs(unrealized_dist / risk_dist) < 0.25 and not (mfe >= 0.80 or pos.get('tp1_hit') or pos.get('is_profit_locked') or pos.get('is_unlimited_runner'))
            # AND momentum oscillator flips against trade direction ((is_long and mom < 0) or (not is_long and mom > 0))
            is_stagnant = (
                pos.get('bars_held', 0) >= stagnation_bars
                and abs(unrealized_dist / risk_dist) < 0.25
                and not (mfe >= 0.80 or pos.get('tp1_hit') or pos.get('is_profit_locked') or pos.get('is_unlimited_runner'))
            )
            mom_flipped = (is_long and mom < 0) or (not is_long and mom > 0)

            if is_stagnant and mom_flipped:
                print(f"[LiveBot:ExitEngine] {sym} Smart Stagnation exit reached ({stagnation_bars} bars on {pos_tf} in dead chop with momentum reversal). Exiting trade.")
                await self._close_position(sym, exit_price=curr_price, exit_time=curr_time, outcome="TIME_EXIT", df=df)
                closed_symbols.append(sym)
                continue

            # SAFEGUARD: Max Holding Horizon Timeout (exempting active runners and profitable profit locks)
            if pos.get('bars_held', 0) >= max_hold_bars and not pos.get('is_unlimited_runner') and not (pos.get('is_profit_locked') and mfe >= 1.50):
                print(f"[LiveBot:ExitEngine] {sym} Max Holding Horizon reached ({max_hold_bars} bars on {pos_tf}). Closing trade at market.")
                await self._close_position(sym, exit_price=curr_price, exit_time=curr_time, outcome="TIME_EXIT", df=df)
                closed_symbols.append(sym)
                continue

            unrealized_r = round(unrealized_dist / risk_dist, 2)
            pos['unrealized_r'] = unrealized_r
            pos['unrealized_pnl_usd'] = round(unrealized_r * risk_usd, 2)

        for sym in closed_symbols:
            if sym in self.open_positions:
                del self.open_positions[sym]
                
        if closed_symbols:
            self.save_state()

        # Check if capital depleted after closing positions
        if self.current_balance < self.fixed_risk_usd and len(self.open_positions) == 0:
            await self._handle_capital_depleted()

    async def _scan_new_entries(self, data_map: Any, scan_tfs: Optional[List[str]] = None):
        """Evaluate strategy signals with Circuit Breaker, BTC Macro Gatekeeper, and Sector Limits across active timeframes."""
        if self.current_balance < self.fixed_risk_usd:
            return

        # STRICT RULE: Allowed trading entry timeframes
        if self.timeframe not in ALLOWED_ENTRY_TIMEFRAMES:
            return

        # Portfolio-level circuit breaker active
        if self.circuit_breaker_until:
            if ph_now() < self.circuit_breaker_until:
                self._reject_entry("CIRCUIT_BREAKER")
                return
            else:
                self.circuit_breaker_until = None

        if isinstance(data_map, dict) and any(isinstance(v, dict) for v in data_map.values()):
            tf_dict = data_map
        else:
            tf_dict = {self.timeframe: data_map}

        tfs_to_scan = scan_tfs or (["5m", "15m", "30m"] if self.timeframe == "triple" else (["15m", "30m"] if self.timeframe == "dual" else [self.timeframe]))
        TF_PRIORITY = {"30m": 3, "15m": 2, "5m": 1}

        discovered_signals = []
        candidate_signals: Dict[str, Dict[str, Any]] = {}

        for tf in tfs_to_scan:
            sym_map = tf_dict.get(tf, {})
            for sym, df in sym_map.items():
                now_ts = time.time()
                closed_df = completed_candles(df, tf, now_ts)
                if len(closed_df) < 200:
                    self._reject_entry("ENTRY_WARMUP")
                    continue
                candle_time = int(closed_df.iloc[-1]["time"])
                if now_ts - (candle_time + interval_seconds(tf)) >= interval_seconds(tf):
                    self._reject_entry("STALE_ENTRY_CANDLE")
                    continue
                guard_key = f"{sym}:{tf}"
                if self.symbol_last_entry_candle.get(guard_key, self.symbol_last_entry_candle.get(sym, -1)) >= candle_time:
                    continue
                sym_htf = self.mtf_data.get(sym)
                anchor_tf = ANCHOR_TIMEFRAMES[tf]
                anchor = (sym_htf or {}).get(anchor_tf)
                decision_time = candle_time + interval_seconds(tf)
                anchor = completed_candles(anchor, anchor_tf, decision_time) if anchor is not None else None
                if anchor is None or len(anchor) < 200:
                    self._reject_entry("MISSING_ANCHOR")
                    continue
                if decision_time - (int(anchor.iloc[-1]["time"]) + interval_seconds(anchor_tf)) >= interval_seconds(anchor_tf):
                    self._reject_entry("STALE_ANCHOR")
                    continue
                signal = self._evaluate_active_strategy(closed_df, len(closed_df) - 1, htf_data=sym_htf, timeframe=tf)
                if not signal:
                    self._reject_entry("STRATEGY_OR_ANCHOR_FILTER")

                if signal:
                    signal_tf = tf
                    direction = signal['direction']
                    entry_price = float(df.iloc[-1]['close'])
                    risk_dist = signal['risk_distance']
                    target_rr = signal.get('target_rr', self.target_rr)
                    sector = get_crypto_sector(sym)

                    sl_price = entry_price - risk_dist if direction == "LONG" else entry_price + risk_dist
                    tp1_rr = float(signal.get('tp1_rr', 1.0 if target_rr <= 2.0 else 1.5))
                    tp1_price = signal.get('tp1_price') or format_price_precision(entry_price + (tp1_rr * risk_dist) if direction == "LONG" else entry_price - (tp1_rr * risk_dist))
                    tp_price = entry_price + (target_rr * risk_dist) if direction == "LONG" else entry_price - (target_rr * risk_dist)

                    # Record discovered market signal for 24/7 Live Radar Feed
                    sig_summary = {
                        "symbol": sym,
                        "sector": sector,
                        "timeframe": signal_tf,
                        "direction": direction,
                        "entry_price": format_price_precision(entry_price),
                        "sl_price": format_price_precision(sl_price),
                        "tp1_price": tp1_price,
                        "tp_price": format_price_precision(tp_price),
                        "target_rr": target_rr,
                        "discovered_at": ph_now().strftime("%Y-%m-%d %H:%M:%S"),
                        "context": signal.get('pre_trade_context', {})
                    }
                    discovered_signals.append(sig_summary)

                    # Conflict resolution: if symbol already has a candidate signal, pick higher timeframe priority
                    cand_obj = {
                        "symbol": sym,
                        "sector": sector,
                        "timeframe": signal_tf,
                        "direction": direction,
                        "entry_price": entry_price,
                        "sl_price": sl_price,
                        "tp1_price": tp1_price,
                        "tp1_rr": tp1_rr,
                        "tp_price": tp_price,
                        "risk_dist": risk_dist,
                        "target_rr": target_rr,
                        "candle_time": candle_time,
                        "entry_candle_time": int(df.iloc[-1]["time"]),
                        "signal": signal
                    }
                    if sym not in candidate_signals or TF_PRIORITY.get(signal_tf, 1) > TF_PRIORITY.get(candidate_signals[sym]["timeframe"], 1):
                        candidate_signals[sym] = cand_obj

        if discovered_signals:
            self.latest_signals = (discovered_signals + self.latest_signals)[:25]

        # GATEWAY: If Auto-Trading is DISABLED (Signals-Only Mode), skip trade execution
        if not self.auto_trading_enabled:
            return

        for sym, cand in candidate_signals.items():
            if len(self.open_positions) >= self.max_open_positions:
                break
            if sym in self.open_positions:
                continue

            direction = cand["direction"]
            sector = cand["sector"]
            signal_tf = cand["timeframe"]
            entry_price = cand["entry_price"]
            sl_price = cand["sl_price"]
            tp1_price = cand["tp1_price"]
            tp_price = cand["tp_price"]
            risk_dist = cand["risk_dist"]
            target_rr = cand["target_rr"]
            candle_time = cand["candle_time"]
            signal = cand["signal"]

            # 0. Check Symbol Anti-Churn Loss Cooldown (Prevents rapid re-entry churn on same candle)
            if sym in self.symbol_loss_cooldowns:
                if ph_now() < self.symbol_loss_cooldowns[sym]:
                    self._reject_entry("SYMBOL_COOLDOWN")
                    continue
                else:
                    del self.symbol_loss_cooldowns[sym]

            # 1. Check Bitcoin Macro Trend Gatekeeper (Bypass for BTC itself)
            if sym != "BTCUSDT":
                gate_status = self.btc_macro_status.get("gate_status", "ALLOW_ALL")
                if direction == "LONG" and gate_status == "BLOCK_LONGS":
                    self._reject_entry("BTC_MACRO_GATE")
                    continue
                elif direction == "SHORT" and gate_status == "BLOCK_SHORTS":
                    self._reject_entry("BTC_MACRO_GATE")
                    continue

            # 2. Check Sector Correlation Limits (Max positions per sector)
            active_in_sector = [p for p in self.open_positions.values() if p.get('sector') == sector]
            if len(active_in_sector) >= self.max_positions_per_sector:
                self._reject_entry("SECTOR_LIMIT")
                continue

            self._ensure_forward_configuration()
            entry_time = time.time()
            try:
                pos_record = create_position(direction, entry_price, risk_dist, self.fixed_risk_usd,
                                             target_rr, entry_time, self.fee_pct, self.slippage_pct)
            except ValueError:
                self._reject_entry("INVALID_EXECUTION_LEVELS")
                continue
            next_trade_id = max([t.get("trade_id", 0) for t in self.closed_trades]
                                + [p.get("trade_id", 0) for p in self.open_positions.values()] + [0]) + 1
            pos_record.update({
                "trade_id": next_trade_id, "symbol": sym, "sector": sector,
                "strategy": self.active_strategy_name, "timeframe": signal_tf,
                "entry_time_str": ph_fromtimestamp(entry_time).strftime("%Y-%m-%d %H:%M:%S"),
                "entry_candle_time": cand["entry_candle_time"],
                "signal_candle_time": candle_time,
                "last_completed_candle_time": cand["entry_candle_time"] - interval_seconds(signal_tf),
                "position_value_usd": pos_record["initial_qty"] * pos_record["entry_price"],
                "unrealized_r": 0.0, "unrealized_pnl_usd": 0.0,
                "pre_trade_context": signal.get("pre_trade_context", {}),
                "forward_run_id": self.forward_run_id,
                "configuration": copy.deepcopy(self.forward_run_config),
                "strategy_version": "paper_v2",
                "execution_model": "observed_prices_with_conservative_gap_replay",
            })
            self.current_balance += pos_record["entry_cash_delta_usd"]
            self.open_positions[sym] = pos_record
            self.symbol_last_entry_candle[f"{sym}:{signal_tf}"] = candle_time
            self.save_state()

    def _reject_entry(self, reason):
        self.rejected_entries[reason] = self.rejected_entries.get(reason, 0) + 1

    def _ensure_forward_configuration(self):
        config = self.forward_run_config or {}
        values = {"strategy": self.active_strategy_name, "timeframe": self.timeframe,
                  "params": self.active_params, "risk_amount_usd": self.fixed_risk_usd,
                  "fee_pct": self.fee_pct, "slippage_pct": self.slippage_pct,
                  "max_open_positions": self.max_open_positions,
                  "max_positions_per_sector": self.max_positions_per_sector}
        if not self.forward_run_id or any(config.get(key) != value for key, value in values.items()):
            self._new_forward_run()

    def _evaluate_active_strategy(
        self, 
        df: pd.DataFrame, 
        idx: int,
        htf_data: Optional[Dict[str, pd.DataFrame]] = None,
        timeframe: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Evaluate strategy incorporating dynamic active parameters, RSI safe corridor, and MTF alignment."""
        if len(df) < 50 or idx < 50:
            return None

        if 'squeeze_on' not in df.columns:
            df = compute_crypto_indicators(df)

        target_rr = self.active_params.get("target_rr", self.target_rr)
        tf = timeframe or (self.timeframe if self.timeframe in ["5m", "15m", "30m"] else "15m")
        
        # Support Dynamic Ensemble or Multi-Strategy scanning
        if self.active_strategy_name in ["Dynamic_Ensemble", "Multi_Strategy", "ALL", "Trend_and_Squeeze"]:
            sig = TrendPullbackConfluence.generate_signal(
                df, idx, target_rr=target_rr, params=self.active_params, htf_data=htf_data, timeframe=tf
            )
            if sig:
                return sig
            return SqueezeMomentumBreakout.generate_signal(
                df, idx, target_rr=target_rr, params=self.active_params, htf_data=htf_data, timeframe=tf
            )

        # Match strategy class by active name
        strat_cls = None
        for s in AVAILABLE_STRATEGIES:
            if s.name == self.active_strategy_name:
                strat_cls = s
                break
        if strat_cls is None:
            strat_cls = TrendPullbackConfluence

        return strat_cls.generate_signal(
            df, 
            idx, 
            target_rr=target_rr, 
            params=self.active_params,
            htf_data=htf_data,
            timeframe=tf
        )

        return None

    async def _close_position(self, symbol, exit_price, exit_time, outcome, df=None):
        pos = self.open_positions.get(symbol)
        if pos is None:
            return None
        if pos.get("schema_version") != 2:
            return await self._close_legacy_position(symbol, exit_price, exit_time, outcome, df)
        event = close_position(pos, exit_price, exit_time, reason=outcome)
        self.current_balance += event["cash_delta_usd"]
        record = summarize_position(pos)
        record["exit_time_str"] = ph_fromtimestamp(record["exit_time"]).strftime("%Y-%m-%d %H:%M:%S")
        record["account_balance"] = self.current_balance
        record["diagnostic"] = {
            "catalyst_type": record["exit_reason"],
            "summary": "Modeled paper fills closed the position; PnL includes fill-level fees and adverse slippage.",
            "key_factors": [f"Exit reason: {record['exit_reason']}", f"Net result: {record['net_r']:+.4f}R"],
        }
        report_path = os.path.join(self.reports_dir, f"trade_{record['forward_run_id']}_{record['trade_id']}_{symbol}.md")
        record["report_file"] = report_path
        self._record_closed_trade(symbol, record)
        try:
            os.makedirs(self.reports_dir, exist_ok=True)
            with open(report_path, "w", encoding="utf-8") as stream:
                stream.write(create_trade_journal_md(record))
        except OSError as exc:
            print(f"[LiveBot] Journal export failed: {exc}")
        return record

    def _record_closed_trade(self, symbol, record):
        self.closed_trades.append(record)
        self.open_positions.pop(symbol, None)
        self._apply_trade_guards(symbol, record)
        self.save_state()
        self._archive_entry("trades", record)
        cohort_count = sum(t.get("forward_run_id") == self.forward_run_id for t in self.closed_trades)
        if (self.is_running and self.optimize_every_n_trades > 0
                and record.get("forward_run_id") == self.forward_run_id
                and cohort_count % self.optimize_every_n_trades == 0):
            asyncio.create_task(self.run_self_optimization())

    def _apply_trade_guards(self, symbol, record):
        net_r = record.get("net_r", 0.0)
        reason = record.get("exit_reason", record.get("outcome"))
        stagnant_reasons = ("TIME_EXIT", "MAX_HOLD", "BE_EXIT", "BREAKEVEN_DEFENSE", "MOMENTUM_EXIT")
        # Loss accounting takes precedence over a descriptive exit label.
        if net_r < 0:
            count = self.symbol_consecutive_losses.get(symbol, 0) + 1
            self.symbol_consecutive_losses[symbol] = count
            self.symbol_loss_cooldowns[symbol] = ph_now() + timedelta(hours=24 if count >= 2 else 4)
            losses = 0
            for trade in reversed(self.closed_trades[-6:]):
                if trade.get("net_r", 0) < 0:
                    losses += 1
                else:
                    break
            if losses >= 2:
                self.circuit_breaker_until = ph_now() + timedelta(minutes=120 if losses >= 3 else 30)
        elif reason in stagnant_reasons:
            self.symbol_loss_cooldowns[symbol] = ph_now() + timedelta(hours=2)
            stagnant = sum(t.get("exit_reason", t.get("outcome")) in stagnant_reasons for t in self.closed_trades[-6:])
            if stagnant >= 2:
                self.circuit_breaker_until = ph_now() + timedelta(minutes=60)
        elif net_r > 0:
            self.symbol_consecutive_losses[symbol] = 0

    async def _close_legacy_position(
        self, 
        symbol: str, 
        exit_price: float, 
        exit_time: int, 
        outcome: str, 
        df: Optional[pd.DataFrame] = None
    ) -> Optional[Dict[str, Any]]:
        """Close an active paper trade and deduct/credit fixed $1.00 risk."""
        pos = self.open_positions.get(symbol)
        if not pos:
            return None

        is_long = (pos['direction'] == 'LONG')
        risk_dist = float(pos.get('risk_distance', 1.0))
        risk_usd = float(pos.get('risk_amount_usd', self.fixed_risk_usd))
        friction_r = 0.08
        
        if pos.get('tp1_hit'):
            # Dual-stage exit calculation for remaining half runner
            pos_target_rr = float(pos.get('target_rr', self.target_rr))
            tp1_banked_r = float(pos.get('realized_partial_r', 0.50 if pos_target_rr <= 2.0 else 0.75))
            runner_raw_r = ((exit_price - float(pos['entry_price'])) if is_long else (float(pos['entry_price']) - exit_price)) / risk_dist if risk_dist > 0 else 0.0
            total_net_r = round(tp1_banked_r + (0.5 * (runner_raw_r - friction_r)), 2)
            runner_pnl_usd = round(0.5 * (runner_raw_r - friction_r) * risk_usd, 2)
            self.current_balance = round(self.current_balance + runner_pnl_usd, 2)
            raw_r = round(tp1_banked_r + 0.5 * runner_raw_r, 2)
            net_r = total_net_r
            pnl_usd = round(total_net_r * risk_usd, 2)

            if outcome == "LOSS" or outcome == "TRAILING_STOP_WIN" or outcome == "WIN":
                outcome = "WIN" if total_net_r > 0.05 else "BE_EXIT"
        else:
            if outcome == "WIN":
                raw_r = float(pos.get('target_rr', self.target_rr))
                net_r = round(raw_r - friction_r, 2)
            elif outcome in ["BE_EXIT", "BREAKEVEN_DEFENSE"]:
                raw_r = 0.15
                net_r = 0.0  # Zero loss (fees covered)
            elif outcome in ["TRAILING_STOP_WIN", "MOMENTUM_EXIT", "TIME_EXIT", "FORCED_CLOSE", "MANUAL_CLOSE"]:
                dist = (exit_price - float(pos['entry_price'])) if is_long else (float(pos['entry_price']) - exit_price)
                raw_r = round(dist / risk_dist, 2) if risk_dist > 0 else 0.0
                net_r = round(raw_r - friction_r, 2)
            else:  # LOSS
                raw_r = -1.0
                net_r = round(raw_r - friction_r, 2)

            pnl_usd = round(net_r * risk_usd, 2)
            self.current_balance = round(self.current_balance + pnl_usd, 2)

        df_len = len(df) if df is not None else 1
        bars_held = max(1, pos.get('bars_held', df_len - 1))

        closed_record = {
            "trade_id": pos.get('trade_id', 1),
            "symbol": symbol,
            "sector": pos.get('sector', 'ALT'),
            "strategy": pos.get('strategy', self.active_strategy_name),
            "timeframe": pos.get('timeframe', self.timeframe),
            "direction": pos.get('direction', 'LONG'),
            "entry_time": pos.get('entry_time', int(time.time())),
            "entry_time_str": pos.get('entry_time_str', ph_now().strftime("%Y-%m-%d %H:%M:%S")),
            "exit_time": exit_time if exit_time else int(time.time()),
            "exit_time_str": ph_now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": pos.get('entry_price', 0.0),
            "exit_price": format_price_precision(exit_price),
            "sl_price": pos.get('sl_price', 0.0),
            "tp_price": pos.get('tp_price', 0.0),
            "tp1_price": pos.get('tp1_price', 0.0),
            "tp1_hit": pos.get('tp1_hit', False),
            "target_rr": pos.get('target_rr', self.target_rr),
            "risk_amount_usd": risk_usd,
            "position_qty": pos.get('position_qty', 1.0),
            "initial_qty": pos.get('initial_qty', pos.get('position_qty', 1.0)),
            "position_value_usd": pos.get('position_value_usd', 0.0),
            "outcome": outcome,
            "raw_r": raw_r,
            "net_r": net_r,
            "pnl_usd": pnl_usd,
            "account_balance": self.current_balance,
            "mfe_r": pos.get('mfe_r', 0.0),
            "mae_r": pos.get('mae_r', 0.0),
            "bars_held": bars_held,
            "friction_breakdown": f"Gross: {raw_r:+.2f}R | Friction: -{friction_r:.2f}R | Net: {net_r:+.2f}R (${pnl_usd:+.2f} USD)",
            "trade_efficiency": f"MFE: +{pos.get('mfe_r', 0.0)}R | MAE: -{pos.get('mae_r', 0.0)}R",
            "pre_trade_context": pos.get('pre_trade_context', {})
        }

        # Run automated root-cause diagnostic
        if df is not None and len(df) > 0:
            diagnostic = diagnose_trade_outcome(closed_record, df, max(0, len(df) - 10), len(df) - 1)
        else:
            diagnostic = diagnose_trade_outcome(closed_record, pd.DataFrame(), 0, 0)
        closed_record['diagnostic'] = diagnostic

        # Write detailed individual trade markdown journal to reports/
        os.makedirs(self.reports_dir, exist_ok=True)
        trade_report_path = os.path.join(self.reports_dir, f"trade_journal_#{pos['trade_id']}_{symbol}_{outcome}.md")
        try:
            with open(trade_report_path, "w", encoding="utf-8") as f:
                f.write(f"# Trade Record & Post-Mortem Diagnostic #{pos['trade_id']}: {symbol} ({pos['direction']})\n")
                f.write(f"*Closed on: {closed_record['exit_time_str']}*\n\n")
                f.write(f"## 1. Trade Execution Summary\n")
                f.write(f"- **Outcome**: `{'PROFIT (WIN)' if outcome == 'WIN' else ('FORCED CLOSE' if outcome == 'FORCED_CLOSE' else 'LOSS')}`\n")
                f.write(f"- **Realized PnL**: `${pnl_usd:+.2f} USD` ({net_r:+.2f} R)\n")
                f.write(f"- **Resulting Account Balance**: `${self.current_balance:.2f} USD`\n")
                f.write(f"- **Entry Price**: `${closed_record['entry_price']}` | **Exit Price**: `${closed_record['exit_price']}`\n")
                f.write(f"- **Stop Loss**: `${closed_record['sl_price']}` | **Take Profit**: `${closed_record['tp_price']}` (1:{closed_record.get('target_rr', 2.0)} RR)\n")
                f.write(f"- **Position Size**: `{closed_record['position_qty']} units` (Notional Value: `${closed_record['position_value_usd']:.2f}`)\n")
                f.write(f"- **Max Favorable Excursion (MFE)**: `+{closed_record['mfe_r']} R`\n")
                f.write(f"- **Max Adverse Excursion (MAE)**: `-{closed_record['mae_r']} R`\n")
                f.write(f"- **Bars / Candles Held**: `{bars_held} bars`\n\n")
                f.write(f"## 2. Pre-Trade Quantitative Context (Why Entered)\n")
                ctx = pos.get('pre_trade_context', {})
                f.write(f"- **Regime**: `{ctx.get('regime', 'N/A')}`\n")
                f.write(f"- **Technical Catalyst**: {ctx.get('reason', 'N/A')}\n")
                f.write(f"- **Relative Volume Surge (RVOL)**: `{ctx.get('rvol', 'N/A')}x` (vs 20-bar SMA)\n")
                f.write(f"- **RSI (14)**: `{ctx.get('rsi', 'N/A')}`\n")
                f.write(f"- **Momentum Oscillator**: `{ctx.get('momentum', 'N/A')}`\n")
                f.write(f"- **Volatility (ATR14)**: `{ctx.get('volatility_atr', 'N/A')}`\n\n")
                f.write(f"## 3. Post-Trade Root Cause Diagnostic\n")
                f.write(f"- **Diagnostic Classification**: `{diagnostic.get('catalyst_type', 'N/A')}`\n")
                f.write(f"- **Summary**: {diagnostic.get('summary', 'Resolved according to plan.')}\n")
                if diagnostic.get('key_factors'):
                    f.write("- **Key Determining Factors**:\n")
                    for factor in diagnostic['key_factors']:
                        f.write(f"  - {factor}\n")
            closed_record['report_file'] = trade_report_path
        except Exception as e:
            print(f"[LiveBot] Notice: Could not write trade journal markdown: {e}")

        closed_record["accounting_mode"] = "legacy"
        self._record_closed_trade(symbol, closed_record)

        return closed_record

    async def force_close_position(
        self, 
        symbol: str, 
        exit_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """Manually force close an active live position at current market price."""
        clean_sym = symbol.upper().replace("/", "").replace("-", "")
        pos = self.open_positions.get(clean_sym)
        if not pos:
            return None

        explicit_price = exit_price is not None and np.isfinite(exit_price) and exit_price > 0
        # An explicit valid reference price must not be replaced by a later fetch.
        if exit_price is None or exit_price <= 0:
            exit_price = pos.get('current_price', pos.get('entry_price', 0.0))

        df = None
        try:
            if not explicit_price:
                async with aiohttp.ClientSession() as session:
                    df = await fetch_symbol_klines(session, clean_sym, interval=pos.get("timeframe", "15m"), limit=20)
                    if df is not None and len(df) > 0:
                        df = compute_crypto_indicators(df)
                        last_close = float(df.iloc[-1]['close'])
                        if last_close > 0:
                            exit_price = last_close
        except Exception:
            pass

        exit_time = int(time.time())
        closed_trade = await self._close_position(
            symbol=clean_sym,
            exit_price=exit_price,
            exit_time=exit_time,
            outcome="FORCED_CLOSE",
            df=df
        )

        # Check if capital depleted after closing position
        if self.current_balance < self.fixed_risk_usd and len(self.open_positions) == 0:
            await self._handle_capital_depleted()

        return closed_trade

    def _archive_entry(self, category: str, entry: Dict[str, Any]):
        """Persist structured records into the permanent historical archive JSON file."""
        try:
            os.makedirs(self.reports_dir, exist_ok=True)
            archive_data = {
                "created_at": ph_now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_trades_archived": 0,
                "trades": [],
                "micro_optimizations": [],
                "weekly_macro_optimizations": [],
                "monthly_macro_audits": []
            }
            if os.path.exists(self.archive_file):
                try:
                    with open(self.archive_file, "r", encoding="utf-8") as f:
                        archive_data = json.load(f)
                except Exception:
                    pass

            if category not in archive_data:
                archive_data[category] = []

            archive_data[category].append(entry)
            if category == "trades":
                archive_data["total_trades_archived"] = len(archive_data["trades"])
            archive_data["last_updated"] = ph_now().strftime("%Y-%m-%d %H:%M:%S")

            with open(self.archive_file, "w", encoding="utf-8") as f:
                json.dump(archive_data, f, indent=2)
        except Exception as e:
            print(f"[LiveBot:Archive] Notice: Error archiving data: {e}")

    async def run_macro_optimization(self, period: str = "WEEKLY") -> Dict[str, Any]:
        return await self._run_report_only_evaluation(period.upper())


    async def _handle_capital_depleted(self):
        """
        Auto-Stop & Depletion Handler:
        Triggered when capital is depleted (< $1.00 USD).
        Stops background scanner immediately and compiles an executive summary report.
        """
        self.is_depleted = True
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None

        print("\n========================================================")
        print("  [!] CAPITAL DEPLETED - SCANNER AUTOMATICALLY STOPPED   ")
        print("========================================================")
        print(f" Initial Capital: ${self.initial_capital:.2f} USD")
        print(f" Remaining Balance: ${self.current_balance:.2f} USD")
        print(f" Total Trades Executed: {len(self.closed_trades)}")
        print(" Compiling final summary report...")

        report_file = self._generate_depletion_summary_report()
        self.depletion_report_file = report_file
        self.save_state()
        print(f" -> Final Depletion Summary Report saved to: {report_file}\n")

    def _generate_depletion_summary_report(self) -> str:
        """Generate formatted Markdown summary report on capital depletion."""
        os.makedirs(self.reports_dir, exist_ok=True)
        timestamp_str = ph_now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(self.reports_dir, f"capital_depleted_summary_{timestamp_str}.md")

        total_trades = len(self.closed_trades)
        wins = [t for t in self.closed_trades if t.get('net_r', 0) > 0]
        losses = [t for t in self.closed_trades if t.get('net_r', 0) <= 0]
        
        win_rate = round((len(wins) / total_trades * 100.0), 2) if total_trades > 0 else None
        total_net_r = round(sum(t.get('net_r', 0) for t in self.closed_trades), 2)
        total_pnl_usd = round(self.current_balance - self.initial_capital, 2)
        
        total_win_r = sum(t.get('net_r', 0) for t in wins)
        total_loss_r = abs(sum(t.get('net_r', 0) for t in losses))
        profit_factor = round(total_win_r / total_loss_r, 2) if total_loss_r > 0 else None
        expectancy_r = round(total_net_r / total_trades, 3) if total_trades > 0 else None

        lines = [
            "# Automated Trading Bot - Capital Depletion Summary Report",
            f"*Generated on: {ph_now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## 1. Executive Performance Summary",
            f"- **Starting Capital**: `${self.initial_capital:.2f} USD`",
            f"- **Final Balance**: `${self.current_balance:.2f} USD`",
            f"- **Total Net PnL**: `${total_pnl_usd:+.2f} USD` ({total_net_r:+.2f} R)",
            f"- **Risk Per Trade**: `${self.fixed_risk_usd:.2f} USD` (Fixed 1R)",
            f"- **Target Risk-to-Reward**: `1:{self.target_rr} RR` (Minimum)",
            f"- **Total Trades Taken**: `{total_trades}` ({len(wins)} Wins / {len(losses)} Losses)",
            f"- **Recorded Win Rate**: `{str(win_rate) + '%' if win_rate is not None else 'Not validated'}` (includes unverified legacy history)",
            f"- **Profit Factor**: `{profit_factor if profit_factor is not None else 'Not validated / no recorded losses'}`",
            f"- **Expectancy per Trade**: `{format(expectancy_r, '+.3f') + ' R' if expectancy_r is not None else 'Not validated'}`",
            f"- **Scanner Status**: **AUTOMATICALLY HALTED (Capital Depleted)**",
            "",
            "## 2. Root-Cause Diagnostic Analysis & Lessons Learned"
        ]

        # Break down catalysts
        catalysts = {}
        for t in self.closed_trades:
            cat = t.get('diagnostic', {}).get('catalyst_type', 'Unclassified')
            catalysts[cat] = catalysts.get(cat, 0) + 1

        for cat, count in catalysts.items():
            pct = round((count / total_trades) * 100.0, 1) if total_trades > 0 else 0
            lines.append(f"- **{cat}**: {count} trades ({pct}%)")

        lines.extend([
            "",
            "## 3. Complete Trade Journal Log",
            "| # | Symbol | Type | Entry | Exit | Net R | Net PnL ($) | Outcome | Catalyst |",
            "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
        ])

        for t in self.closed_trades:
            diag = t.get('diagnostic', {})
            lines.append(
                f"| #{t['trade_id']} | {t['symbol']} | {t['direction']} | ${t['entry_price']} | ${t['exit_price']} | {t['net_r']:+.2f}R | ${t.get('pnl_usd', 0):+.2f} | **{t['outcome']}** | {diag.get('catalyst_type', 'N/A')} |"
            )

        with open(report_filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return report_filename

    def _analyze_recent_trade_failures(self) -> Dict[str, Any]:
        """
        Analyze recent closed trades for systemic failure patterns.
        Returns defensive adaptation parameters if high loss or wick trap rate is detected.
        """
        recent = self.closed_trades[-10:] if len(self.closed_trades) >= 5 else self.closed_trades
        if not recent:
            return {
                "wick_defense_active": False,
                "min_atr_mult": 1.35,
                "min_rvol": 1.15,
                "quarantined_symbols": [],
                "failure_rate": 0.0,
                "wick_trap_rate": 0.0
            }
        
        losses = [t for t in recent if t.get('outcome') == 'LOSS' or t.get('net_r', 0) < 0]
        failure_rate = len(losses) / len(recent)
        
        # Count immediate wick traps (<= 2 bars held or Wick catalyst)
        wick_traps = [
            t for t in losses 
            if t.get('bars_held', 99) <= 2 or "Wick" in t.get('diagnostic', {}).get('catalyst_type', '')
        ]
        wick_trap_rate = len(wick_traps) / len(losses) if losses else 0.0
        
        # Count losing symbols with >= 2 losses in recent window
        sym_counts: Dict[str, int] = {}
        for t in losses:
            s = t.get('symbol')
            if s:
                sym_counts[s] = sym_counts.get(s, 0) + 1
        
        quarantined = [s for s, count in sym_counts.items() if count >= 2]
        
        # Wick defense activates if >= 40% losses are fast wick stopouts
        wick_defense_active = (failure_rate >= 0.4 and wick_trap_rate >= 0.3)
        
        return {
            "wick_defense_active": wick_defense_active,
            "min_atr_mult": 2.40 if wick_defense_active else 2.20,
            "min_rvol": 1.60 if wick_defense_active else 1.45,
            "quarantined_symbols": quarantined,
            "failure_rate": round(failure_rate * 100.0, 1),
            "wick_trap_rate": round(wick_trap_rate * 100.0, 1)
        }

    def _generate_candidate_parameters(self, failure_diag: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a diverse grid of parameter suites dynamically shaped by live failure feedback."""
        base_atr = 2.40 if failure_diag.get("wick_defense_active") else 2.20
        base_rvol = max(1.45, failure_diag.get("min_rvol", 1.45))
        
        atr_steps = [base_atr, round(base_atr + 0.20, 2), round(base_atr + 0.40, 2)]
        rvol_steps = [base_rvol, round(base_rvol + 0.15, 2)]
        rr_steps = [2.0]
        rsi_presets = [
            {"rsi_min_long": 38.0, "rsi_max_long": 58.0, "rsi_min_short": 42.0, "rsi_max_short": 62.0}
        ]
        
        candidates = []
        for atr in atr_steps:
            for rvol in rvol_steps:
                for rr in rr_steps:
                    for rsi in rsi_presets:
                        candidates.append({
                            "rvol_min": rvol,
                            "atr_sl_mult": atr,
                            "target_rr": rr,
                            "rsi_min_long": rsi["rsi_min_long"],
                            "rsi_max_long": rsi["rsi_max_long"],
                            "rsi_min_short": rsi["rsi_min_short"],
                            "rsi_max_short": rsi["rsi_max_short"],
                            "min_body_ratio": 0.35,
                            "max_wick_ratio": 0.40,
                            "min_risk_dist_pct": 0.012,
                            "adx_min": 22.0
                        })
        return candidates

    async def run_self_optimization(self) -> Dict[str, Any]:
        return await self._run_report_only_evaluation("MICRO")


    async def run_daily_strategy_snapshot(self) -> Dict[str, Any]:
        self.last_daily_snapshot_time = ph_now()
        telemetry = self.get_telemetry()
        record = {"date": self.last_daily_snapshot_time.strftime("%Y_%m_%d"),
                  "account_balance": self.current_balance,
                  "forward_test": telemetry["forward_test"], "legacy_history": telemetry["legacy_history"],
                  "strategy": self.active_strategy_name, "timeframe": self.timeframe,
                  "optimizer_mode": "report_only", "validation_status": "NOT_VALIDATED"}
        os.makedirs(self.reports_dir, exist_ok=True)
        path = os.path.join(self.reports_dir, f"forward_snapshot_{self.forward_run_id}_{int(time.time())}.json")
        atomic_write_json(path, record)
        record["report_file"] = path
        self.save_state()
        return record

    async def run_monthly_strategy_tournament(self) -> Dict[str, Any]:
        return await self._run_report_only_evaluation("MONTHLY")


    async def run_champions_of_champions_gauntlet(self, current_champ=None) -> Dict[str, Any]:
        """Historical comparison only; this endpoint does not execute a new simulation."""
        return {"status": "HISTORICAL_COMPARISON", "label": "Historical comparison (not a fresh simulation)",
                "optimizer_mode": "report_only", "rankings": [dict(item, validation_status=("MEASURED" if item.get("evaluation_id") else "LEGACY_UNVERIFIED")) for item in self.hall_of_fame],
                "strategy_name": self.active_strategy_name, "win_rate_pct": None,
                "reproducibility_score": None, "net_expectancy_r": None}

    async def _run_report_only_evaluation(self, mode):
        from validation import run_report_only_evaluation
        if self._evaluation_lock.locked():
            return {"status": "EVALUATION_RUNNING", "optimizer_mode": "report_only", "improved": False}
        async with self._evaluation_lock:
            now = ph_now()
            self.last_optimization_time = now
            if mode == "WEEKLY":
                self.last_weekly_optimization_time = now
            if mode == "MONTHLY":
                self.last_monthly_optimization_time = now
            incumbent = {"strategy": self.active_strategy_name, "timeframe": self.timeframe,
                         "params": copy.deepcopy(self.active_params), "target_rr": self.target_rr,
                         "fee_pct": self.fee_pct, "slippage_pct": self.slippage_pct}
            research_mode = {"MICRO": "micro", "WEEKLY": "macro", "MONTHLY": "monthly"}.get(mode, "macro")
            result = await run_report_only_evaluation(mode=research_mode, report_dir=self.reports_dir,
                                                     incumbent=incumbent, symbols=self.symbols or None)
            result = dict(result, optimizer_mode="report_only", improved=False, promoted=False,
                          timestamp=now.strftime("%Y-%m-%d %H:%M:%S"))
            self.optimization_logs.append(result)
            if mode != "MICRO":
                self.macro_audits.append(result)
            self.save_state()
            return result


    def _forward_metrics(self):
        closed = [t for t in self.closed_trades if t.get("forward_run_id") == self.forward_run_id and t.get("schema_version") == 2]
        positions = [p for p in self.open_positions.values() if p.get("forward_run_id") == self.forward_run_id and p.get("schema_version") == 2]
        metrics = compile_simulation_metrics(closed, self.active_strategy_name, self.target_rr)
        records = closed + positions
        flows = sorted((f for p in records for f in p.get("fills", [])), key=lambda f: (f["timestamp"], f["fill_id"]))
        equity = peak = drawdown = 0.0
        equity_r = peak_r = drawdown_r = 0.0
        risk_by_fill = sorted(((f["timestamp"], f["fill_id"], f["cash_delta_usd"] / p["risk_amount_usd"]) for p in records for f in p.get("fills", [])))
        for fill in flows:
            equity += fill["cash_delta_usd"]
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        for _, _, cash_r in risk_by_fill:
            equity_r += cash_r
            peak_r = max(peak_r, equity_r)
            drawdown_r = max(drawdown_r, peak_r - equity_r)
        return {"run_id": self.forward_run_id, "configuration": copy.deepcopy(self.forward_run_config),
                "optimizer_mode": "report_only", "validation_status": "NOT_VALIDATED",
                "closed_trades": len(closed), "open_positions": len(positions),
                "net_pnl_usd": round(equity, 8), "closed_pnl_usd": round(sum(t["pnl_usd"] for t in closed), 8),
                "unrealized_pnl_usd": round(sum(p.get("unrealized_pnl_usd", 0) for p in positions), 8),
                "fees_usd": round(sum(p.get("fees_usd", 0) for p in records), 8),
                "slippage_usd": round(sum(p.get("slippage_usd", 0) for p in records), 8),
                "costs_usd": round(sum(p.get("fees_usd", 0) + p.get("slippage_usd", 0) for p in records), 8),
                "max_drawdown_usd": round(drawdown, 8), "max_drawdown_r": round(drawdown_r, 8),
                "expectancy_r": metrics.get("expectancy_r") if closed else None,
                "win_rate_pct": metrics.get("win_rate_pct") if closed else None,
                "profit_factor": metrics.get("profit_factor") if closed else None,
                "rejected_entries": dict(self.rejected_entries),
                "cost_assumptions": {"fee_pct": self.fee_pct, "slippage_pct": self.slippage_pct,
                                     "basis": "per modeled fill", "funding_or_borrow_costs": "not modeled"}}

    def get_telemetry(self) -> Dict[str, Any]:
        """Return full real-time telemetry metrics for dashboard visualization."""
        total_trades = len(self.closed_trades)
        wins = [t for t in self.closed_trades if t.get('net_r', 0) > 0]
        be_trades = [t for t in self.closed_trades if t.get("net_r", 0) == 0]
        losses = [t for t in self.closed_trades if t.get("net_r", 0) < 0]
        
        win_rate = round((len(wins) / total_trades * 100.0), 2) if total_trades > 0 else None
        total_net_r = round(sum(t.get('net_r', 0) for t in self.closed_trades), 2)
        total_win_r = sum(t.get('net_r', 0) for t in wins)
        total_loss_r = abs(sum(t.get('net_r', 0) for t in losses))
        profit_factor = round(total_win_r / total_loss_r, 2) if total_loss_r > 0 else None
        expectancy_r = round(total_net_r / total_trades, 3) if total_trades > 0 else None

        # USD Balances - preserve actual wallet balance
        total_realized_pnl_usd = round(sum(t.get('pnl_usd', round(t.get('net_r', 0) * self.fixed_risk_usd, 2)) for t in self.closed_trades), 2)

        unrealized_pnl_usd = round(sum(p.get('unrealized_pnl_usd', 0.0) for p in self.open_positions.values()), 2)
        equity_usd = round(self.current_balance + unrealized_pnl_usd, 2)
        total_pnl_usd = total_realized_pnl_usd
        total_pnl_pct = None  # Historical resets prevent a continuous account-return percentage.

        status_str = "DEPLETED_STOPPED" if self.is_depleted else ("RUNNING" if self.is_running else "PAUSED")

        sanitized_positions = []
        for p in self.open_positions.values():
            p_copy = dict(p)
            if p_copy.get("timeframe") not in ALLOWED_ENTRY_TIMEFRAMES:
                p_copy["timeframe"] = self.timeframe
            sanitized_positions.append(p_copy)

        return {
            "status": status_str,
            "is_depleted": self.is_depleted,
            "depletion_report_file": self.depletion_report_file,
            "timeframe": self.timeframe,
            "timeframe_profile": self.timeframe_profile,
            "initial_capital": self.initial_capital,
            "current_balance": self.current_balance,
            "equity_usd": equity_usd,
            "unrealized_pnl_usd": unrealized_pnl_usd,
            "total_pnl_usd": total_pnl_usd,
            "total_pnl_pct": total_pnl_pct,
            "fixed_risk_usd": self.fixed_risk_usd,
            "target_rr": self.active_params.get("target_rr", self.target_rr),
            "active_strategy": self.active_strategy_name,
            "active_params": self.active_params,
            "champion_stats": self.champion_stats,
            "all_time_grand_champion": self.all_time_grand_champion,
            "watched_pairs_count": len(self.symbols),
            "open_positions_count": len(sanitized_positions),
            "max_open_positions": self.max_open_positions,
            "open_positions": sanitized_positions,
            "btc_macro_status": self.btc_macro_status,
            "total_closed_trades": total_trades,
            "win_count": len(wins),
            "loss_count": len(losses),
            "win_rate_pct": win_rate,
            "total_net_r": total_net_r,
            "profit_factor": profit_factor,
            "expectancy_r": expectancy_r,
            "last_scan_time": self.last_scan_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_scan_time else None,
            "last_optimization_time": self.last_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_optimization_time else None,
            "last_daily_snapshot_time": self.last_daily_snapshot_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_daily_snapshot_time else None,
            "last_weekly_optimization_time": self.last_weekly_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_weekly_optimization_time else None,
            "last_monthly_optimization_time": self.last_monthly_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_monthly_optimization_time else None,
            "recent_optimizations": self.optimization_logs[-5:],
            "macro_audits": self.macro_audits[-5:],
            "hall_of_fame": [dict(item, validation_status=("MEASURED" if item.get("evaluation_id") else "LEGACY_UNVERIFIED")) for item in self.hall_of_fame[-5:]],
            "optimizer_mode": "report_only",
            "forward_test": self._forward_metrics(),
            "legacy_history": {"trades": sum(t.get("schema_version") != 2 for t in self.closed_trades),
                               "net_pnl_usd": sum(t.get("pnl_usd", 0) for t in self.closed_trades if t.get("schema_version") != 2),
                               "validation_status": "LEGACY_UNVERIFIED"},
            "auto_trading_enabled": self.auto_trading_enabled,
            "circuit_breaker_active": bool(self.circuit_breaker_until and ph_now() < self.circuit_breaker_until),
            "circuit_breaker_until": self.circuit_breaker_until.strftime("%Y-%m-%d %H:%M:%S") if self.circuit_breaker_until and self.circuit_breaker_until > ph_now() else None,
            "quarantined_symbols": [sym for sym, dt in self.symbol_loss_cooldowns.items() if dt > ph_now()],
            "latest_signals": self.latest_signals[-15:],
            "recent_journal": self.closed_trades[::-1],
            "api_rate_limit": rate_limit_manager.get_telemetry()
        }

# Created explicitly by the application at startup; importing this module is read-only.
bot_instance = None
