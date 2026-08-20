import asyncio
from scanner import scan_market
from backtester import backtest_symbol

async def main():
    print("Testing market scan for 5 pairs...")
    scan_res = await scan_market(interval="1h", limit_pairs=5)
    print(f"Scanned {len(scan_res)} pairs successfully.")
    for item in scan_res:
        print(f"  {item['symbol']}: Price={item['price']}, Squeeze={item['is_squeeze']} ({item['squeeze_bars']} bars), Signal={item['signal']}")
        
    print("\nTesting backtester on BTCUSDT...")
    bt_res = await backtest_symbol("BTCUSDT", interval="1h", limit=500, target_rr=2.0)
    print(f"Backtest result: Trades={bt_res.get('total_trades')}, WinRate={bt_res.get('win_rate_pct')}%, ProfitFactor={bt_res.get('profit_factor')}, Total R={bt_res.get('total_r_return')}")

if __name__ == "__main__":
    asyncio.run(main())
