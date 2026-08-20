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
    outcome = trade['outcome']
    direction = trade['direction']
    bars_held = trade['bars_held']
    mae_r = trade['mae_r']
    mfe_r = trade['mfe_r']
    strategy_name = trade['strategy']
    
    # Calculate price action behavior during trade duration
    trade_slice = df.iloc[entry_idx:exit_idx + 1]
    vol_surge = (trade_slice['volume'].max() / (trade_slice['volume'].mean() + 1e-6)) > 1.8
    
    analysis = {
        "summary": "",
        "catalyst_type": "",
        "key_factors": [],
        "risk_management_quality": "High"
    }

    if outcome == "WIN" or outcome == "TRAILING_STOP_WIN":
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

    return analysis

def simulate_strategy_on_dataframe(
    df: pd.DataFrame, 
    strategy_cls: type[StrategyBase],
    target_rr: float = 3.0,
    fee_pct: float = 0.05,
    slippage_pct: float = 0.02,
    max_holding_bars: int = 120
) -> Dict[str, Any]:
    """
    Simulate a strategy over historical crypto candles with strict >= 1:3 RR and comprehensive diagnostics.
    """
    assert target_rr >= 3.0, f"Target Risk-to-Reward must be at least 1:3 (got {target_rr})"
    
    df = compute_crypto_indicators(df)
    trades: List[Dict[str, Any]] = []
    
    n = len(df)
    i = 50
    symbol = df['symbol'].iloc[0] if 'symbol' in df.columns else 'CRYPTO'

    while i < n - 2:
        signal = strategy_cls.generate_signal(df, i, target_rr=target_rr)
        if not signal:
            i += 1
            continue

        direction = signal['direction']
        entry_price = signal['entry_price']
        sl_price = signal['sl_price']
        tp_price = signal['tp_price']
        risk_dist = signal['risk_distance']
        entry_time = int(df.iloc[i]['time'])
        
        is_long = (direction == 'LONG')
        bars_held = 0
        outcome = "OPEN"
        exit_price = entry_price
        exit_time = entry_time
        exit_idx = i
        
        max_favorable_price = entry_price
        max_adverse_price = entry_price

        # Forward simulate subsequent candles
        for j in range(i + 1, min(i + max_holding_bars + 1, n)):
            bars_held += 1
            bar = df.iloc[j]
            bar_high = float(bar['high'])
            bar_low = float(bar['low'])
            bar_time = int(bar['time'])

            if is_long:
                max_favorable_price = max(max_favorable_price, bar_high)
                max_adverse_price = min(max_adverse_price, bar_low)

                # Check SL hit
                if bar_low <= sl_price:
                    outcome = "LOSS"
                    exit_price = sl_price
                    exit_time = bar_time
                    exit_idx = j
                    break
                # Check TP hit (>= 1:3 RR)
                elif bar_high >= tp_price:
                    outcome = "WIN"
                    exit_price = tp_price
                    exit_time = bar_time
                    exit_idx = j
                    break
            else:  # SHORT
                max_favorable_price = min(max_favorable_price, bar_low)
                max_adverse_price = max(max_adverse_price, bar_high)

                # Check SL hit
                if bar_high >= sl_price:
                    outcome = "LOSS"
                    exit_price = sl_price
                    exit_time = bar_time
                    exit_idx = j
                    break
                # Check TP hit (>= 1:3 RR)
                elif bar_low <= tp_price:
                    outcome = "WIN"
                    exit_price = tp_price
                    exit_time = bar_time
                    exit_idx = j
                    break

        if outcome == "OPEN":
            # Timeout at max holding period: close at market close price
            last_bar = df.iloc[min(i + max_holding_bars, n - 1)]
            exit_price = float(last_bar['close'])
            exit_time = int(last_bar['time'])
            exit_idx = min(i + max_holding_bars, n - 1)
            pnl_dist = (exit_price - entry_price) if is_long else (entry_price - exit_price)
            raw_r = round(pnl_dist / risk_dist, 2)
            outcome = "WIN" if raw_r > 0 else "LOSS"
        else:
            raw_r = target_rr if outcome == "WIN" else -1.0

        # Calculate MAE and MFE in terms of R-multiples
        if is_long:
            mfe_r = round(max(0.0, (max_favorable_price - entry_price) / risk_dist), 2)
            mae_r = round(max(0.0, (entry_price - max_adverse_price) / risk_dist), 2)
        else:
            mfe_r = round(max(0.0, (entry_price - max_favorable_price) / risk_dist), 2)
            mae_r = round(max(0.0, (max_adverse_price - entry_price) / risk_dist), 2)

        # Friction calculation (Roundtrip fee + slippage)
        friction_cost_pct = (fee_pct + slippage_pct) * 2.0
        risk_pct = (risk_dist / entry_price) * 100.0
        friction_r = friction_cost_pct / risk_pct if risk_pct > 0 else 0.05
        net_r = round(raw_r - friction_r, 2)

        trade_record = {
            "trade_id": len(trades) + 1,
            "symbol": symbol,
            "strategy": strategy_cls.name,
            "direction": direction,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": round(entry_price, 6 if entry_price < 1 else 2),
            "exit_price": round(exit_price, 6 if exit_price < 1 else 2),
            "sl_price": round(sl_price, 6 if sl_price < 1 else 2),
            "tp_price": round(tp_price, 6 if tp_price < 1 else 2),
            "target_rr": target_rr,
            "outcome": outcome,
            "raw_r": raw_r,
            "net_r": net_r,
            "mfe_r": mfe_r,
            "mae_r": mae_r,
            "bars_held": bars_held,
            "pre_trade_context": signal['pre_trade_context']
        }

        # Perform deep algorithmic diagnosis
        diagnostic = diagnose_trade_outcome(trade_record, df, i, exit_idx)
        trade_record['diagnostic'] = diagnostic

        trades.append(trade_record)

        # Advance index to avoid taking simultaneous overlapping signals on the same candle sequence
        i += max(1, bars_held)

    return compile_simulation_metrics(trades, strategy_cls.name, target_rr)

def compile_simulation_metrics(trades: List[Dict[str, Any]], strategy_name: str, target_rr: float) -> Dict[str, Any]:
    """Calculate statistical performance metrics for a batch of trades."""
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "strategy": strategy_name,
            "target_rr": target_rr,
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "total_net_r": 0.0,
            "profit_factor": 0.0,
            "expectancy_r": 0.0,
            "max_drawdown_r": 0.0,
            "avg_bars_held": 0.0,
            "trades": []
        }

    wins = [t for t in trades if t['net_r'] > 0]
    losses = [t for t in trades if t['net_r'] <= 0]
    
    win_count = len(wins)
    loss_count = len(losses)
    win_rate_pct = round((win_count / total_trades) * 100.0, 2)
    
    total_win_r = sum(t['net_r'] for t in wins)
    total_loss_r = abs(sum(t['net_r'] for t in losses))
    profit_factor = round(total_win_r / total_loss_r, 2) if total_loss_r > 0 else 999.0
    
    total_net_r = round(sum(t['net_r'] for t in trades), 2)
    expectancy_r = round(total_net_r / total_trades, 3)
    
    # Calculate Max Drawdown in R
    cumulative_r = []
    curr = 0.0
    for t in trades:
        curr += t['net_r']
        cumulative_r.append(curr)
        
    peak = cumulative_r[0]
    max_dd = 0.0
    for val in cumulative_r:
        if val > peak:
            peak = val
        dd = peak - val
        if dd > max_dd:
            max_dd = dd

    avg_bars_held = round(float(np.mean([t['bars_held'] for t in trades])), 1)

    return {
        "strategy": strategy_name,
        "target_rr": target_rr,
        "total_trades": total_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate_pct": win_rate_pct,
        "total_net_r": total_net_r,
        "profit_factor": profit_factor,
        "expectancy_r": expectancy_r,
        "max_drawdown_r": round(max_dd, 2),
        "avg_bars_held": avg_bars_held,
        "trades": trades
    }
