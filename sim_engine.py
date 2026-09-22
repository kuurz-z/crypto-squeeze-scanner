import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional
from strategies import compute_crypto_indicators, StrategyBase, AVAILABLE_STRATEGIES

def diagnose_trade_outcome(
    trade: Dict[str, Any], 
    df: pd.DataFrame, 
    entry_idx: int, 
    exit_idx: int
) -> Dict[str, Any]:
    """
    Perform deep algorithmic post-trade root-cause analysis on why a trade succeeded or failed.
    """
    if trade.get("schema_version") == 2:
        reason = trade.get("exit_reason", "UNKNOWN")
        return {
            "summary": f"Modeled {reason.lower().replace('_', ' ')} exit; net {trade.get('net_r', 0):+.4f}R after recorded fill costs.",
            "catalyst_type": reason,
            "key_factors": [
                f"Recorded favorable excursion: {trade.get('mfe_r', 0):.3f}R",
                f"Recorded adverse excursion: {trade.get('mae_r', 0):.3f}R",
                f"Fees: ${trade.get('fees_usd', 0):.6f}; slippage is included in fill prices",
            ],
            "risk_management_quality": "Measured execution; market cause not inferred",
        }
    outcome = trade['outcome']
    direction = trade['direction']
    bars_held = trade['bars_held']
    mae_r = trade['mae_r']
    mfe_r = trade['mfe_r']
    strategy_name = trade['strategy']
    
    # Calculate price action behavior during trade duration
    vol_surge = False
    if df is not None and len(df) > 0 and entry_idx >= 0 and exit_idx >= entry_idx:
        trade_slice = df.iloc[entry_idx:exit_idx + 1]
        if len(trade_slice) > 0 and 'volume' in trade_slice.columns:
            vol_surge = (trade_slice['volume'].max() / (trade_slice['volume'].mean() + 1e-6)) > 1.8
    
    analysis = {
        "summary": "",
        "catalyst_type": "",
        "key_factors": [],
        "risk_management_quality": "High"
    }

    if outcome in ["FORCED_CLOSE", "MANUAL_CLOSE"]:
        analysis["catalyst_type"] = "Manual Forced Close"
        analysis["summary"] = f"Position manually closed by trader at market price ${trade.get('exit_price', 0)} ({trade.get('net_r', 0):+.2f}R PnL)."
        analysis["key_factors"].append("User-initiated manual position termination")
        analysis["key_factors"].append(f"Exit Price: ${trade.get('exit_price', 0)} (Net PnL: ${trade.get('pnl_usd', 0):+.2f} USD)")

    elif outcome == "WIN" or outcome == "TRAILING_STOP_WIN":
        if outcome == "TRAILING_STOP_WIN":
            analysis["catalyst_type"] = "ATR Trailing Stop Protected Profit"
            analysis["summary"] = f"Dynamic trailing stop locked in +{trade['net_r']}R profit as momentum cooled off after peaking at +{mfe_r}R MFE."
            analysis["key_factors"].append("Dynamic stop protection prevented giving back gains")
            analysis["key_factors"].append(f"MFE reached +{mfe_r}R before trailing SL secured profit")
        elif bars_held <= 5:
            analysis["catalyst_type"] = "Impulsive Momentum Expansion"
            analysis["summary"] = f"Rapid target hit in {bars_held} bars. Strong order flow propelled price directly to {trade['target_rr']}R target without significant drawdown."
            analysis["key_factors"].append("High institutional velocity")
            analysis["key_factors"].append(f"Low adverse excursion (MAE: {mae_r}R)")
        elif mfe_r >= trade['target_rr']:
            analysis["catalyst_type"] = "Sustained Trend Continuation"
            analysis["summary"] = f"Trade navigated intermediate pullbacks and successfully reached full {trade['target_rr']}R extension over {bars_held} bars."
            analysis["key_factors"].append("Trend structure remained intact above invalidation level")
        else:
            analysis["catalyst_type"] = "Time-Horizon PnL Capture"
            analysis["summary"] = f"Position closed in profit (+{trade['net_r']}R) at trade horizon."
            
        if vol_surge:
            analysis["key_factors"].append("Volume surge confirmed direction")

    elif outcome in ["BE_EXIT", "BREAKEVEN_DEFENSE"]:
        analysis["catalyst_type"] = "Breakeven Shield De-risking"
        analysis["summary"] = f"Position reached +{mfe_r}R MFE, triggering the automated breakeven shield. Price subsequently retraced, exiting with 0.00R loss and zero capital drawdown."
        analysis["key_factors"].append("Automated de-risking prevented a full -1.0R loss")
        analysis["key_factors"].append("Exchange trading fees fully covered")

    elif outcome == "MOMENTUM_EXIT":
        analysis["catalyst_type"] = "Momentum Exhaustion Exit"
        analysis["summary"] = f"Strategy detected momentum oscillator flip and extreme RSI divergence after peaking at +{mfe_r}R MFE. Exited at market to protect capital."
        analysis["key_factors"].append("Proactive exhaustion exit avoided deeper retracement")
        analysis["key_factors"].append(f"Realized PnL: {trade['net_r']:+.2f}R")

    elif outcome == "TIME_EXIT":
        analysis["catalyst_type"] = "Time Stagnation Invalidation"
        analysis["summary"] = f"Trade stagnated in low-volatility consolidation for {bars_held} bars without momentum expansion. Exited early to free up capital."
        analysis["key_factors"].append("Capital recycled out of dead chop")
        analysis["key_factors"].append(f"Realized PnL: {trade['net_r']:+.2f}R")
            
    else:  # LOSS
        if bars_held <= 3 and mae_r >= 0.95:
            analysis["catalyst_type"] = "Immediate Liquidity Wick / Trap"
            analysis["summary"] = f"Quick stop-out within {bars_held} bars. Invalidation level was breached almost immediately by aggressive counter-flow."
            analysis["key_factors"].append("Fast hostile volume against entry position")
            analysis["key_factors"].append("Possible false breakout or front-running liquidity sweep")
        elif mfe_r >= 1.5:
            analysis["catalyst_type"] = "Failed Continuation / Reversal"
            analysis["summary"] = f"Trade initially moved favorable (+{mfe_r}R MFE), but stalled before the {trade['target_rr']}R target and completely reversed into stop loss."
            analysis["key_factors"].append(f"Reached {mfe_r}R favorable before exhausting momentum")
            analysis["key_factors"].append("Failed to break key structural barrier")
        else:
            analysis["catalyst_type"] = "Regime Resistance / Range Consolidation"
            analysis["summary"] = f"Position was caught in choppy chop/counter-trend pressure over {bars_held} bars and eventually triggered 1R SL."
            analysis["key_factors"].append("Lack of sustained volume follow-through")

    if trade.get('tp1_hit'):
        target_rr_val = float(trade.get('target_rr', 2.0))
        tp1_r_val = float(trade.get('tp1_rr', 1.0 if target_rr_val <= 2.0 else 1.5))
        banked_val = round(0.5 * tp1_r_val, 2)
        analysis["key_factors"].append(f"Dual-Stage Scale-Out executed: Banked +{banked_val:.2f}R guaranteed profit at TP1 (+{tp1_r_val:.2f}R target) with risk-free runner.")

    return analysis

TIMEFRAME_PROFILES: Dict[str, Dict[str, Any]] = {
    "5m": {
        "name": "5m Scalp",
        "expected_hold_str": "25m - 2.5h",
        "max_holding_bars": 64,
        "stagnation_bars": 10,
        "cooldown_minutes": 20,
        "scan_interval_sec": 15,
    },
    "15m": {
        "name": "15m Intraday",
        "expected_hold_str": "1.5h - 8h",
        "max_holding_bars": 64,       # ~16 hours
        "stagnation_bars": 16,        # ~4 hours smart stagnation
        "cooldown_minutes": 45,       # 3 bars
        "scan_interval_sec": 20,
    },
    "30m": {
        "name": "30m Intraday",
        "expected_hold_str": "3h - 16h",
        "max_holding_bars": 64,       # ~32 hours
        "stagnation_bars": 16,        # ~8 hours smart stagnation
        "cooldown_minutes": 90,       # 3 bars
        "scan_interval_sec": 30,
    },
    "1h": {
        "name": "1h Short Swing",
        "expected_hold_str": "12h - 3d",
        "max_holding_bars": 96,       # 4 days
        "stagnation_bars": 15,        # 15 hours
        "cooldown_minutes": 180,      # 3 hours (3 bars)
        "scan_interval_sec": 45,
    },
    "4h": {
        "name": "4h Macro Swing",
        "expected_hold_str": "2d - 10d",
        "max_holding_bars": 84,       # 14 days
        "stagnation_bars": 15,        # ~2.5 days
        "cooldown_minutes": 720,      # 12 hours (3 bars)
        "scan_interval_sec": 60,
    },
    "1d": {
        "name": "1d Positional Trend",
        "expected_hold_str": "2w - 2mo",
        "max_holding_bars": 60,       # 60 days
        "stagnation_bars": 15,        # 15 days
        "cooldown_minutes": 2880,     # 48 hours (2 bars)
        "scan_interval_sec": 120,
    },
}

from execution import EXIT_TIMEFRAME_PROFILES
for _timeframe, _exit_profile in EXIT_TIMEFRAME_PROFILES.items():
    TIMEFRAME_PROFILES[_timeframe].update(_exit_profile)


def simulate_strategy_on_dataframe(
    df: pd.DataFrame,
    strategy_cls: type[StrategyBase],
    target_rr: float = 2.0,
    fee_pct: float = 0.05,
    slippage_pct: float = 0.02,
    max_holding_bars: Optional[int] = None,
    timeframe: str = "30m",
    stagnation_bars: Optional[int] = None,
    params: Optional[Dict[str, Any]] = None,
    htf_data: Optional[Dict[str, pd.DataFrame]] = None,
    window_start: Optional[int] = None,
    window_end: Optional[int] = None,
) -> Dict[str, Any]:
    """Replay completed signals at the next open using conservative fill accounting.

    Window bounds are UTC seconds and constrain entries to [start, end). Earlier
    candles warm indicators only. Any surviving position is marked out at the
    last completed price in the window, explicitly tagged WINDOW_END.
    """
    from execution import create_position, process_bar, close_position, summarize_position
    from data_loader import completed_candles

    assert target_rr >= 2.0, f"Target Risk-to-Reward must be at least 1:2 (got {target_rr})"
    seconds = {"5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "4h": 14400, "1d": 86400}
    if timeframe not in seconds:
        raise ValueError(f"Unsupported timeframe: {timeframe}")
    duration = seconds[timeframe]
    profile = TIMEFRAME_PROFILES[timeframe]
    max_hold = max_holding_bars if max_holding_bars is not None else profile["max_holding_bars"]
    stagnation = stagnation_bars if stagnation_bars is not None else profile["stagnation_bars"]
    trades: List[Dict[str, Any]] = []
    diagnostics = {"insufficient_primary_history": 0, "missing_anchor_history": 0}
    if df is None or len(df) < 201:
        diagnostics["insufficient_primary_history"] = 1
        result = compile_simulation_metrics(trades, strategy_cls.name, target_rr)
        result.update({"simulation_version": "execution_v2", "execution_model": "conservative_ohlc",
                       "data_diagnostics": diagnostics,
                       "validation_window": {"start": window_start, "end": window_end},
                       "cost_model": {"version": "fills_v1", "fee_pct": fee_pct, "slippage_pct": slippage_pct}})
        return result
    df = df.sort_values("time", kind="stable").drop_duplicates("time", keep="last").reset_index(drop=True)
    df = completed_candles(df, timeframe, decision_time=window_end).reset_index(drop=True)
    df = compute_crypto_indicators(df)
    symbol = str(df.iloc[0].get("symbol", "CRYPTO")) if len(df) else "CRYPTO"
    anchor = {"5m": "30m", "15m": "1h", "30m": "4h"}.get(timeframe)
    i = 199
    while i < len(df) - 1:
        next_idx = i + 1
        decision_time = int(df.iloc[next_idx]["time"])
        if window_start is not None and decision_time < window_start:
            i += 1
            continue
        if window_end is not None and decision_time >= window_end:
            break
        # Only completed primary/anchor information may influence this decision.
        prefix = completed_candles(df.iloc[:i + 1], timeframe, decision_time=decision_time)
        if len(prefix) < 200:
            diagnostics["insufficient_primary_history"] += 1
            i += 1
            continue
        anchor_df = (htf_data or {}).get(anchor) if anchor else None
        if anchor_df is None or len(completed_candles(anchor_df, anchor, decision_time=decision_time)) < 200:
            diagnostics["missing_anchor_history"] += 1
            i += 1
            continue
        signal = strategy_cls.generate_signal(
            prefix, len(prefix) - 1, target_rr=target_rr, params=params,
            htf_data=htf_data, timeframe=timeframe, decision_time=decision_time,
        )
        if not signal:
            i += 1
            continue
        try:
            pos = create_position(
                signal["direction"], float(df.iloc[next_idx]["open"]), float(signal["risk_distance"]),
                1.0, float(signal.get("target_rr", target_rr)), decision_time, fee_pct, slippage_pct,
            )
        except (ValueError, KeyError, TypeError):
            i += 1
            continue
        pos.update({"strategy": strategy_cls.name, "symbol": symbol, "timeframe": timeframe,
                    "pre_trade_context": signal.get("pre_trade_context", {}),
                    "signal_time": int(prefix.iloc[-1]["time"]) + duration})
        exit_idx = next_idx
        for j in range(next_idx, len(df)):
            bar = df.iloc[j]
            bar_end = int(bar["time"]) + duration
            if window_end is not None and bar_end > window_end:
                break
            process_bar(pos, bar, timestamp=bar_end, completed_bars=j - next_idx + 1,
                        stagnation_bars=stagnation, max_holding_bars=max_hold)
            exit_idx = j
            if pos["closed"]:
                break
        if not pos["closed"]:
            last_bar = df.iloc[exit_idx]
            close_position(pos, float(last_bar["close"]), int(last_bar["time"]) + duration, "WINDOW_END")
        record = summarize_position(pos)
        record["trade_id"] = len(trades) + 1
        record["diagnostic"] = diagnose_trade_outcome(record, df, i, exit_idx)
        trades.append(record)
        # The exit bar may supply the next completed signal, never an earlier one.
        i = max(i + 1, exit_idx)
    result = compile_simulation_metrics(trades, strategy_cls.name, target_rr)
    result.update({"simulation_version": "execution_v2", "execution_model": "conservative_ohlc",
                   "validation_window": {"start": window_start, "end": window_end},
                   "data_diagnostics": diagnostics,
                   "cost_model": {"version": "fills_v1", "fee_pct": fee_pct, "slippage_pct": slippage_pct},
                   "window_end_closes": sum(t.get("exit_reason") == "WINDOW_END" for t in trades)})
    return result


def compile_simulation_metrics(trades: List[Dict[str, Any]], strategy_name: str, target_rr: float) -> Dict[str, Any]:
    """Metrics from net fills, with chronological equity and its initial zero peak."""
    ordered = sorted(trades, key=lambda t: (float(t.get("exit_time", 0)),
                                            float(t.get("entry_time", 0)), str(t.get("symbol", ""))))
    wins = [t for t in ordered if float(t["net_r"]) > 0]
    losses = [t for t in ordered if float(t["net_r"]) <= 0]
    total = len(ordered)
    win_r = sum(float(t["net_r"]) for t in wins)
    loss_r = -sum(float(t["net_r"]) for t in losses)
    net_r = sum(float(t["net_r"]) for t in ordered)
    cash_flows = []
    for index, trade in enumerate(ordered):
        fills = trade.get("fills")
        risk = float(trade.get("risk_amount_usd", 1.0))
        if fills and risk > 0:
            cash_flows.extend((float(f["timestamp"]), index, int(f.get("fill_id", 0)),
                               float(f["cash_delta_usd"]) / risk) for f in fills)
        else:
            cash_flows.append((float(trade.get("exit_time", index)), index, 0, float(trade["net_r"])))
    cash_flows.sort(key=lambda item: item[:3])
    equity = peak = max_dd = 0.0
    for _, _, _, change in cash_flows:
        equity += change
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    return {
        "strategy": strategy_name, "target_rr": target_rr, "total_trades": total,
        "win_count": len(wins), "loss_count": len(losses),
        "validation_status": "MEASURED_SAMPLE" if total else "NOT_VALIDATED",
        "win_rate_pct": round(100.0 * len(wins) / total, 2) if total else None,
        "total_net_r": round(net_r, 6),
        "profit_factor": round(win_r / loss_r, 4) if loss_r > 0 else None,
        "profit_factor_unbounded": loss_r == 0 and win_r > 0,
        "expectancy_r": round(net_r / total, 6) if total else None,
        "max_drawdown_r": round(max_dd, 6),
        "avg_bars_held": round(float(np.mean([t.get("bars_held", 0) for t in ordered])), 1) if total else 0.0,
        "trades": ordered,
    }
