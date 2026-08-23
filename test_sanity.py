import asyncio
import time
from scanner import scan_market, close_http_session
from backtester import backtest_symbol

async def main():
    print("Testing initial market scan for 5 pairs (15m)...")
    t0 = time.time()
    scan_res = await scan_market(interval="15m", limit_pairs=5)
    t1 = time.time()
    print(f"Scanned {len(scan_res)} pairs in {(t1 - t0)*1000:.1f}ms.")
    
    print("\nTesting subsequent cached market scan (15m)...")
    t2 = time.time()
    scan_cached = await scan_market(interval="15m", limit_pairs=5)
    t3 = time.time()
    print(f"Retrieved {len(scan_cached)} pairs from cache in {(t3 - t2)*1000:.2f}ms.")

    print("\nTesting backtester on BTCUSDT...")
    bt_res = await backtest_symbol("BTCUSDT", interval="1h", limit=500, target_rr=2.0)
    print(f"Backtest result: Trades={bt_res.get('total_trades')}, WinRate={bt_res.get('win_rate_pct')}%, ProfitFactor={bt_res.get('profit_factor')}, Total R={bt_res.get('total_r_return')}")

    await close_http_session()

if __name__ == "__main__":
    asyncio.run(main())

