import os
import json
from datetime import datetime
from typing import Dict, Any, List

def format_trade_markdown(trade: Dict[str, Any]) -> str:
    """Format a single trade record into structured Markdown with pre/post analysis."""
    dt_entry = datetime.fromtimestamp(trade['entry_time']).strftime('%Y-%m-%d %H:%M')
    dt_exit = datetime.fromtimestamp(trade['exit_time']).strftime('%Y-%m-%d %H:%M')
    
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
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_filename = os.path.join(output_dir, f"simulation_report_{timestamp_str}.md")

    lines = [
        f"# Automated Crypto Simulation & Strategy Validation Report",
        f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
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
