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

from data_loader import fetch_top_crypto_pairs, fetch_market_dataset, split_train_test
from strategies import AVAILABLE_STRATEGIES
from sim_engine import simulate_strategy_on_dataframe, compile_simulation_metrics
from trade_journal import generate_full_simulation_report
from strategy_memory import evaluate_reproducibility, save_strategy_to_catalog

async def main():
    parser = argparse.ArgumentParser(description="Automated Crypto Trading Simulation, Trade Analysis & Strategy Memory Engine")
    parser.add_argument("--timeframe", type=str, default="30m", help="Candle timeframe (e.g. 5m, 15m, 30m, 1h, 4h)")
    parser.add_argument("--limit", type=int, default=500, help="Number of candles per symbol (max 1000)")
    parser.add_argument("--num-coins", type=int, default=25, help="Number of top liquid USDT pairs to simulate")
    parser.add_argument("--rr", type=float, default=3.0, help="Target Risk-to-Reward ratio (minimum 3.0)")
    args = parser.parse_args()

    if args.rr < 2.0:
        print(f"[Error] Target Risk-to-Reward must be at least 1:2 (got {args.rr}). Resetting to 3.0.")
        args.rr = 3.0

    print(f"\n========================================================")
    print(f"  AUTOMATED CRYPTO SIMULATION & STRATEGY MEMORY ENGINE  ")
    print(f"========================================================")
    print(f" - Timeframe: {args.timeframe}")
    print(f" - Candles per pair: {args.limit}")
    print(f" - Target R:R: 1:{args.rr} (Strict >= 1:3)")
    print(f" - Top Coins: {args.num_coins}")
    print(f"--------------------------------------------------------\n")

    # Step 1: Fetch Top Crypto Pairs
    print("[1/5] Fetching liquid Binance USDT trading pairs...")
    symbols = await fetch_top_crypto_pairs(limit=args.num_coins)
    print(f"  -> Selected {len(symbols)} coins: {', '.join(symbols[:8])}...")

    # Step 2: Ingest Multi-Coin Market Datasets
    print(f"\n[2/5] Ingesting historical OHLCV data from Binance ({args.timeframe})...")
    dataset = await fetch_market_dataset(symbols, interval=args.timeframe, limit=args.limit)
    print(f"  -> Successfully loaded {len(dataset)} active market series.")

    if not dataset:
        print("[Error] No market data could be loaded. Exiting.")
        sys.exit(1)

    # Step 3: Run In-Sample and Out-of-Sample Simulations
    print(f"\n[3/5] Simulating strategies & analyzing trade-by-trade root causes...")
    strategy_results: Dict[str, Dict[str, Any]] = {}
    validation_summaries: List[Dict[str, Any]] = []

    for strat_cls in AVAILABLE_STRATEGIES:
        strat_name = strat_cls.name
        print(f"\n  [>>] Testing Strategy: [{strat_name}] (Target 1:{args.rr} RR)")
        
        train_trades_all: List[Dict[str, Any]] = []
        test_trades_all: List[Dict[str, Any]] = []

        for symbol, df in dataset.items():
            train_df, test_df = split_train_test(df, train_ratio=0.7)
            
            train_res = simulate_strategy_on_dataframe(train_df, strat_cls, target_rr=args.rr, timeframe=args.timeframe)
            test_res = simulate_strategy_on_dataframe(test_df, strat_cls, target_rr=args.rr, timeframe=args.timeframe)
            
            train_trades_all.extend(train_res.get('trades', []))
            test_trades_all.extend(test_res.get('trades', []))

        # Re-number trades sequentially for clarity
        for idx, t in enumerate(test_trades_all, 1):
            t['trade_id'] = idx

        train_metrics = compile_simulation_metrics(train_trades_all, strat_name, args.rr)
        test_metrics = compile_simulation_metrics(test_trades_all, strat_name, args.rr)
        
        strategy_results[strat_name] = test_metrics

        # Step 4: Reproducibility & Out-of-Sample Evaluation
        eval_result = evaluate_reproducibility(train_metrics, test_metrics)
        validation_summaries.append((strat_cls, eval_result, test_metrics))

        print(f"     Train (In-Sample): {train_metrics['total_trades']} trades | Win: {train_metrics['win_rate_pct']}% | PF: {train_metrics['profit_factor']} | Exp: +{train_metrics['expectancy_r']}R")
        print(f"     Test  (Out-of-Sample): {test_metrics['total_trades']} trades | Win: {test_metrics['win_rate_pct']}% | PF: {test_metrics['profit_factor']} | Exp: +{test_metrics['expectancy_r']}R | Net: {test_metrics['total_net_r']}R")

        if eval_result['is_reproducible']:
            print(f"     [+] VALIDATED REPRODUCIBLE! Saving to Strategy Catalog & Agent Memory.")
            save_strategy_to_catalog(
                strategy_name=strat_name, 
                eval_result=eval_result, 
                details={"description": strat_cls.description}
            )
        else:
            print(f"     [-] REJECTED: {', '.join(eval_result['rejection_reasons'])}")

    # Step 5: Generate Full Trade Report
    print(f"\n[5/5] Generating comprehensive trade diagnostics report...")
    report_file = generate_full_simulation_report(strategy_results)
    print(f"  -> Executive Trade Diagnostic Report saved to: {report_file}")

    print("\n========================================================")
    print("                 SIMULATION COMPLETE                    ")
    print("========================================================")

if __name__ == "__main__":
    asyncio.run(main())
