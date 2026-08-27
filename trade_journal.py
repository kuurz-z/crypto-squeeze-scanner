import os
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Philippine Standard Time (PHT, UTC+8 / Asia/Manila)
PHT = timezone(timedelta(hours=8))

def ph_now() -> datetime:
    """Return current timestamp in Philippine Standard Time (PHT, UTC+8)."""
    return datetime.now(timezone.utc).astimezone(PHT).replace(tzinfo=None)

def ph_fromtimestamp(ts: float) -> datetime:
    """Convert Unix epoch timestamp (seconds) to Philippine Standard Time (PHT, UTC+8)."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(PHT).replace(tzinfo=None)

def format_trade_markdown(trade: Dict[str, Any]) -> str:
    """Format a single trade record into structured Markdown with pre/post analysis."""
    dt_entry = ph_fromtimestamp(trade['entry_time']).strftime('%Y-%m-%d %H:%M') if trade.get('entry_time') else (trade.get('entry_time_str') or 'N/A')
    dt_exit = ph_fromtimestamp(trade['exit_time']).strftime('%Y-%m-%d %H:%M') if trade.get('exit_time') else (trade.get('exit_time_str') or 'N/A')
    
    status_icon = "🟢" if trade['outcome'] == "WIN" else "🔴"
    r_color = f"+{trade['net_r']}R" if trade['net_r'] > 0 else f"{trade['net_r']}R"
    
    ctx = trade.get('pre_trade_context', {})
    diag = trade.get('diagnostic', {})

    lines = [
        f"### {status_icon} Trade #{trade['trade_id']}: {trade['symbol']} {trade['direction']} ({r_color})",
        f"- **Strategy**: `{trade['strategy']}` | **Target R:R**: `1:{trade['target_rr']}`",
        f"- **Entry**: `${trade['entry_price']}` ({dt_entry}) | **Exit**: `${trade['exit_price']}` ({dt_exit})",
        f"- **Stop Loss**: `${trade['sl_price']}` | **Take Profit**: `${trade['tp_price']}`",
        f"- **Performance**: Net R: `{r_color}` | Max Drawdown (MAE): `{trade['mae_r']}R` | Max Run (MFE): `{trade['mfe_r']}R` | Bars: `{trade['bars_held']}`",
        "",
        "**Pre-Trade Analysis (Why Entered):**",
        f"- *Regime*: {ctx.get('regime', 'N/A')}",
        f"- *Rationale*: {ctx.get('reason', 'N/A')}",
        f"- *Metrics*: RVOL: `{ctx.get('rvol', 'N/A')}` | RSI: `{ctx.get('rsi', 'N/A')}` | ATR: `{ctx.get('volatility_atr', 'N/A')}`",
        "",
        "**Post-Trade Diagnostic (Root Cause & Outcome):**",
        f"- *Catalyst Category*: **{diag.get('catalyst_type', 'N/A')}**",
        f"- *Diagnosis*: {diag.get('summary', 'N/A')}",
        f"- *Key Contributing Factors*: {', '.join(diag.get('key_factors', [])) if diag.get('key_factors') else 'Standard trade evolution'}",
        "---"
    ]
    return "\n".join(lines)

def generate_full_simulation_report(
    results_by_strategy: Dict[str, Dict[str, Any]], 
    output_dir: str = "reports"
) -> str:
    """Generate comprehensive Markdown simulation report and save to disk."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp_str = ph_now().strftime("%Y%m%d_%H%M%S")
    report_filename = os.path.join(output_dir, f"simulation_report_{timestamp_str}.md")

    lines = [
        f"# Automated Crypto Simulation & Strategy Validation Report",
        f"*Generated on: {ph_now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "## 1. Strategy Performance Summary (Strict >= 1:3 RR)",
        "| Strategy | Target RR | Total Trades | Win Rate | Profit Factor | Net Return (R) | Expectancy / Trade | Max Drawdown |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    all_trades: List[Dict[str, Any]] = []

    for strat_name, res in results_by_strategy.items():
        lines.append(
            f"| **{strat_name}** | 1:{res['target_rr']} | {res['total_trades']} | {res['win_rate_pct']}% | {res['profit_factor']} | {res['total_net_r']}R | +{res['expectancy_r']}R | {res['max_drawdown_r']}R |"
        )
        all_trades.extend(res.get('trades', []))

    lines.extend([
        "",
        "## 2. In-Depth Trade Diagnostics Log",
        f"Total Simulated Trades Logged: **{len(all_trades)}**",
        ""
    ])

    for trade in all_trades:
        lines.append(format_trade_markdown(trade))

    report_content = "\n".join(lines)

    with open(report_filename, "w", encoding="utf-8") as f:
        f.write(report_content)

    return report_filename

def archive_and_reset_ledger(data_dir: str = ".") -> str:
    """
    Safely archive historical trades to reports/archive_pre_optimization_trades.json
    and reset live_trades.json, live_positions.json, and bot_state.json to a clean initial benchmark state.
    """
    reports_dir = os.path.join(data_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    archive_file = os.path.join(reports_dir, "archive_pre_optimization_trades.json")
    trades_file = os.path.join(data_dir, "live_trades.json")
    positions_file = os.path.join(data_dir, "live_positions.json")
    state_file = os.path.join(data_dir, "bot_state.json")

    # 1. Archive historical trades if live_trades.json exists and contains trades
    if os.path.exists(trades_file):
        try:
            with open(trades_file, "r", encoding="utf-8") as f:
                trades = json.load(f)
            if isinstance(trades, list) and len(trades) > 0:
                with open(archive_file, "w", encoding="utf-8") as f:
                    json.dump(trades, f, indent=2)
        except Exception as e:
            print(f"[TradeJournal] Warning: error archiving trades: {e}")

    # 2. Reset live_trades.json to empty list
    with open(trades_file, "w", encoding="utf-8") as f:
        json.dump([], f, indent=2)

    # 3. Reset live_positions.json to empty dict
    with open(positions_file, "w", encoding="utf-8") as f:
        json.dump({}, f, indent=2)

    # 4. Reset bot_state.json to clean initial benchmark state
    clean_state = {
        "initial_capital": 100.0,
        "current_balance": 100.0,
        "active_strategy": "Trend_Pullback_Confluence",
        "timeframe": "15m",
        "target_rr": 3.0,
        "open_positions": {},
        "symbol_loss_cooldowns": {},
        "circuit_breaker_until": None,
        "last_reset": ph_now().strftime("%Y-%m-%d %H:%M:%S")
    }
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(clean_state, f, indent=2)

    # 5. Clear SQLite DB if present in data_dir
    db_file = os.path.join(data_dir, "local_crypto_bot.db")
    if os.path.exists(db_file):
        try:
            import sqlite3
            conn = sqlite3.connect(db_file)
            cur = conn.cursor()
            cur.execute("DELETE FROM bot_trades;")
            cur.execute("DELETE FROM bot_positions;")
            cur.execute("DELETE FROM bot_state_store;")
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"[TradeJournal] Notice: DB clear tables: {e}")

    return archive_file

