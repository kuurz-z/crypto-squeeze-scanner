"""
End-to-End System Simulation & Verification Script (Task 6)
Verifies:
1. fetch_top_usdt_pairs() filters pairs with >= $15M 24h quote volume.
2. fetch_symbol_htf_data() populates 15m, 30m, 1h, 4h indicator-enriched frames.
3. TrendPullbackConfluence.generate_signal() evaluates with 1h anchor and 1:3.0 RR.
4. LiveCryptoBot initializes cleanly with $100.00 capital, 15m timeframe, 3.0 target RR, 0 open positions.
"""
import os
import sys
import json
import asyncio
import tempfile
import pandas as pd
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock

# Project imports
from scanner import (
    fetch_top_usdt_pairs,
    filter_liquid_usdt_pairs,
    fetch_symbol_htf_data,
    compute_indicators
)
from strategies import (
    TrendPullbackConfluence,
    compute_crypto_indicators,
    evaluate_mtf_alignment
)
from live_bot import LiveCryptoBot, ph_now


def generate_synthetic_ohlcv(
    n: int = 100,
    base_price: float = 100.0,
    trend: str = "UP",
    timeframe: str = "15m"
) -> pd.DataFrame:
    """Generate deterministic OHLCV candles with clear trend and indicator properties."""
    freq_map = {"5m": "5min", "15m": "15min", "30m": "30min", "1h": "1h", "4h": "4h"}
    dates = pd.date_range("2026-01-01", periods=n, freq=freq_map.get(timeframe, "15min"))
    
    if trend == "UP":
        close_prices = np.linspace(base_price * 0.85, base_price, n)
    elif trend == "DOWN":
        close_prices = np.linspace(base_price * 1.15, base_price, n)
    else:
        close_prices = np.full(n, base_price)

    opens = close_prices - 0.2 if trend == "UP" else close_prices + 0.2
    highs = np.maximum(opens, close_prices) + 0.5
    lows = np.minimum(opens, close_prices) - 0.5
    volumes = np.full(n, 2000.0)

    df = pd.DataFrame({
        "time": [int(d.timestamp()) for d in dates],
        "open": opens,
        "high": highs,
        "low": lows,
        "close": close_prices,
        "volume": volumes,
        "taker_buy_base": volumes * (0.60 if trend == "UP" else 0.40)
    })
    return compute_crypto_indicators(df)


async def verify_scanner_liquidity_filter() -> bool:
    print("\n--- [1/4] Verifying fetch_top_usdt_pairs & Liquidity Filter ---")
    mock_tickers = [
        {"symbol": "BTCUSDT", "quoteVolume": "500000000.0"},  # $500M -> Pass
        {"symbol": "ETHUSDT", "quoteVolume": "250000000.0"},  # $250M -> Pass
        {"symbol": "SOLUSDT", "quoteVolume": "18000000.0"},   # $18M -> Pass
        {"symbol": "LOWVOLUSDT", "quoteVolume": "5000000.0"}, # $5M -> Filtered (< $15M)
        {"symbol": "DEADUSDT", "quoteVolume": "100000.0"},    # $100k -> Filtered (< $15M)
        {"symbol": "USDCUSDT", "quoteVolume": "800000000.0"}, # Stablecoin -> Filtered
        {"symbol": "FDUSDUSDT", "quoteVolume": "900000000.0"},# Stablecoin -> Filtered
        {"symbol": "BTCUPUSDT", "quoteVolume": "50000000.0"}, # Leveraged token -> Filtered
        {"symbol": "ETHDOWNUSDT", "quoteVolume": "40000000.0"},# Leveraged token -> Filtered
    ]

    filtered = filter_liquid_usdt_pairs(mock_tickers, min_quote_volume=15000000.0)
    print(f"Filtered symbols from mock: {filtered}")
    assert "BTCUSDT" in filtered, "BTCUSDT should be included"
    assert "ETHUSDT" in filtered, "ETHUSDT should be included"
    assert "SOLUSDT" in filtered, "SOLUSDT should be included"
    assert "LOWVOLUSDT" not in filtered, "LOWVOLUSDT should be filtered (< $15M)"
    assert "DEADUSDT" not in filtered, "DEADUSDT should be filtered (< $15M)"
    assert "USDCUSDT" not in filtered, "USDCUSDT stablecoin pair should be filtered"
    assert "FDUSDUSDT" not in filtered, "FDUSDUSDT stablecoin pair should be filtered"
    assert "BTCUPUSDT" not in filtered, "BTCUPUSDT leveraged token should be filtered"
    assert "ETHDOWNUSDT" not in filtered, "ETHDOWNUSDT leveraged token should be filtered"
    assert len(filtered) == 3, f"Expected 3 filtered liquid pairs, got {len(filtered)}"

    # Test fetch_top_usdt_pairs with mocked session
    mock_resp = AsyncMock()
    mock_resp.status = 200
    mock_resp.json = AsyncMock(return_value=mock_tickers)
    mock_session = MagicMock()
    mock_session.get.return_value.__aenter__.return_value = mock_resp

    with patch("scanner.get_http_session", AsyncMock(return_value=mock_session)):
        with patch("scanner._top_pairs_cache", {"timestamp": 0, "pairs": []}):
            top_pairs = await fetch_top_usdt_pairs(limit=10, min_quote_volume=15000000.0)
            print(f"fetch_top_usdt_pairs output: {top_pairs}")
            assert top_pairs == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    print(" [1/4] PASSED: Scanner liquidity filter strictly enforces >= $15M 24h volume floor.")
    return True


async def verify_symbol_htf_data_population() -> bool:
    print("\n--- [2/4] Verifying fetch_symbol_htf_data Population ---")
    mock_15m = generate_synthetic_ohlcv(100, base_price=100.0, trend="UP", timeframe="15m")
    mock_30m = generate_synthetic_ohlcv(100, base_price=100.0, trend="UP", timeframe="30m")
    mock_1h = generate_synthetic_ohlcv(100, base_price=100.0, trend="UP", timeframe="1h")
    mock_4h = generate_synthetic_ohlcv(100, base_price=100.0, trend="UP", timeframe="4h")

    async def mock_fetch_klines(session, symbol, interval="30m", limit=120):
        mapping = {"15m": mock_15m, "30m": mock_30m, "1h": mock_1h, "4h": mock_4h}
        return mapping.get(interval, mock_30m)

    mock_session = MagicMock()
    with patch("scanner.fetch_klines", side_effect=mock_fetch_klines):
        htf_map = await fetch_symbol_htf_data(
            mock_session,
            "BTCUSDT",
            intervals=["15m", "30m", "1h", "4h"],
            limit=120
        )

    print(f"Populated HTF timeframes: {list(htf_map.keys())}")
    for tf in ["15m", "30m", "1h", "4h"]:
        assert tf in htf_map, f"Missing timeframe {tf} in HTF map"
        df = htf_map[tf]
        assert isinstance(df, pd.DataFrame), f"HTF {tf} is not a DataFrame"
        assert len(df) >= 30, f"HTF {tf} length {len(df)} is less than 30"
        # Check computed indicators
        for ind in ["ema20", "ema50", "ema200", "bb_upper", "bb_lower", "atr14"]:
            assert ind in df.columns, f"Missing indicator {ind} in {tf} frame"

    print(" [2/4] PASSED: fetch_symbol_htf_data accurately populates 15m, 30m, 1h, 4h indicator frames.")
    return True


def verify_trend_pullback_confluence_signal() -> bool:
    print("\n--- [3/4] Verifying TrendPullbackConfluence Signal Generation ---")
    n = 80
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    close_base = 100.0
    open_base = close_base - 1.5
    high_base = close_base + 0.3
    low_base = open_base - 0.3

    df_15m = pd.DataFrame({
        "time": [int(d.timestamp()) for d in dates],
        "open": np.linspace(80, open_base, n),
        "high": np.linspace(81, high_base, n),
        "low": np.linspace(79, low_base, n),
        "close": np.linspace(80.5, close_base, n),
        "volume": np.full(n, 2500.0),
        "taker_buy_base": np.full(n, 1500.0)
    })
    df_15m = compute_crypto_indicators(df_15m)

    # Set exact pullback setup conditions on the final candle (idx 79)
    df_15m.loc[79, "open"] = 99.0
    df_15m.loc[79, "close"] = 101.0
    df_15m.loc[79, "high"] = 101.5
    df_15m.loc[79, "low"] = 98.8
    df_15m.loc[79, "ema20"] = 99.5
    df_15m.loc[79, "ema50"] = 95.0
    df_15m.loc[79, "ema200"] = 88.0
    df_15m.loc[79, "rsi14"] = 48.0
    df_15m.loc[79, "rvol"] = 1.6
    df_15m.loc[79, "adx14"] = 28.0
    df_15m.loc[79, "hurst"] = 0.58
    df_15m.loc[79, "atr14"] = 1.0
    df_15m.loc[79, "buyer_ratio"] = 58.0

    # 1h Higher Timeframe Anchor DataFrame (Bullish aligned)
    df_1h = generate_synthetic_ohlcv(60, base_price=100.0, trend="UP", timeframe="1h")
    htf_data_aligned = {"1h": df_1h, "4h": generate_synthetic_ohlcv(60, base_price=100.0, trend="UP", timeframe="4h")}

    signal = TrendPullbackConfluence.generate_signal(
        df=df_15m,
        idx=79,
        target_rr=3.0,
        htf_data=htf_data_aligned,
        timeframe="15m"
    )

    print("Generated 15m Signal with 1h Anchor:")
    print(json.dumps(signal, indent=2))

    assert signal is not None, "Signal should be generated for valid setup"
    assert signal["strategy"] == "Trend_Pullback_Confluence"
    assert signal["direction"] == "LONG"
    assert signal["timeframe"] == "15m"
    assert signal["target_rr"] == 3.0, f"Expected target_rr == 3.0, got {signal['target_rr']}"
    
    # Check stop loss & take profit mathematical relationship
    entry_p = signal["entry_price"]
    sl_p = signal["sl_price"]
    tp_p = signal["tp_price"]
    risk = entry_p - sl_p
    reward = tp_p - entry_p
    rr_ratio = reward / risk
    print(f"Entry: {entry_p}, SL: {sl_p}, TP: {tp_p}, Risk: {risk:.4f}, Reward: {reward:.4f}, Calculated RR: {rr_ratio:.2f}")
    assert abs(rr_ratio - 3.0) < 0.05, f"Reward-to-risk ratio must be 3.0 (got {rr_ratio:.2f})"

    # Check 1h Anchor confirmation in pre_trade_context
    mtf_meta = signal["pre_trade_context"]["mtf_alignment"]
    assert mtf_meta["aligned"] is True
    assert mtf_meta["entry_tf"] == "15m"
    assert mtf_meta["anchor_tf"] == "1h"

    # Verify that conflicting 1h HTF trend rejects the signal
    df_1h_bearish = generate_synthetic_ohlcv(60, base_price=100.0, trend="DOWN", timeframe="1h")
    htf_data_conflicting = {"1h": df_1h_bearish}
    rejected_signal = TrendPullbackConfluence.generate_signal(
        df=df_15m,
        idx=79,
        target_rr=3.0,
        htf_data=htf_data_conflicting,
        timeframe="15m"
    )
    assert rejected_signal is None, "Signal must be rejected when 1h anchor is bearish for a LONG setup"
    print(" Conflicting 1h anchor correctly rejected conflicting long signal.")

    print(" [3/4] PASSED: TrendPullbackConfluence evaluates with 1h anchor and 1:3.0 RR.")
    return True


def verify_live_crypto_bot_benchmark() -> bool:
    print("\n--- [4/4] Verifying LiveCryptoBot Clean Initialization ---")
    test_dir = tempfile.mkdtemp()
    bot = LiveCryptoBot(
        initial_capital=100.0,
        fixed_risk_usd=1.0,
        timeframe="15m",
        max_open_positions=5,
        target_rr=3.0,
        active_strategy_name="Trend_Pullback_Confluence",
        data_dir=test_dir
    )

    print(f"Bot Initial Capital: ${bot.initial_capital:.2f}")
    print(f"Bot Current Balance: ${bot.current_balance:.2f}")
    print(f"Bot Timeframe: {bot.timeframe}")
    print(f"Bot Target RR: {bot.target_rr}")
    print(f"Bot Open Positions: {len(bot.open_positions)}")
    print(f"Bot Closed Trades: {len(bot.closed_trades)}")
    print(f"Bot Active Strategy: {bot.active_strategy_name}")
    print(f"Bot Is Depleted: {bot.is_depleted}")

    assert bot.initial_capital == 100.0, "Initial capital must be 100.0"
    assert bot.current_balance == 100.0, "Current balance must be 100.0"
    assert bot.timeframe == "15m", "Timeframe must be 15m"
    assert bot.target_rr == 3.0, "Target RR must be 3.0"
    assert len(bot.open_positions) == 0, "Open positions must be empty"
    assert len(bot.closed_trades) == 0, "Closed trades must be empty"
    assert bot.active_strategy_name == "Trend_Pullback_Confluence", "Active strategy must be Trend_Pullback_Confluence"
    assert bot.is_depleted is False, "Bot must not be depleted"

    telemetry = bot.get_telemetry()
    assert telemetry["initial_capital"] == 100.0
    assert telemetry["current_balance"] == 100.0
    assert telemetry["active_strategy"] == "Trend_Pullback_Confluence"
    assert telemetry["target_rr"] == 3.0
    assert telemetry["open_positions_count"] == 0
    assert telemetry["timeframe"] == "15m"

    print(" [4/4] PASSED: LiveCryptoBot cleanly initializes with $100.00 capital, 15m timeframe, 3.0 target RR, 0 open positions.")
    return True


def verify_disk_state_files() -> bool:
    print("\n--- State Files Verification ---")
    archive_file = "reports/archive_pre_optimization_trades.json"
    trades_file = "live_trades.json"
    positions_file = "live_positions.json"
    state_file = "bot_state.json"

    assert os.path.exists(archive_file), f"Missing {archive_file}"
    assert os.path.exists(trades_file), f"Missing {trades_file}"
    assert os.path.exists(positions_file), f"Missing {positions_file}"
    assert os.path.exists(state_file), f"Missing {state_file}"

    with open(archive_file, "r", encoding="utf-8") as f:
        archive_data = json.load(f)
    assert isinstance(archive_data, list), "Archive data must be a list"
    assert len(archive_data) == 85, f"Archive must contain 85 historical records, found {len(archive_data)}"
    print(f" {archive_file}: Verified {len(archive_data)} historical records.")

    with open(trades_file, "r", encoding="utf-8") as f:
        trades_data = json.load(f)
    assert trades_data == [], f"live_trades.json must be [], found {trades_data}"
    print(f" {trades_file}: Verified empty list [].")

    with open(positions_file, "r", encoding="utf-8") as f:
        positions_data = json.load(f)
    assert positions_data == {}, f"live_positions.json must be {{}}, found {positions_data}"
    print(f" {positions_file}: Verified empty dict {{}}.")

    with open(state_file, "r", encoding="utf-8") as f:
        state_data = json.load(f)
    assert state_data.get("current_balance") == 100.0, f"bot_state current_balance must be 100.0, got {state_data.get('current_balance')}"
    strategy_name = state_data.get("active_strategy_name", state_data.get("active_strategy"))
    assert strategy_name == "Trend_Pullback_Confluence", f"active strategy must be Trend_Pullback_Confluence, got {strategy_name}"
    print(f" {state_file}: Verified current_balance: 100.0, active_strategy: Trend_Pullback_Confluence.")

    return True


async def main():
    print("=" * 60)
    print("STARTING FULL END-TO-END SYSTEM SIMULATION & VERIFICATION")
    print("=" * 60)

    res1 = await verify_scanner_liquidity_filter()
    res2 = await verify_symbol_htf_data_population()
    res3 = verify_trend_pullback_confluence_signal()
    res4 = verify_live_crypto_bot_benchmark()
    res5 = verify_disk_state_files()

    print("\n" + "=" * 60)
    if all([res1, res2, res3, res4, res5]):
        print("ALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY (100% PASS)")
        print("=" * 60)
    else:
        print("VERIFICATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
