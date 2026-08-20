# Trade Record & Post-Mortem Diagnostic #25: BICOUSDT (LONG)
*Closed on: 2026-08-20 21:27:33*

## 1. Trade Execution Summary
- **Outcome**: `LOSS`
- **Realized PnL**: `$-1.08 USD` (-1.08 R)
- **Resulting Account Balance**: `$75.84 USD`
- **Entry Price**: `$0.01848` | **Exit Price**: `$0.017727`
- **Stop Loss**: `$0.017727` | **Take Profit**: `$0.020362` (1:2.5 RR)
- **Position Size**: `1328.0212 units` (Notional Value: `$24.54`)
- **Max Favorable Excursion (MFE)**: `+0.28 R`
- **Max Adverse Excursion (MAE)**: `-1.06 R`
- **Bars / Candles Held**: `1 bars`

## 2. Pre-Trade Quantitative Context (Why Entered)
- **Regime**: `Bullish Trend & Volatility Expansion`
- **Technical Catalyst**: Squeeze fired bullishly above BB upper band with volume surge
- **Relative Volume Surge (RVOL)**: `1.32x` (vs 20-bar SMA)
- **RSI (14)**: `74.1`
- **Momentum Oscillator**: `0.0002`
- **Volatility (ATR14)**: `0.0005`

## 3. Post-Trade Root Cause Diagnostic
- **Diagnostic Classification**: `Immediate Liquidity Wick / Trap`
- **Summary**: Quick stop-out within 1 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- **Key Determining Factors**:
  - Fast hostile volume against entry position
  - Possible false breakout or front-running liquidity sweep
