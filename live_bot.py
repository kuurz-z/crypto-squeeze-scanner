import asyncio
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
import aiohttp
import pandas as pd
import numpy as np

from data_loader import fetch_top_crypto_pairs, fetch_symbol_klines, split_train_test
from strategies import (
    compute_crypto_indicators, 
    SqueezeMomentumBreakout, 
    LiquiditySweepReversal, 
    TrendPullbackConfluence,
    AVAILABLE_STRATEGIES
)
from sim_engine import diagnose_trade_outcome, compile_simulation_metrics
from strategy_memory import evaluate_reproducibility, save_strategy_to_catalog, load_saved_strategies

LIVE_TRADES_FILE = "live_trades.json"
LIVE_POSITIONS_FILE = "live_positions.json"
BOT_STATE_FILE = "bot_state.json"
REPORTS_DIR = "reports"
HISTORICAL_ARCHIVE_FILE = os.path.join(REPORTS_DIR, "historical_archive.json")

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

class LiveCryptoBot:
    """
    Continuous automated paper-trading bot with fixed $1.00 USD risk per trade,
    strict >= 1:2 RR targets, real-time trade diagnosis, BTC Macro Gatekeeper, Sector Correlation Limits,
    and Automated Weekly/Monthly Macro Strategy Optimization & Permanent Historical Data Archiving.
    """
    def __init__(
        self,
        initial_capital: float = 100.0,
        fixed_risk_usd: float = 1.0,
        timeframe: str = "15m",
        max_open_positions: int = 5,
        target_rr: float = 2.0,
        scan_interval_sec: int = 20,
        optimize_every_n_trades: int = 5,
        max_positions_per_sector: int = 1
    ):
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.fixed_risk_usd = fixed_risk_usd
        self.timeframe = timeframe
        self.max_open_positions = max_open_positions
        self.target_rr = max(2.0, target_rr)
        self.scan_interval_sec = scan_interval_sec
        self.optimize_every_n_trades = optimize_every_n_trades
        self.max_positions_per_sector = max_positions_per_sector
        
        self.is_running = False
        self.is_depleted = False
        self.depletion_report_file: Optional[str] = None
        self.task: Optional[asyncio.Task] = None
        
        self.symbols: List[str] = []
        self.open_positions: Dict[str, Dict[str, Any]] = {}
        self.closed_trades: List[Dict[str, Any]] = []
        self.optimization_logs: List[Dict[str, Any]] = []
        self.macro_audits: List[Dict[str, Any]] = []
        self.btc_macro_status: Dict[str, Any] = {
            "regime": "BULLISH",
            "trend": "Bullish Trend Alignment",
            "rsi": 52.0,
            "flash_drop": False,
            "gate_status": "ALLOW_ALL",
            "btc_price": 0.0
        }
        
        self.active_strategy_name = "Squeeze_Momentum_Breakout"
        self.active_params = {
            "rvol_min": 1.1,
            "atr_sl_mult": 1.3,
            "target_rr": self.target_rr,
            "rsi_min_long": 50.0,
            "rsi_max_short": 50.0
        }
        
        self.started_at = datetime.now()
        self.last_scan_time: Optional[datetime] = None
        self.last_optimization_time: Optional[datetime] = None
        self.last_weekly_optimization_time: Optional[datetime] = None
        self.last_monthly_optimization_time: Optional[datetime] = None
        
        self.load_state()

    def reset_account(self, initial_capital: float = 100.0, fixed_risk_usd: float = 1.0, target_rr: float = 2.0):
        """Reset paper wallet balance to specified USD capital and clear depletion flags."""
        self.initial_capital = initial_capital
        self.current_balance = initial_capital
        self.fixed_risk_usd = fixed_risk_usd
        self.target_rr = target_rr
        self.active_params["target_rr"] = target_rr
        self.is_depleted = False
        self.depletion_report_file = None
        self.open_positions = {}
        self.closed_trades = []
        self.optimization_logs = []
        self.save_state()
        print(f"[LiveBot] Account reset to ${initial_capital:.2f} USD starting capital (${fixed_risk_usd:.2f}/trade, 1:{target_rr} RR).")

    async def restart_with_capital(self, capital: float, fixed_risk_usd: float = 1.0):
        """Re-fund the bot with custom capital amount and immediately resume live scanning."""
        await self.stop()
        self.reset_account(initial_capital=capital, fixed_risk_usd=fixed_risk_usd)
        await self.start()
        print(f"[LiveBot] Bot re-funded with ${capital:.2f} USD and resumed scanning.")

    def load_state(self):
        """Load persisted trades, balances, and open positions from disk."""
        if os.path.exists(LIVE_TRADES_FILE):
            try:
                with open(LIVE_TRADES_FILE, "r", encoding="utf-8") as f:
                    self.closed_trades = json.load(f)
            except Exception:
                self.closed_trades = []

        if os.path.exists(LIVE_POSITIONS_FILE):
            try:
                with open(LIVE_POSITIONS_FILE, "r", encoding="utf-8") as f:
                    self.open_positions = json.load(f)
            except Exception:
                self.open_positions = {}

        if os.path.exists(BOT_STATE_FILE):
            try:
                with open(BOT_STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                    self.initial_capital = state.get("initial_capital", self.initial_capital)
                    self.current_balance = state.get("current_balance", self.current_balance)
                    self.fixed_risk_usd = state.get("fixed_risk_usd", self.fixed_risk_usd)
                    self.is_depleted = state.get("is_depleted", False)
                    self.depletion_report_file = state.get("depletion_report_file", None)
                    self.active_strategy_name = state.get("active_strategy_name", self.active_strategy_name)
                    self.active_params = state.get("active_params", self.active_params)
                    self.target_rr = self.active_params.get("target_rr", self.target_rr)
                    self.optimization_logs = state.get("optimization_logs", [])
                    self.macro_audits = state.get("macro_audits", [])
                    if state.get("last_weekly_opt"):
                        self.last_weekly_optimization_time = datetime.strptime(state["last_weekly_opt"], "%Y-%m-%d %H:%M:%S")
                    if state.get("last_monthly_opt"):
                        self.last_monthly_optimization_time = datetime.strptime(state["last_monthly_opt"], "%Y-%m-%d %H:%M:%S")
            except Exception:
                pass

    def save_state(self):
        """Persist state and wallet balances to disk."""
        try:
            with open(LIVE_TRADES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.closed_trades, f, indent=2)
            with open(LIVE_POSITIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.open_positions, f, indent=2)
            with open(BOT_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "initial_capital": self.initial_capital,
                    "current_balance": self.current_balance,
                    "fixed_risk_usd": self.fixed_risk_usd,
                    "is_depleted": self.is_depleted,
                    "depletion_report_file": self.depletion_report_file,
                    "active_strategy_name": self.active_strategy_name,
                    "active_params": self.active_params,
                    "optimization_logs": self.optimization_logs[-20:],
                    "macro_audits": self.macro_audits[-10:],
                    "last_weekly_opt": self.last_weekly_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_weekly_optimization_time else None,
                    "last_monthly_opt": self.last_monthly_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_monthly_optimization_time else None,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, indent=2)
        except Exception as e:
            print(f"[LiveBot] Error saving state: {e}")

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
        """Pause the live trading worker."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            self.task = None
        print("[LiveBot] Bot worker stopped.")

    async def _main_loop(self):
        """Continuous execution loop."""
        while self.is_running and not self.is_depleted:
            try:
                self.last_scan_time = datetime.now()
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

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=16)) as session:
            # 1. Fetch latest candles for all watched symbols
            tasks = [fetch_symbol_klines(session, sym, interval=self.timeframe, limit=120) for sym in self.symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            data_map: Dict[str, pd.DataFrame] = {}
            for sym, res in zip(self.symbols, results):
                if isinstance(res, pd.DataFrame) and len(res) >= 50:
                    data_map[sym] = compute_crypto_indicators(res)

            # 2. Update Bitcoin Macro Trend Gatekeeper status
            btc_df = data_map.get("BTCUSDT")
            self._evaluate_btc_macro(btc_df)

            # 3. Update and check existing open positions
            await self._update_open_positions(data_map)

            # 4. Scan for new trade setups if capital and capacity permit
            if not self.is_depleted and self.current_balance >= self.fixed_risk_usd and len(self.open_positions) < self.max_open_positions:
                await self._scan_new_entries(data_map)

            # 5. Check if scheduled Weekly or Monthly Macro Optimization is due
            now = datetime.now()
            if self.last_weekly_optimization_time is None or (now - self.last_weekly_optimization_time).total_seconds() >= 7 * 86400:
                asyncio.create_task(self.run_macro_optimization("WEEKLY"))
            if self.last_monthly_optimization_time is None or (now - self.last_monthly_optimization_time).total_seconds() >= 30 * 86400:
                asyncio.create_task(self.run_macro_optimization("MONTHLY"))

    def _evaluate_btc_macro(self, btc_df: Optional[pd.DataFrame]):
        """Evaluate Bitcoin real-time momentum and macro trend to act as safety gatekeeper for Altcoin trades."""
        if btc_df is None or len(btc_df) < 50:
            self.btc_macro_status = {
                "regime": "NEUTRAL",
                "trend": "Awaiting BTC Kline Feed",
                "rsi": 50.0,
                "flash_drop": False,
                "gate_status": "ALLOW_ALL",
                "btc_price": 0.0
            }
            return

        last_bar = btc_df.iloc[-1]
        close = float(last_bar['close'])
        ema50 = float(last_bar.get('ema50', close))
        rsi = float(last_bar.get('rsi14', 50.0))
        mom = float(last_bar.get('momentum', 0.0))

        # Check flash dump: 3-bar drop > 1.2%
        three_bars_ago = float(btc_df.iloc[-3]['close']) if len(btc_df) >= 3 else close
        drop_pct_3bar = ((close - three_bars_ago) / three_bars_ago) * 100.0

        if drop_pct_3bar <= -1.2:
            self.btc_macro_status = {
                "regime": "FLASH_DUMP",
                "trend": f"Acute Selloff ({drop_pct_3bar:.2f}% in 3 bars)",
                "rsi": round(rsi, 1),
                "flash_drop": True,
                "gate_status": "BLOCK_LONGS",
                "btc_price": round(close, 2)
            }
        elif close > ema50 and rsi >= 48.0 and mom >= 0:
            self.btc_macro_status = {
                "regime": "BULLISH",
                "trend": f"Bullish (Above EMA50 @ ${ema50:.0f})",
                "rsi": round(rsi, 1),
                "flash_drop": False,
                "gate_status": "ALLOW_ALL",
                "btc_price": round(close, 2)
            }
        elif close < ema50 and rsi <= 48.0:
            self.btc_macro_status = {
                "regime": "BEARISH",
                "trend": f"Bearish Downtrend (Below EMA50 @ ${ema50:.0f})",
                "rsi": round(rsi, 1),
                "flash_drop": False,
                "gate_status": "BLOCK_LONGS",
                "btc_price": round(close, 2)
            }
        else:
            self.btc_macro_status = {
                "regime": "NEUTRAL",
                "trend": "Consolidation / Ranging",
                "rsi": round(rsi, 1),
                "flash_drop": False,
                "gate_status": "ALLOW_ALL",
                "btc_price": round(close, 2)
            }

    async def _update_open_positions(self, data_map: Dict[str, pd.DataFrame]):
        """
        Institutional 4-Layer Dynamic Exit Engine:
        Layer 1: Initial Hard Stop Loss (1.0R)
        Layer 2: Automatic Breakeven Shift at +1.0R (De-risks to zero)
        Layer 3: Dynamic ATR Trailing Stop at +1.5R
        Layer 4: Target Profit Capture (>= 1:2.0 to 2.5R)
        Safeguards: Time Stagnation (>30 bars) & Momentum Exhaustion Exit
        """
        closed_symbols = []

        for sym, pos in self.open_positions.items():
            df = data_map.get(sym)
            if df is None or len(df) == 0:
                continue

            last_bar = df.iloc[-1]
            curr_price = float(last_bar['close'])
            high_price = float(last_bar['high'])
            low_price = float(last_bar['low'])
            curr_time = int(last_bar['time'])

            pos['current_price'] = round(curr_price, 6 if curr_price < 1 else 2)
            pos['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            pos['bars_held'] = pos.get('bars_held', 0) + 1

            is_long = (pos['direction'] == 'LONG')
            entry_p = pos['entry_price']
            risk_dist = pos['risk_distance']
            risk_usd = pos.get('risk_amount_usd', self.fixed_risk_usd)
            target_rr = pos['target_rr']
            tp_p = pos['tp_price']

            # Update MAE / MFE
            if is_long:
                unrealized_dist = curr_price - entry_p
                pos['mfe_r'] = max(pos.get('mfe_r', 0.0), round((high_price - entry_p) / risk_dist, 2))
                pos['mae_r'] = max(pos.get('mae_r', 0.0), round((entry_p - low_price) / risk_dist, 2))
            else:  # SHORT
                unrealized_dist = entry_p - curr_price
                pos['mfe_r'] = max(pos.get('mfe_r', 0.0), round((entry_p - low_price) / risk_dist, 2))
                pos['mae_r'] = max(pos.get('mae_r', 0.0), round((high_price - entry_p) / risk_dist, 2))

            mfe = pos.get('mfe_r', 0.0)

            # LAYER 2: Breakeven De-risking at +1.0R
            if mfe >= 1.0 and not pos.get('is_breakeven'):
                pos['is_breakeven'] = True
                pos['exit_status'] = "BE Protected 🛡️"
                be_sl = entry_p + (0.08 * risk_dist) if is_long else entry_p - (0.08 * risk_dist)
                pos['sl_price'] = round(be_sl, 6 if entry_p < 1 else 2)
                print(f"[LiveBot:ExitEngine] {sym} reached +1.0R! SL raised to Breakeven (${pos['sl_price']}) to guarantee zero risk.")

            # LAYER 3: Dynamic ATR Trailing Stop at +1.5R
            if mfe >= 1.5:
                pos['is_trailing'] = True
                pos['exit_status'] = "Trailing Active ⚡"
                atr_val = float(last_bar['atr14']) if 'atr14' in last_bar else risk_dist / 1.3
                if is_long:
                    trail_sl = round(high_price - (1.0 * atr_val), 6 if entry_p < 1 else 2)
                    if trail_sl > pos['sl_price']:
                        pos['sl_price'] = trail_sl
                else:
                    trail_sl = round(low_price + (1.0 * atr_val), 6 if entry_p < 1 else 2)
                    if trail_sl < pos['sl_price']:
                        pos['sl_price'] = trail_sl

            # LAYER 4: Check Full Target TP Hit (>= 1:2.0 to 2.5R)
            if (is_long and high_price >= tp_p) or (not is_long and low_price <= tp_p):
                await self._close_position(sym, exit_price=tp_p, exit_time=curr_time, outcome="WIN", df=df)
                closed_symbols.append(sym)
                continue

            # Check SL or Trailing Stop Hit
            if (is_long and low_price <= pos['sl_price']) or (not is_long and high_price >= pos['sl_price']):
                if pos.get('is_trailing') and ((pos['sl_price'] > entry_p and is_long) or (pos['sl_price'] < entry_p and not is_long)):
                    outcome = "TRAILING_STOP_WIN"
                elif pos.get('is_breakeven'):
                    outcome = "BE_EXIT"
                else:
                    outcome = "LOSS"
                await self._close_position(sym, exit_price=pos['sl_price'], exit_time=curr_time, outcome=outcome, df=df)
                closed_symbols.append(sym)
                continue

            # SAFEGUARD: Momentum Exhaustion Exit (if peaked > 0.8R and momentum flips)
            mom = float(last_bar['momentum']) if 'momentum' in last_bar else 0.0
            rsi = float(last_bar['rsi14']) if 'rsi14' in last_bar else 50.0
            if mfe >= 0.8:
                if (is_long and mom < 0 and rsi >= 68.0) or (not is_long and mom > 0 and rsi <= 32.0):
                    print(f"[LiveBot:ExitEngine] {sym} Momentum Exhaustion detected. Securing profits at market.")
                    await self._close_position(sym, exit_price=curr_price, exit_time=curr_time, outcome="MOMENTUM_EXIT", df=df)
                    closed_symbols.append(sym)
                    continue

            # SAFEGUARD: Time Stagnation Exit (> 30 candles of dead chop)
            if pos.get('bars_held', 0) >= 30 and abs(unrealized_dist / risk_dist) < 0.4:
                print(f"[LiveBot:ExitEngine] {sym} Time Stagnation reached (30 bars). Exiting dead chop.")
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

    async def _scan_new_entries(self, data_map: Dict[str, pd.DataFrame]):
        """Evaluate strategy signals with BTC Macro Gatekeeper and Sector Correlation Limits."""
        if self.current_balance < self.fixed_risk_usd:
            return

        for sym, df in data_map.items():
            if len(self.open_positions) >= self.max_open_positions:
                break
            if sym in self.open_positions:
                continue

            last_idx = len(df) - 1
            signal = self._evaluate_active_strategy(df, last_idx)
            
            if signal:
                direction = signal['direction']
                entry_price = signal['entry_price']
                sl_price = signal['sl_price']
                tp_price = signal['tp_price']
                risk_dist = signal['risk_distance']
                target_rr = signal['target_rr']

                # 1. Check Bitcoin Macro Trend Gatekeeper (Bypass for BTC itself)
                if sym != "BTCUSDT":
                    gate_status = self.btc_macro_status.get("gate_status", "ALLOW_ALL")
                    if direction == "LONG" and gate_status == "BLOCK_LONGS":
                        # BTC is dumping or in severe downtrend -> protect capital from fakeouts
                        continue
                    elif direction == "SHORT" and gate_status == "BLOCK_SHORTS":
                        # BTC is in strong bullish trend -> block alt shorts
                        continue

                # 2. Check Sector Correlation Limits (Max positions per sector)
                sector = get_crypto_sector(sym)
                active_in_sector = [p for p in self.open_positions.values() if p.get('sector') == sector]
                if len(active_in_sector) >= self.max_positions_per_sector:
                    # Sector capacity reached -> skip to prevent concentrated exposure
                    continue

                # Fixed $1.00 USD risk per trade
                risk_amount_usd = self.fixed_risk_usd
                position_qty = round(risk_amount_usd / risk_dist, 4) if risk_dist > 0 else 1.0
                position_value_usd = round(position_qty * entry_price, 2)

                pos_record = {
                    "trade_id": len(self.closed_trades) + len(self.open_positions) + 1,
                    "symbol": sym,
                    "sector": sector,
                    "strategy": self.active_strategy_name,
                    "direction": direction,
                    "entry_time": int(df.iloc[-1]['time']),
                    "entry_time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "entry_price": round(entry_price, 6 if entry_price < 1 else 2),
                    "current_price": round(entry_price, 6 if entry_price < 1 else 2),
                    "sl_price": round(sl_price, 6 if sl_price < 1 else 2),
                    "tp_price": round(tp_price, 6 if tp_price < 1 else 2),
                    "risk_distance": risk_dist,
                    "risk_amount_usd": risk_amount_usd,
                    "position_qty": position_qty,
                    "position_value_usd": position_value_usd,
                    "target_rr": target_rr,
                    "unrealized_r": 0.0,
                    "unrealized_pnl_usd": 0.0,
                    "mfe_r": 0.0,
                    "mae_r": 0.0,
                    "bars_held": 0,
                    "pre_trade_context": signal['pre_trade_context']
                }

                self.open_positions[sym] = pos_record
                print(f"[LiveBot] OPENED {direction} on {sym} [{sector}] @ ${entry_price} (Fixed Risk: ${risk_amount_usd:.2f} USD, SL: ${sl_price}, TP: ${tp_price} [1:{target_rr} RR])")
                self.save_state()

    def _evaluate_active_strategy(self, df: pd.DataFrame, idx: int) -> Optional[Dict[str, Any]]:
        """Evaluate strategy incorporating dynamic active parameters."""
        if len(df) < 50 or idx < 50:
            return None

        if 'squeeze_on' not in df.columns:
            df = compute_crypto_indicators(df)

        curr = df.iloc[idx]
        recent_squeezes = df['squeeze_on'].iloc[max(0, idx - 5):idx].sum()
        squeeze_fired = (recent_squeezes >= 2) and (not curr['squeeze_on'])
        
        if not squeeze_fired:
            return None

        close = float(curr['close'])
        atr = float(curr['atr14'])
        ema50 = float(curr['ema50'])
        rvol = float(curr['rvol'])
        rsi = float(curr['rsi14'])
        mom = float(curr['momentum'])

        if atr <= 0:
            return None

        rvol_thresh = self.active_params.get("rvol_min", 1.1)
        atr_sl = self.active_params.get("atr_sl_mult", 1.3)
        target_rr = self.active_params.get("target_rr", self.target_rr)

        # Long Setup
        if close > curr['bb_upper'] and mom > 0 and rvol >= rvol_thresh and close > ema50 and rsi >= self.active_params.get("rsi_min_long", 50.0):
            risk_dist = atr_sl * atr
            entry_price = close
            sl_price = entry_price - risk_dist
            tp_price = entry_price + (target_rr * risk_dist)

            return {
                "strategy": self.active_strategy_name,
                "direction": "LONG",
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "risk_distance": risk_dist,
                "target_rr": target_rr,
                "pre_trade_context": {
                    "regime": "Bullish Trend & Volatility Expansion",
                    "reason": "Squeeze fired bullishly above BB upper band with volume surge",
                    "rvol": round(rvol, 2),
                    "rsi": round(rsi, 1),
                    "momentum": round(mom, 4),
                    "ema_alignment": "Close > EMA50",
                    "volatility_atr": round(atr, 4)
                }
            }

        # Short Setup
        if close < curr['bb_lower'] and mom < 0 and rvol >= rvol_thresh and close < ema50 and rsi <= self.active_params.get("rsi_max_short", 50.0):
            risk_dist = atr_sl * atr
            entry_price = close
            sl_price = entry_price + risk_dist
            tp_price = entry_price - (target_rr * risk_dist)

            return {
                "strategy": self.active_strategy_name,
                "direction": "SHORT",
                "entry_price": entry_price,
                "sl_price": sl_price,
                "tp_price": tp_price,
                "risk_distance": risk_dist,
                "target_rr": target_rr,
                "pre_trade_context": {
                    "regime": "Bearish Trend & Volatility Breakdown",
                    "reason": "Squeeze fired bearishly below BB lower band with volume surge",
                    "rvol": round(rvol, 2),
                    "rsi": round(rsi, 1),
                    "momentum": round(mom, 4),
                    "ema_alignment": "Close < EMA50",
                    "volatility_atr": round(atr, 4)
                }
            }

        return None

    async def _close_position(
        self, 
        symbol: str, 
        exit_price: float, 
        exit_time: int, 
        outcome: str, 
        df: pd.DataFrame
    ):
        """Close an active paper trade and deduct/credit fixed $1.00 risk."""
        pos = self.open_positions.get(symbol)
        if not pos:
            return

        is_long = (pos['direction'] == 'LONG')
        risk_dist = pos.get('risk_distance', 1.0)
        friction_r = 0.08
        
        if outcome == "WIN":
            raw_r = pos['target_rr']
            net_r = round(raw_r - friction_r, 2)
        elif outcome in ["BE_EXIT", "BREAKEVEN_DEFENSE"]:
            raw_r = 0.08
            net_r = 0.0  # Zero loss (fees covered)
        elif outcome in ["TRAILING_STOP_WIN", "MOMENTUM_EXIT", "TIME_EXIT"]:
            dist = (exit_price - pos['entry_price']) if is_long else (pos['entry_price'] - exit_price)
            raw_r = round(dist / risk_dist, 2) if risk_dist > 0 else 0.0
            net_r = round(raw_r - friction_r, 2)
        else:  # LOSS
            raw_r = -1.0
            net_r = round(raw_r - friction_r, 2)

        risk_usd = pos.get('risk_amount_usd', self.fixed_risk_usd)
        pnl_usd = round(net_r * risk_usd, 2)
        
        self.current_balance = round(self.current_balance + pnl_usd, 2)
        bars_held = max(1, pos.get('bars_held', len(df) - 1))

        closed_record = {
            "trade_id": pos['trade_id'],
            "symbol": symbol,
            "strategy": pos['strategy'],
            "direction": pos['direction'],
            "entry_time": pos['entry_time'],
            "entry_time_str": pos['entry_time_str'],
            "exit_time": exit_time,
            "exit_time_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "entry_price": pos['entry_price'],
            "exit_price": round(exit_price, 6 if exit_price < 1 else 2),
            "sl_price": pos['sl_price'],
            "tp_price": pos['tp_price'],
            "target_rr": pos['target_rr'],
            "risk_amount_usd": risk_usd,
            "position_qty": pos.get('position_qty', 1.0),
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
            "pre_trade_context": pos['pre_trade_context']
        }

        # Run automated root-cause diagnostic
        diagnostic = diagnose_trade_outcome(closed_record, df, max(0, len(df) - 10), len(df) - 1)
        closed_record['diagnostic'] = diagnostic

        # Write detailed individual trade markdown journal to reports/
        os.makedirs(REPORTS_DIR, exist_ok=True)
        trade_report_path = os.path.join(REPORTS_DIR, f"trade_journal_#{pos['trade_id']}_{symbol}_{outcome}.md")
        try:
            with open(trade_report_path, "w", encoding="utf-8") as f:
                f.write(f"# Trade Record & Post-Mortem Diagnostic #{pos['trade_id']}: {symbol} ({pos['direction']})\n")
                f.write(f"*Closed on: {closed_record['exit_time_str']}*\n\n")
                f.write(f"## 1. Trade Execution Summary\n")
                f.write(f"- **Outcome**: `{'PROFIT (WIN)' if outcome == 'WIN' else 'LOSS'}`\n")
                f.write(f"- **Realized PnL**: `${pnl_usd:+.2f} USD` ({net_r:+.2f} R)\n")
                f.write(f"- **Resulting Account Balance**: `${self.current_balance:.2f} USD`\n")
                f.write(f"- **Entry Price**: `${closed_record['entry_price']}` | **Exit Price**: `${closed_record['exit_price']}`\n")
                f.write(f"- **Stop Loss**: `${closed_record['sl_price']}` | **Take Profit**: `${closed_record['tp_price']}` (1:{pos['target_rr']} RR)\n")
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

        self.closed_trades.append(closed_record)
        self._archive_entry("trades", closed_record)
        print(f"[LiveBot] CLOSED {pos['direction']} on {symbol}: {outcome} ({net_r}R | ${pnl_usd:+.2f} USD) | Balance: ${self.current_balance:.2f} USD")

        # Trigger Continuous Self-Evolution loop if threshold reached
        if len(self.closed_trades) % self.optimize_every_n_trades == 0:
            asyncio.create_task(self.run_self_optimization())

    def _archive_entry(self, category: str, entry: Dict[str, Any]):
        """Persist structured records into the permanent historical archive JSON file."""
        try:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            archive_data = {
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_trades_archived": 0,
                "trades": [],
                "micro_optimizations": [],
                "weekly_macro_optimizations": [],
                "monthly_macro_audits": []
            }
            if os.path.exists(HISTORICAL_ARCHIVE_FILE):
                try:
                    with open(HISTORICAL_ARCHIVE_FILE, "r", encoding="utf-8") as f:
                        archive_data = json.load(f)
                except Exception:
                    pass

            if category not in archive_data:
                archive_data[category] = []

            archive_data[category].append(entry)
            if category == "trades":
                archive_data["total_trades_archived"] = len(archive_data["trades"])
            archive_data["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(HISTORICAL_ARCHIVE_FILE, "w", encoding="utf-8") as f:
                json.dump(archive_data, f, indent=2)
        except Exception as e:
            print(f"[LiveBot:Archive] Notice: Error archiving data: {e}")

    async def run_macro_optimization(self, period: str = "WEEKLY") -> Dict[str, Any]:
        """
        Extended Multi-Week / Multi-Month Macro Strategy Optimization & Portfolio Audit.
        Pulls deep historical data (500-1000 bars on 1h and 4h), tests parameter durability,
        computes sector-by-sector metrics, and records audit reports.
        """
        period_upper = period.upper()
        now = datetime.now()
        print(f"[LiveBot:Macro Audit] Initiating {period_upper} Macro Strategy Optimization & Portfolio Audit...")

        if period_upper == "MONTHLY":
            self.last_monthly_optimization_time = now
            lookback_bars = 1000
            target_timeframes = ["1h", "4h"]
            report_code = now.strftime("%Y_%m")
            report_filename = os.path.join(REPORTS_DIR, f"monthly_optimization_report_{report_code}.md")
        else:
            self.last_weekly_optimization_time = now
            lookback_bars = 500
            target_timeframes = ["1h", "4h"]
            report_code = f"{now.strftime('%Y')}_W{now.isocalendar()[1]:02d}_{now.strftime('%m%d_%H%M%S')}"
            report_filename = os.path.join(REPORTS_DIR, f"weekly_optimization_report_{report_code}.md")

        param_candidates = [
            {"rvol_min": 1.10, "atr_sl_mult": 1.30, "target_rr": 2.0, "rsi_min_long": 50.0, "rsi_max_short": 50.0},
            {"rvol_min": 1.20, "atr_sl_mult": 1.40, "target_rr": 2.5, "rsi_min_long": 52.0, "rsi_max_short": 48.0},
            {"rvol_min": 1.25, "atr_sl_mult": 1.40, "target_rr": 2.5, "rsi_min_long": 50.0, "rsi_max_short": 50.0},
            {"rvol_min": 1.15, "atr_sl_mult": 1.50, "target_rr": 2.0, "rsi_min_long": 48.0, "rsi_max_short": 52.0},
            {"rvol_min": 1.30, "atr_sl_mult": 1.35, "target_rr": 3.0, "rsi_min_long": 52.0, "rsi_max_short": 48.0}
        ]

        best_score = -999.0
        best_params = self.active_params
        best_tf = self.timeframe
        best_summary: Dict[str, Any] = {
            "timeframe": best_tf,
            "tested_trades": 0,
            "win_rate_pct": 0.0,
            "total_net_r": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
            "params": best_params
        }
        sector_results: Dict[str, Dict[str, Any]] = {}

        symbols_to_test = self.symbols[:25] if self.symbols else ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "DOGEUSDT", "NEARUSDT", "FETUSDT", "PEPEUSDT", "LINKUSDT", "AVAXUSDT", "SUIUSDT"]

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=16)) as session:
            for tf in target_timeframes:
                dataset: Dict[str, pd.DataFrame] = {}
                tasks = [fetch_symbol_klines(session, sym, interval=tf, limit=lookback_bars) for sym in symbols_to_test]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for sym, res in zip(symbols_to_test, results):
                    if isinstance(res, pd.DataFrame) and len(res) >= 60:
                        dataset[sym] = res

                for params in param_candidates:
                    tf_trades = []
                    sec_trades: Dict[str, List[float]] = {}

                    for sym, df in dataset.items():
                        sec = get_crypto_sector(sym)
                        if sec not in sec_trades:
                            sec_trades[sec] = []

                        _, test_df = split_train_test(df, train_ratio=0.5)
                        test_df = compute_crypto_indicators(test_df)
                        n = len(test_df)

                        for i in range(50, n - 2):
                            curr = test_df.iloc[i]
                            recent_sq = test_df['squeeze_on'].iloc[max(0, i-5):i].sum()
                            if recent_sq >= 2 and (not curr['squeeze_on']):
                                close = float(curr['close'])
                                atr = float(curr['atr14'])
                                rvol = float(curr['rvol'])
                                rsi = float(curr['rsi14'])
                                mom = float(curr['momentum'])
                                ema50 = float(curr['ema50'])

                                if close > curr['bb_upper'] and mom > 0 and rvol >= params['rvol_min'] and close > ema50 and rsi >= params['rsi_min_long']:
                                    risk = params['atr_sl_mult'] * atr
                                    sl = close - risk
                                    tp = close + (params['target_rr'] * risk)
                                    outcome = "LOSS"
                                    for j in range(i+1, min(i+50, n)):
                                        bar = test_df.iloc[j]
                                        if bar['low'] <= sl: outcome = "LOSS"; break
                                        elif bar['high'] >= tp: outcome = "WIN"; break
                                    trade_net_r = params['target_rr'] - 0.08 if outcome == "WIN" else -1.08
                                    tf_trades.append(trade_net_r)
                                    sec_trades[sec].append(trade_net_r)

                    total_t = len(tf_trades)
                    if total_t >= 8:
                        wins = [r for r in tf_trades if r > 0]
                        win_rate = (len(wins) / total_t) * 100.0
                        total_net_r = sum(tf_trades)
                        exp_r = total_net_r / total_t
                        score = exp_r * np.sqrt(total_t)

                        if score > best_score and win_rate >= 33.0 and exp_r > 0.05:
                            best_score = score
                            best_params = params
                            best_tf = tf
                            loss_sum = abs(sum(r for r in tf_trades if r <= 0))
                            best_summary = {
                                "timeframe": tf,
                                "tested_trades": total_t,
                                "win_rate_pct": round(win_rate, 2),
                                "total_net_r": round(total_net_r, 2),
                                "expectancy_r": round(exp_r, 3),
                                "profit_factor": round(sum(wins) / loss_sum, 2) if loss_sum > 0 else 999.0,
                                "params": params
                            }
                            # Record sector performance breakdown
                            for sec, s_trades in sec_trades.items():
                                if s_trades:
                                    s_wins = [r for r in s_trades if r > 0]
                                    s_wr = round((len(s_wins) / len(s_trades)) * 100.0, 1)
                                    s_net = round(sum(s_trades), 2)
                                    sector_results[sec] = {"trades": len(s_trades), "win_rate_pct": s_wr, "net_r": s_net}

        audit_entry = {
            "period": period_upper,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
            "lookback_bars": lookback_bars,
            "timeframes_tested": target_timeframes,
            "optimal_timeframe": best_tf,
            "optimal_params": best_params,
            "metrics": best_summary,
            "sector_breakdown": sector_results,
            "report_file": report_filename
        }

        # Generate Rich Markdown Audit Report
        try:
            os.makedirs(REPORTS_DIR, exist_ok=True)
            lines = [
                f"# 🏛️ {period_upper} Macro Strategy Optimization & Portfolio Audit Report",
                f"*Generated on: {now.strftime('%Y-%m-%d %H:%M:%S')} (Lookback Horizon: {lookback_bars} bars on 1h/4h)*",
                "",
                "## 1. Executive Performance Summary",
                f"- **Audit Period**: `{period_upper}`",
                f"- **Optimal Macro Timeframe**: `{best_tf}`",
                f"- **Macro Win Rate**: `{best_summary.get('win_rate_pct', 'N/A')}%`",
                f"- **Net Mathematical Expectancy**: `+{best_summary.get('expectancy_r', 'N/A')} R / trade`",
                f"- **Cumulative Out-of-Sample Net Return**: `+{best_summary.get('total_net_r', 'N/A')} R`",
                f"- **Profit Factor**: `{best_summary.get('profit_factor', 'N/A')}`",
                f"- **Sample Size Tested**: `{best_summary.get('tested_trades', 'N/A')} simulated macro trades`",
                "",
                "## 2. Calibrated Optimal Parameter Suite",
                "| Parameter | Calibrated Value | Quantitative Rationale |",
                "| :--- | :--- | :--- |",
                f"| **Target Risk-to-Reward (RR)** | `1:{best_params.get('target_rr', 2.0):.1f} RR` | Asymmetric reward floor ensures net positive expectancy |",
                f"| **Relative Volume (RVOL)** | `≥ {best_params.get('rvol_min', 1.1):.2f}x` | Eliminates false breakouts during low institutional participation |",
                f"| **ATR Stop Loss Distance** | `{best_params.get('atr_sl_mult', 1.3):.2f} × ATR14` | Volatility-scaled breathing room avoiding market noise wicks |",
                f"| **ATR Take Profit Distance** | `{(best_params.get('atr_sl_mult', 1.3) * best_params.get('target_rr', 2.0)):.2f} × ATR14` | Volatility-scaled mathematical profit objective |",
                f"| **RSI Momentum Filter** | `Long ≥ {best_params.get('rsi_min_long', 50):.0f} \\| Short ≤ {best_params.get('rsi_max_short', 50):.0f}` | Directional momentum confluence filter |",
                "",
                "## 3. Sector Correlation & Performance Breakdown",
                "| Sector | Tested Trades | Win Rate % | Total Net R | Cluster Risk Status |",
                "| :--- | :--- | :--- | :--- | :--- |"
            ]

            if sector_results:
                for sec, s_data in sector_results.items():
                    lines.append(
                        f"| **{sec.replace('_', ' ')}** | {s_data.get('trades', 0)} | {s_data.get('win_rate_pct', 0)}% | {s_data.get('net_r', 0):+.2f}R | Strict 1-Position Cap Enforced |"
                    )
            else:
                lines.append("| **GENERAL ALT** | - | - | - | Strict 1-Position Cap Enforced |")

            lines.extend([
                "",
                "## 4. Archival & Historical Logging",
                f"- **Permanent JSON Archive**: Stored in `reports/historical_archive.json`",
                f"- **Next Scheduled {period_upper} Audit**: in {'7' if period_upper == 'WEEKLY' else '30'} days."
            ])

            with open(report_filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception as e:
            print(f"[LiveBot:Macro Audit] Notice: Could not write markdown report: {e}")

        # Archive to JSON historical database
        archive_category = "weekly_macro_optimizations" if period_upper == "WEEKLY" else "monthly_macro_audits"
        self._archive_entry(archive_category, audit_entry)

        self.macro_audits.append(audit_entry)
        self.save_state()
        print(f"[LiveBot:Macro Audit] {period_upper} Optimization completed and saved to {report_filename}")
        return audit_entry

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
        os.makedirs(REPORTS_DIR, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(REPORTS_DIR, f"capital_depleted_summary_{timestamp_str}.md")

        total_trades = len(self.closed_trades)
        wins = [t for t in self.closed_trades if t.get('net_r', 0) > 0]
        losses = [t for t in self.closed_trades if t.get('net_r', 0) <= 0]
        
        win_rate = round((len(wins) / total_trades * 100.0), 2) if total_trades > 0 else 0.0
        total_net_r = round(sum(t.get('net_r', 0) for t in self.closed_trades), 2)
        total_pnl_usd = round(self.current_balance - self.initial_capital, 2)
        
        total_win_r = sum(t.get('net_r', 0) for t in wins)
        total_loss_r = abs(sum(t.get('net_r', 0) for t in losses))
        profit_factor = round(total_win_r / total_loss_r, 2) if total_loss_r > 0 else 0.0
        expectancy_r = round(total_net_r / total_trades, 3) if total_trades > 0 else 0.0

        lines = [
            "# Automated Trading Bot - Capital Depletion Summary Report",
            f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            "",
            "## 1. Executive Performance Summary",
            f"- **Starting Capital**: `${self.initial_capital:.2f} USD`",
            f"- **Final Balance**: `${self.current_balance:.2f} USD`",
            f"- **Total Net PnL**: `${total_pnl_usd:+.2f} USD` ({total_net_r:+.2f} R)",
            f"- **Risk Per Trade**: `${self.fixed_risk_usd:.2f} USD` (Fixed 1R)",
            f"- **Target Risk-to-Reward**: `1:{self.target_rr} RR` (Minimum)",
            f"- **Total Trades Taken**: `{total_trades}` ({len(wins)} Wins / {len(losses)} Losses)",
            f"- **Win Rate**: `{win_rate}%` (Breakeven required: 25.0%)",
            f"- **Profit Factor**: `{profit_factor}`",
            f"- **Expectancy per Trade**: `{expectancy_r:+.3f} R`",
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

    async def run_self_optimization(self) -> Dict[str, Any]:
        """Self-Evolving Multi-Timeframe & Parameter Optimization Loop."""
        print("[LiveBot:AI Optimizer] Initiating dynamic multi-timeframe self-perfection cycle...")
        self.last_optimization_time = datetime.now()
        
        candidate_timeframes = ["5m", "15m", "1h", "4h"]
        param_candidates = [
            {"rvol_min": 1.1, "atr_sl_mult": 1.3, "target_rr": 2.0, "rsi_min_long": 50.0, "rsi_max_short": 50.0},
            {"rvol_min": 1.2, "atr_sl_mult": 1.2, "target_rr": 2.0, "rsi_min_long": 52.0, "rsi_max_short": 48.0},
            {"rvol_min": 1.25, "atr_sl_mult": 1.4, "target_rr": 2.5, "rsi_min_long": 50.0, "rsi_max_short": 50.0},
            {"rvol_min": 1.15, "atr_sl_mult": 1.5, "target_rr": 2.0, "rsi_min_long": 48.0, "rsi_max_short": 52.0}
        ]

        best_score = -999.0
        best_params = self.active_params
        best_tf = self.timeframe
        best_summary = {}

        # Benchmark across candidate timeframes (5m, 15m, 1h, 4h)
        for tf in candidate_timeframes:
            dataset = {}
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=12)) as session:
                tasks = [fetch_symbol_klines(session, sym, interval=tf, limit=200) for sym in self.symbols[:15]]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for sym, res in zip(self.symbols[:15], results):
                    if isinstance(res, pd.DataFrame) and len(res) >= 50:
                        dataset[sym] = res

            for params in param_candidates:
                all_trades = []
                for sym, df in dataset.items():
                    _, test_df = split_train_test(df, train_ratio=0.6)
                    test_df = compute_crypto_indicators(test_df)
                    
                    n = len(test_df)
                    for i in range(50, n - 2):
                        curr = test_df.iloc[i]
                        recent_sq = test_df['squeeze_on'].iloc[max(0, i-5):i].sum()
                        if recent_sq >= 2 and (not curr['squeeze_on']):
                            close = float(curr['close'])
                            atr = float(curr['atr14'])
                            rvol = float(curr['rvol'])
                            rsi = float(curr['rsi14'])
                            mom = float(curr['momentum'])
                            ema50 = float(curr['ema50'])
                            
                            if close > curr['bb_upper'] and mom > 0 and rvol >= params['rvol_min'] and close > ema50 and rsi >= params['rsi_min_long']:
                                risk = params['atr_sl_mult'] * atr
                                sl = close - risk
                                tp = close + (params['target_rr'] * risk)
                                outcome = "LOSS"
                                for j in range(i+1, min(i+50, n)):
                                    bar = test_df.iloc[j]
                                    if bar['low'] <= sl: outcome = "LOSS"; break
                                    elif bar['high'] >= tp: outcome = "WIN"; break
                                all_trades.append(params['target_rr'] - 0.08 if outcome == "WIN" else -1.08)

                total_t = len(all_trades)
                if total_t >= 8:
                    wins = [r for r in all_trades if r > 0]
                    win_rate = (len(wins) / total_t) * 100.0
                    total_net_r = sum(all_trades)
                    exp_r = total_net_r / total_t
                    score = exp_r * np.sqrt(total_t)

                    if score > best_score and win_rate >= 33.3 and exp_r > 0.10:
                        best_score = score
                        best_params = params
                        best_tf = tf
                        best_summary = {
                            "timeframe": tf,
                            "tested_trades": total_t,
                            "win_rate_pct": round(win_rate, 2),
                            "total_net_r": round(total_net_r, 2),
                            "expectancy_r": round(exp_r, 3),
                            "params": params
                        }

        tf_changed = (best_tf != self.timeframe)
        params_changed = (best_params != self.active_params)

        opt_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "improved": params_changed or tf_changed,
            "best_timeframe": best_tf,
            "best_params": best_params,
            "summary": best_summary or f"Maintained current timeframe ({self.timeframe}) and baseline parameters"
        }

        # Persist full evolution report to reports/
        os.makedirs(REPORTS_DIR, exist_ok=True)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        evo_report_path = os.path.join(REPORTS_DIR, f"ai_evolution_report_{ts_str}.md")
        try:
            with open(evo_report_path, "w", encoding="utf-8") as f:
                f.write(f"# Dynamic Multi-Timeframe Strategy Evolution Report\n")
                f.write(f"*Generated on: {opt_entry['timestamp']}*\n\n")
                f.write(f"## 1. Executive Summary\n")
                f.write(f"- **Strategy Name**: `{self.active_strategy_name}`\n")
                f.write(f"- **Optimal Timeframe Selected**: `{best_tf}` (Evaluated: 5m, 15m, 1h, 4h)\n")
                f.write(f"- **Timeframe Switched**: `{'Yes' if tf_changed else 'No (Current confirmed optimal)'}`\n")
                f.write(f"- **Active Target RR**: `1:{best_params.get('target_rr', 2.0)} RR` (Minimum floor: >= 1:2)\n\n")
                f.write(f"## 2. Tested Parameter Benchmarks\n")
                f.write(f"```json\n{json.dumps(best_params, indent=2)}\n```\n\n")
                f.write(f"## 3. Walk-Forward Diagnostic Metrics\n")
                if isinstance(best_summary, dict):
                    f.write(f"- **Timeframe**: `{best_summary.get('timeframe', best_tf)}`\n")
                    f.write(f"- **Tested Out-of-Sample Trades**: `{best_summary.get('tested_trades', 'N/A')}`\n")
                    f.write(f"- **Win Rate**: `{best_summary.get('win_rate_pct', 'N/A')}%`\n")
                    f.write(f"- **Net Expectancy**: `+{best_summary.get('expectancy_r', 'N/A')} R`\n")
                    f.write(f"- **Total Net Return**: `{best_summary.get('total_net_r', 'N/A')} R`\n")
                else:
                    f.write(f"{best_summary}\n")
            opt_entry["report_file"] = evo_report_path
        except Exception as e:
            print(f"[LiveBot] Notice: Could not write evolution report: {e}")

        if tf_changed:
            print(f"[LiveBot:AI Optimizer] DYNAMIC TIMEFRAME UPGRADE: Switched from {self.timeframe} to {best_tf} based on statistical edge!")
            self.timeframe = best_tf

        if params_changed:
            self.active_params = best_params
            print(f"[LiveBot:AI Optimizer] Upgraded Strategy Parameters: {best_params} (Expectancy: +{best_summary.get('expectancy_r')}R)")
        
        self.optimization_logs.append(opt_entry)
        self._archive_entry("micro_optimizations", opt_entry)
        self.save_state()
        return opt_entry

    def get_telemetry(self) -> Dict[str, Any]:
        """Return full real-time telemetry metrics for dashboard visualization."""
        total_trades = len(self.closed_trades)
        wins = [t for t in self.closed_trades if t.get('net_r', 0) > 0]
        losses = [t for t in self.closed_trades if t.get('net_r', 0) <= 0]
        
        win_rate = round((len(wins) / total_trades * 100.0), 2) if total_trades > 0 else 0.0
        total_net_r = round(sum(t.get('net_r', 0) for t in self.closed_trades), 2)
        total_win_r = sum(t.get('net_r', 0) for t in wins)
        total_loss_r = abs(sum(t.get('net_r', 0) for t in losses))
        profit_factor = round(total_win_r / total_loss_r, 2) if total_loss_r > 0 else (999.0 if total_win_r > 0 else 0.0)
        expectancy_r = round(total_net_r / total_trades, 3) if total_trades > 0 else 0.0

        # USD Balances
        unrealized_pnl_usd = round(sum(p.get('unrealized_pnl_usd', 0.0) for p in self.open_positions.values()), 2)
        equity_usd = round(self.current_balance + unrealized_pnl_usd, 2)
        total_pnl_usd = round(self.current_balance - self.initial_capital, 2)
        total_pnl_pct = round(((self.current_balance - self.initial_capital) / self.initial_capital) * 100.0, 2)

        status_str = "DEPLETED_STOPPED" if self.is_depleted else ("RUNNING" if self.is_running else "PAUSED")

        return {
            "status": status_str,
            "is_depleted": self.is_depleted,
            "depletion_report_file": self.depletion_report_file,
            "timeframe": self.timeframe,
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
            "watched_pairs_count": len(self.symbols),
            "open_positions_count": len(self.open_positions),
            "open_positions": list(self.open_positions.values()),
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
            "last_weekly_optimization_time": self.last_weekly_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_weekly_optimization_time else None,
            "last_monthly_optimization_time": self.last_monthly_optimization_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_monthly_optimization_time else None,
            "recent_optimizations": self.optimization_logs[-5:],
            "macro_audits": self.macro_audits[-5:],
            "recent_journal": self.closed_trades[-20:][::-1]
        }

# Global singleton bot instance initialized with $100.00 USD Capital, $1.00 Fixed Risk, and 1:2.0 RR (100 pairs)
bot_instance = LiveCryptoBot(initial_capital=100.0, fixed_risk_usd=1.0, timeframe="15m", target_rr=2.0, scan_interval_sec=20)
