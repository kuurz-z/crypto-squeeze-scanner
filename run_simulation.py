import asyncio
import argparse
import sys
import os
from typing import Dict, Any, List
import pandas as pd

# Ensure UTF-8 output on Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from data_loader import fetch_top_crypto_pairs
from validation import run_report_only_evaluation


async def main():
    parser = argparse.ArgumentParser(description="Report-only chronological crypto strategy research")
    parser.add_argument("--timeframe", choices=["5m", "15m", "30m"], default="15m")
    parser.add_argument("--limit", type=int, default=1500,
                        help="Research horizon in 30-minute bars; indicator warmup is additional")
    parser.add_argument("--num-coins", type=int, default=25)
    parser.add_argument("--rr", type=float, default=2.0)
    parser.add_argument("--report-dir", default="reports")
    args = parser.parse_args()
    if args.rr < 2.0:
        parser.error("Target risk-to-reward must be at least 1:2")
    symbols = await fetch_top_crypto_pairs(limit=args.num_coins)
    report = await run_report_only_evaluation(
        mode="cli", report_dir=args.report_dir, symbols=symbols,
        timeframes=[args.timeframe], limit=args.limit,
        incumbent={"strategy": "Trend_Pullback_Confluence", "timeframe": args.timeframe,
                   "params": {}, "target_rr": args.rr},
    )
    print(report["message"])
    print("Execution: conservative OHLC candle approximation; costs are modeled per fill.")
    for row in report.get("final_results", []):
        candidate, metrics = row["candidate"], row["metrics"]
        expectancy = metrics.get("expectancy_r")
        expectancy_text = f"{expectancy:+.3f}R" if expectancy is not None else "Not validated"
        print(f"{candidate['strategy']} {candidate['timeframe']}: "
              f"{metrics.get('total_trades', 0)} final-test trades, "
              f"{expectancy_text} expectancy, "
              f"{metrics.get('total_net_r', 0):+.3f}R net")
    if report.get("cached"):
        print(report["cache_reason"])
    if report.get("report_path"):
        print(f"Report: {report['report_path']}")
    if report["status"] in ("CACHE_ERROR", "EVALUATION_FAILED"):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
