import asyncio
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from scanner import compute_indicators, fetch_klines, fetch_top_usdt_pairs
import aiohttp
from execution import EXIT_TIMEFRAME_PROFILES

TIMEFRAME_PROFILES: Dict[str, Dict[str, Any]] = {
    "15m": {
        "name": "15m Intraday",
        "expected_hold_str": "1.5h - 8h",
        "max_holding_bars": 64,       # ~16 hours
        "stagnation_bars": 24,        # ~6 hours
        "cooldown_minutes": 45,       # 3 bars
        "scan_interval_sec": 20,
    },
    "30m": {
        "name": "30m Intraday",
        "expected_hold_str": "3h - 16h",
        "max_holding_bars": 64,       # ~32 hours
        "stagnation_bars": 24,        # ~12 hours
        "cooldown_minutes": 90,       # 3 bars
        "scan_interval_sec": 30,
    },
    "1h": {
        "name": "1h Short Swing",
        "expected_hold_str": "12h - 3d",
        "max_holding_bars": 96,       # 4 days
        "stagnation_bars": 30,        # 30 hours
        "cooldown_minutes": 180,      # 3 hours (3 bars)
        "scan_interval_sec": 45,
    },
    "4h": {
        "name": "4h Macro Swing",
        "expected_hold_str": "2d - 10d",
        "max_holding_bars": 84,       # 14 days
        "stagnation_bars": 24,        # 4 days
        "cooldown_minutes": 720,      # 12 hours (3 bars)
        "scan_interval_sec": 60,
    },
    "1d": {
        "name": "1d Positional Trend",
        "expected_hold_str": "2w - 2mo",
        "max_holding_bars": 60,       # 60 days
        "stagnation_bars": 20,        # 20 days
        "cooldown_minutes": 2880,     # 48 hours (2 bars)
        "scan_interval_sec": 120,
    },
}

for _timeframe, _exit_profile in EXIT_TIMEFRAME_PROFILES.items():
    TIMEFRAME_PROFILES.setdefault(_timeframe, {}).update(_exit_profile)


def _backtest_metrics(trades: List[Dict[str, Any]], target_rr: float) -> Dict[str, Any]:
    from sim_engine import compile_simulation_metrics
    result = compile_simulation_metrics(trades, "Scanner_Squeeze_Reference", target_rr)
    ordered = result["trades"]
    flows = sorted((float(fill["timestamp"]), str(t.get("symbol", "")), int(fill["fill_id"]),
                    float(fill["cash_delta_usd"]) / float(t["risk_amount_usd"]))
                   for t in ordered for fill in t.get("fills", []))
    equity = [0.0]
    for _, _, _, change in flows:
        equity.append(round(equity[-1] + change, 8))
    result.update({
        "wins": result["win_count"], "losses": result["loss_count"],
        "total_r_return": result["total_net_r"],
        "tp1_hit_rate_pct": round(100 * sum(bool(t.get("tp1_hit")) for t in ordered) / len(ordered), 2) if ordered else 0.0,
        "equity_curve": equity,
        "simulation_version": "execution_v2", "execution_model": "conservative_ohlc",
        "strategy_scope": "Scanner reference signals; not validation of the active MTF bot strategy",
    })
    return result


def run_backtest_simulation(
    df: pd.DataFrame,
    target_rr: float = 3.0,
    fee_pct: float = 0.05,
    slippage_pct: float = 0.02,
    timeframe: str = "1h",
) -> Dict[str, Any]:
    """Replay scanner reference signals with the shared fill execution model.

    This endpoint retains its scanner signal rules; its explicitly labeled
    results must not be used as evidence for the active MTF bot strategy.
    """
    from data_loader import completed_candles, interval_seconds
    from execution import create_position, process_bar, close_position, summarize_position
    duration = interval_seconds(timeframe)
    profile = TIMEFRAME_PROFILES.get(timeframe, TIMEFRAME_PROFILES["15m"])
    df = completed_candles(df, timeframe).sort_values("time", kind="stable").reset_index(drop=True)
    df = compute_indicators(df.copy())
    trades = []
    i = 199
    while i < len(df) - 1:
        row = df.iloc[i]
        if row.get("signal") not in ("LONG", "SHORT"):
            i += 1
            continue
        entry_idx = i + 1
        try:
            pos = create_position(row["signal"], float(df.iloc[entry_idx]["open"]),
                                  1.5 * float(row["atr14"]), 1.0, target_rr,
                                  int(df.iloc[entry_idx]["time"]), fee_pct, slippage_pct)
        except (ValueError, TypeError):
            i += 1
            continue
        pos.update({"strategy": "Scanner_Squeeze_Reference", "timeframe": timeframe})
        exit_idx = entry_idx
        for j in range(entry_idx, len(df)):
            bar = df.iloc[j]
            process_bar(pos, bar, timestamp=int(bar["time"]) + duration,
                        completed_bars=j - entry_idx + 1,
                        stagnation_bars=profile["stagnation_bars"],
                        max_holding_bars=profile["max_holding_bars"])
            exit_idx = j
            if pos["closed"]:
                break
        if not pos["closed"]:
            bar = df.iloc[exit_idx]
            close_position(pos, float(bar["close"]), int(bar["time"]) + duration, "WINDOW_END")
        trade = summarize_position(pos)
        trade.update({"trade_num": len(trades) + 1, "tp_target_price": pos["tp_price"]})
        trades.append(trade)
        i = max(i + 1, exit_idx)
    result = _backtest_metrics(trades, target_rr)
    result["cost_model"] = {"version": "fills_v1", "fee_pct": fee_pct, "slippage_pct": slippage_pct}
    return result


async def backtest_symbol(symbol: str, interval: str = "1h", limit: int = 1000,
                          target_rr: float = 2.0) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        df = await fetch_klines(session, symbol, interval=interval, limit=limit)
    if df is None or len(df) < 201:
        return {"error": f"Insufficient completed history for {symbol}: at least 201 bars required"}
    result = run_backtest_simulation(df, target_rr=target_rr, timeframe=interval)
    result.update({"symbol": symbol, "interval": interval, "bars_analyzed": len(df)})
    return result


async def backtest_portfolio(symbols: List[str], interval: str = "1h", limit: int = 500,
                             target_rr: float = 2.0) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as session:
        dfs = await asyncio.gather(*[fetch_klines(session, sym, interval=interval, limit=limit)
                                     for sym in symbols], return_exceptions=True)
    trades = []
    for symbol, df in zip(symbols, dfs):
        if isinstance(df, pd.DataFrame) and len(df) >= 201:
            result = run_backtest_simulation(df, target_rr=target_rr, timeframe=interval)
            for trade in result["trades"]:
                trades.append(dict(trade, symbol=symbol))
    result = _backtest_metrics(trades, target_rr)
    for index, trade in enumerate(result["trades"], 1):
        trade["trade_num"] = index
    result.update({"symbol": "ALL (Portfolio)", "interval": interval,
                   "cost_model": {"version": "fills_v1", "fee_pct": 0.05, "slippage_pct": 0.02}})
    return result
