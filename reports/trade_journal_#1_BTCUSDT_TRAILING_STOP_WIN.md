# Trade Record & Post-Mortem Diagnostic #1: BTCUSDT (LONG)
*Closed on: 2026-08-26 19:02:42*

## 1. Trade Execution Summary
- **Outcome**: `LOSS`
- **Realized PnL**: `$+1.47 USD` (+1.47 R)
- **Resulting Account Balance**: `$101.47 USD`
- **Entry Price**: `$100.0` | **Exit Price**: `$115.5`
- **Stop Loss**: `$115.5` | **Take Profit**: `$125.0` (1:2.5 RR)
- **Position Size**: `1.0 units` (Notional Value: `$0.00`)
- **Max Favorable Excursion (MFE)**: `+2.3 R`
- **Max Adverse Excursion (MAE)**: `-0.0 R`
- **Bars / Candles Held**: `3 bars`

## 2. Pre-Trade Quantitative Context (Why Entered)
- **Regime**: `N/A`
- **Technical Catalyst**: Test setup
- **Relative Volume Surge (RVOL)**: `N/Ax` (vs 20-bar SMA)
- **RSI (14)**: `N/A`
- **Momentum Oscillator**: `N/A`
- **Volatility (ATR14)**: `N/A`

## 3. Post-Trade Root Cause Diagnostic
- **Diagnostic Classification**: `ATR Trailing Stop Protected Profit`
- **Summary**: Dynamic trailing stop locked in +1.47R profit as momentum cooled off after peaking at +2.3R MFE.
- **Key Determining Factors**:
  - Dynamic stop protection prevented giving back gains
  - MFE reached +2.3R before trailing SL secured profit
