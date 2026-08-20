import asyncio
import aiohttp
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_TICKER_24HR_URL = "https://api.binance.com/api/v3/ticker/24hr"

EXCLUDED_KEYWORDS = [
    'UPUSDT', 'DOWNUSDT', 'BEARUSDT', 'BULLUSDT', 'USDCUSDT', 'FDUSDUSDT', 
    'TUSDUSDT', 'EURUSDT', 'DAIUSDT', 'USD1USDT', 'USDEUSDT', 'EURIUSDT', 
    'AEURUSDT', 'USDPUSDT', 'PYUSDUSDT', 'USDDUSDT', 'WBTCUSDT', 'WETHUSDT',
    'RLUSDUSDT', 'BUSDUSDT', 'USTCUSDT'
]

DEFAULT_TOP_COINS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "ADAUSDT", 
    "AVAXUSDT", "LINKUSDT", "SUIUSDT", "NEARUSDT", "DOTUSDT", "APTUSDT", "LTCUSDT", 
    "UNIUSDT", "ICPUSDT", "RENDERUSDT", "INJUSDT", "TIAUSDT", "SEIUSDT", "ARBUSDT", 
    "OPUSDT", "PEPEUSDT", "WIFUSDT", "SHIBUSDT", "BONKUSDT", "FETUSDT", "TAOUSDT", 
    "RUNEUSDT", "STXUSDT", "AAVEUSDT", "MKRUSDT", "PENDLEUSDT", "ONDOUSDT", "JUPUSDT", 
    "PYTHUSDT", "CRVUSDT", "FILUSDT", "ATOMUSDT", "HBARUSDT", "KASUSDT", "FTMUSDT", 
    "GALAUSDT", "FLOKIUSDT", "IMXUSDT", "GRTUSDT", "THETAUSDT", "ALGOUSDT", "SANDUSDT", "MANAUSDT"
]

async def fetch_top_crypto_pairs(limit: int = 100) -> List[str]:
    """Fetch top 100 liquid USDT spot pairs by 24h quote volume from Binance API."""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as session:
            async with session.get(BINANCE_TICKER_24HR_URL) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    usdt_pairs = [
                        item for item in data 
                        if item['symbol'].endswith('USDT') 
                        and not any(x == item['symbol'] or x in item['symbol'] for x in EXCLUDED_KEYWORDS)
                    ]
                    usdt_pairs.sort(key=lambda x: float(x.get('quoteVolume', 0)), reverse=True)
                    top_symbols = [item['symbol'] for item in usdt_pairs[:limit]]
                    if top_symbols:
                        return top_symbols
    except Exception as e:
        print(f"[DataLoader] Notice: Failed to fetch live tickers ({e}), using default top liquid coins.")
    return DEFAULT_TOP_COINS[:limit]

async def fetch_symbol_klines(
    session: aiohttp.ClientSession, 
    symbol: str, 
    interval: str = "15m", 
    limit: int = 500
) -> Optional[pd.DataFrame]:
    """Fetch OHLCV candlestick data with rate-limit header tracking and backoff."""
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        async with session.get(BINANCE_KLINES_URL, params=params, timeout=aiohttp.ClientTimeout(total=8)) as resp:
            # Check Binance rate limit usage
            used_weight = int(resp.headers.get('x-mbx-used-weight-1m', 0))
            if used_weight > 900:
                print(f"[RateLimitGuard] Warning: Binance 1m used weight high ({used_weight}/1200), pacing requests.")
                await asyncio.sleep(0.5)

            if resp.status == 429:
                retry_after = int(resp.headers.get('Retry-After', 30))
                print(f"[RateLimitGuard] HTTP 429 received. Backing off for {retry_after}s...")
                await asyncio.sleep(retry_after)
                return None

            if resp.status == 200:
                raw = await resp.json()
                if not raw or len(raw) < 50:
                    return None
                
                df = pd.DataFrame(raw, columns=[
                    'open_time', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df['time'] = (df['open_time'] // 1000).astype(int)
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                df['symbol'] = symbol
                return df[['time', 'open', 'high', 'low', 'close', 'volume', 'symbol']]
    except Exception as e:
        print(f"[DataLoader] Warning fetching {symbol}: {e}")
        return None

async def fetch_market_dataset(
    symbols: List[str], 
    interval: str = "15m", 
    limit: int = 500
) -> Dict[str, pd.DataFrame]:
    """Fetch OHLCV market dataset for multiple crypto symbols concurrently."""
    dataset: Dict[str, pd.DataFrame] = {}
    connector = aiohttp.TCPConnector(limit=10)
    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [fetch_symbol_klines(session, sym, interval, limit) for sym in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for sym, res in zip(symbols, results):
            if isinstance(res, pd.DataFrame) and len(res) >= 60:
                dataset[sym] = res
    return dataset

def split_train_test(df: pd.DataFrame, train_ratio: float = 0.7) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split time-series data into In-Sample (Train/Discovery) and Out-of-Sample (Validation)."""
    split_idx = int(len(df) * train_ratio)
    train_df = df.iloc[:split_idx].copy().reset_index(drop=True)
    test_df = df.iloc[split_idx:].copy().reset_index(drop=True)
    return train_df, test_df
