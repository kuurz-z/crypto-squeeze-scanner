import asyncio
import pandas as pd
import numpy as np
from typing import Dict, Any, List
from scanner import compute_indicators, fetch_klines, fetch_top_usdt_pairs
import aiohttp

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

def run_backtest_simulation(
    df: pd.DataFrame, 
    target_rr: float = 3.0, 
    fee_pct: float = 0.05,
    slippage_pct: float = 0.02,
    timeframe: str = "1h"
) -> Dict[str, Any]:
    """
    Simulate historical trading on calculated signals with realistic fee and slippage friction and timeframe-aware holding horizons.
    
    target_rr: Target Risk-to-Reward multiple (e.g. 1.0, 2.0, 3.0, 4.0)
    fee_pct: Exchange taker fee percentage per trade leg (0.05% = 0.0005)
    slippage_pct: Slippage estimate per trade leg
    timeframe: Active candle timeframe (e.g. 15m, 30m, 1h, 4h, 1d)
    """
    tf_profile = TIMEFRAME_PROFILES.get(timeframe, TIMEFRAME_PROFILES["1h"])
    max_holding_bars = tf_profile.get("max_holding_bars", 96)
    stagnation_bars = tf_profile.get("stagnation_bars", 30)

    df = compute_indicators(df)
    trades: List[Dict[str, Any]] = []
    
    i = 50  # Start after indicators stabilize
    n = len(df)
    
    while i < n - 1:
        row = df.iloc[i]
        sig = row['signal']
        
        if sig in ['LONG', 'SHORT']:
            entry_time = int(row['time'])
            entry_price = float(row['close'])
            atr = float(row['atr14'])
            risk_dist = 1.5 * atr
            
            if risk_dist <= 0:
                i += 1
                continue
                
            is_long = (sig == 'LONG')
            sl_price = entry_price - risk_dist if is_long else entry_price + risk_dist
            tp1_price = entry_price + (1.0 * risk_dist) if is_long else entry_price - (1.0 * risk_dist)
            tp_target_price = entry_price + (target_rr * risk_dist) if is_long else entry_price - (target_rr * risk_dist)
            
            # Forward simulate future candles
            outcome = "OPEN"
            exit_price = entry_price
            exit_time = entry_time
            bars_held = 0
            tp1_hit = False
            realized_r = 0.0
            
            for j in range(i + 1, min(i + max_holding_bars + 1, n)):
                bars_held += 1
                curr_bar = df.iloc[j]
                bar_high = float(curr_bar['high'])
                bar_low = float(curr_bar['low'])
                bar_close = float(curr_bar['close'])
                bar_time = int(curr_bar['time'])
                
                if is_long:
                    # Check if TP1 hit
                    if bar_high >= tp1_price:
                        tp1_hit = True
                    
                    # Check SL hit
                    if bar_low <= sl_price:
                        outcome = "LOSS"
                        exit_price = sl_price
                        exit_time = bar_time
                        realized_r = -1.0
                        break
                    # Check Target TP hit
                    elif bar_high >= tp_target_price:
                        outcome = "WIN"
                        exit_price = tp_target_price
                        exit_time = bar_time
                        realized_r = target_rr
                        break
                    # Check Stagnation Exit
                    elif bars_held >= stagnation_bars and abs((bar_close - entry_price) / risk_dist) < 0.4:
                        outcome = "TIME_EXIT"
                        exit_price = bar_close
                        exit_time = bar_time
                        pnl_dist = bar_close - entry_price
                        realized_r = round(pnl_dist / risk_dist, 2)
                        break
                else:  # SHORT
                    if bar_low <= tp1_price:
                        tp1_hit = True
                        
                    if bar_high >= sl_price:
                        outcome = "LOSS"
                        exit_price = sl_price
                        exit_time = bar_time
                        realized_r = -1.0
                        break
                    elif bar_low <= tp_target_price:
                        outcome = "WIN"
                        exit_price = tp_target_price
                        exit_time = bar_time
                        realized_r = target_rr
                        break
                    # Check Stagnation Exit
                    elif bars_held >= stagnation_bars and abs((entry_price - bar_close) / risk_dist) < 0.4:
                        outcome = "TIME_EXIT"
                        exit_price = bar_close
                        exit_time = bar_time
                        pnl_dist = entry_price - bar_close
                        realized_r = round(pnl_dist / risk_dist, 2)
                        break
            
            if outcome == "OPEN":
                # Closed at end of dataset or max holding period
                last_bar = df.iloc[min(i + max_holding_bars, n - 1)]
                exit_price = float(last_bar['close'])
                exit_time = int(last_bar['time'])
                pnl_dist = (exit_price - entry_price) if is_long else (entry_price - exit_price)
                realized_r = round(pnl_dist / risk_dist, 2)
                outcome = "WIN" if realized_r > 0 else "LOSS"
            
            # Apply roundtrip fees and slippage impact on R
            friction_cost_pct = (fee_pct + slippage_pct) * 2.0
            risk_pct = (risk_dist / entry_price) * 100.0
            friction_r = friction_cost_pct / risk_pct if risk_pct > 0 else 0.05
            net_realized_r = round(realized_r - friction_r, 2)
            
            trades.append({
                "trade_num": len(trades) + 1,
                "direction": sig,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": round(entry_price, 6 if entry_price < 1 else 2),
                "exit_price": round(exit_price, 6 if exit_price < 1 else 2),
                "sl_price": round(sl_price, 6 if sl_price < 1 else 2),
                "tp_target_price": round(tp_target_price, 6 if tp_target_price < 1 else 2),
                "outcome": outcome,
                "tp1_hit": tp1_hit,
                "raw_r": realized_r,
                "net_r": net_realized_r,
                "bars_held": bars_held
            })
            
            # Advance index to avoid overlapping triggers in the same trade cycle
            i += max(1, bars_held)
        else:
            i += 1

    # Statistical Summary Calculation
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "tp1_hit_rate_pct": 0.0,
            "total_r_return": 0.0,
            "profit_factor": 0.0,
            "expectancy_r": 0.0,
            "max_drawdown_r": 0.0,
            "trades": []
        }
        
    wins = [t for t in trades if t['net_r'] > 0]
    losses = [t for t in trades if t['net_r'] <= 0]
    tp1_hits = [t for t in trades if t['tp1_hit']]
    
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = (win_count / total_trades) * 100.0
    tp1_rate = (len(tp1_hits) / total_trades) * 100.0
    
    gross_profit_r = sum(t['net_r'] for t in wins)
    gross_loss_r = abs(sum(t['net_r'] for t in losses))
    profit_factor = (gross_profit_r / gross_loss_r) if gross_loss_r > 0 else (gross_profit_r if gross_profit_r > 0 else 0.0)
    
    total_r = sum(t['net_r'] for t in trades)
    expectancy = total_r / total_trades
    
    # Calculate Max Drawdown in R
    cum_r = 0.0
    peak_r = 0.0
    max_dd_r = 0.0
    equity_curve = [0.0]
    
    for t in trades:
        cum_r += t['net_r']
        equity_curve.append(round(cum_r, 2))
        if cum_r > peak_r:
            peak_r = cum_r
        dd = peak_r - cum_r
        if dd > max_dd_r:
            max_dd_r = dd
            
    return {
        "total_trades": total_trades,
        "wins": win_count,
        "losses": loss_count,
        "win_rate_pct": round(win_rate, 2),
        "tp1_hit_rate_pct": round(tp1_rate, 2),
        "total_r_return": round(total_r, 2),
        "profit_factor": round(profit_factor, 2),
        "expectancy_r": round(expectancy, 2),
        "max_drawdown_r": round(max_dd_r, 2),
        "equity_curve": equity_curve,
        "trades": trades
    }

async def backtest_symbol(symbol: str, interval: str = "1h", limit: int = 1000, target_rr: float = 2.0) -> Dict[str, Any]:
    """Fetch extended historical candles and execute full backtest simulation."""
    async with aiohttp.ClientSession() as session:
        df = await fetch_klines(session, symbol, interval=interval, limit=limit)
        if df is None or len(df) < 60:
            return {"error": f"Insufficient historical data for {symbol}"}
            
        results = run_backtest_simulation(df, target_rr=target_rr, timeframe=interval)
        results["symbol"] = symbol
        results["interval"] = interval
        results["bars_analyzed"] = len(df)
        return results

async def backtest_portfolio(symbols: List[str], interval: str = "1h", limit: int = 500, target_rr: float = 2.0) -> Dict[str, Any]:
    """Simulate strategy across an entire portfolio of symbols simultaneously."""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_klines(session, sym, interval=interval, limit=limit) for sym in symbols]
        dfs = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_trades = []
        for sym, df in zip(symbols, dfs):
            if isinstance(df, pd.DataFrame) and len(df) >= 60:
                res = run_backtest_simulation(df, target_rr=target_rr, timeframe=interval)
                for t in res.get("trades", []):
                    t_copy = dict(t)
                    t_copy["symbol"] = sym
                    all_trades.append(t_copy)
                    
        all_trades.sort(key=lambda x: x['entry_time'])
        for idx, t in enumerate(all_trades, 1):
            t["trade_num"] = idx
            
        total_trades = len(all_trades)
        if total_trades == 0:
            return {
                "symbol": "ALL (Portfolio)",
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate_pct": 0.0,
                "tp1_hit_rate_pct": 0.0,
                "total_r_return": 0.0,
                "profit_factor": 0.0,
                "expectancy_r": 0.0,
                "max_drawdown_r": 0.0,
                "equity_curve": [0.0],
                "trades": []
            }
            
        wins = [t for t in all_trades if t['net_r'] > 0]
        losses = [t for t in all_trades if t['net_r'] <= 0]
        tp1_hits = [t for t in all_trades if t.get('tp1_hit', False)]
        
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades) * 100.0
        tp1_rate = (len(tp1_hits) / total_trades) * 100.0
        
        gross_profit_r = sum(t['net_r'] for t in wins)
        gross_loss_r = abs(sum(t['net_r'] for t in losses))
        profit_factor = (gross_profit_r / gross_loss_r) if gross_loss_r > 0 else (gross_profit_r if gross_profit_r > 0 else 0.0)
        
        total_r = sum(t['net_r'] for t in all_trades)
        expectancy = total_r / total_trades
        
        cum_r = 0.0
        peak_r = 0.0
        max_dd_r = 0.0
        equity_curve = [0.0]
        
        for t in all_trades:
            cum_r += t['net_r']
            equity_curve.append(round(cum_r, 2))
            if cum_r > peak_r:
                peak_r = cum_r
            dd = peak_r - cum_r
            if dd > max_dd_r:
                max_dd_r = dd
                
        return {
            "symbol": "ALL (Portfolio)",
            "total_trades": total_trades,
            "wins": win_count,
            "losses": loss_count,
            "win_rate_pct": round(win_rate, 2),
            "tp1_hit_rate_pct": round(tp1_rate, 2),
            "total_r_return": round(total_r, 2),
            "profit_factor": round(profit_factor, 2),
            "expectancy_r": round(expectancy, 2),
            "max_drawdown_r": round(max_dd_r, 2),
            "equity_curve": equity_curve,
            "trades": all_trades
        }

