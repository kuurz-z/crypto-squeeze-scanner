# Trade Record & Post-Mortem Diagnostic #21: BICOUSDT (LONG)
*Closed on: 2026-08-20 21:26:03*

## 1. Trade Execution Summary
- **Outcome**: `LOSS`
- **Realized PnL**: `$-1.08 USD` (-1.08 R)
- **Resulting Account Balance**: `$80.16 USD`
- **Entry Price**: `$0.01849` | **Exit Price**: `$0.017737`
- **Stop Loss**: `$0.017737` | **Take Profit**: `$0.020372` (1:2.5 RR)
- **Position Size**: `1328.0212 units` (Notional Value: `$24.56`)
- **Max Favorable Excursion (MFE)**: `+0.27 R`
- **Max Adverse Excursion (MAE)**: `-1.08 R`
- **Bars / Candles Held**: `1 bars`

## 2. Pre-Trade Quantitative Context (Why Entered)
- **Regime**: `Bullish Trend & Volatility Expansion`
- **Technical Catalyst**: Squeeze fired bullishly above BB upper band with volume surge
- **Relative Volume Surge (RVOL)**: `1.26x` (vs 20-bar SMA)
- **RSI (14)**: `74.2`
- **Momentum Oscillator**: `0.0002`
- **Volatility (ATR14)**: `0.0005`

## 3. Post-Trade Root Cause Diagnostic
- **Diagnostic Classification**: `Immediate Liquidity Wick / Trap`
- **Summary**: Quick stop-out within 1 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- **Key Determining Factors**:
  - Fast hostile volume against entry position
  - Possible false breakout or front-running liquidity sweep
