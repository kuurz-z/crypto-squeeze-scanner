# Trade Record & Post-Mortem Diagnostic #1: BTCUSDT (LONG)
*Closed on: 2026-08-21 00:55:00*

## 1. Trade Execution Summary
- **Outcome**: `LOSS`
- **Realized PnL**: `$+0.87 USD` (+0.87 R)
- **Resulting Account Balance**: `$100.87 USD`
- **Entry Price**: `$100.0` | **Exit Price**: `$109.5`
- **Stop Loss**: `$109.5` | **Take Profit**: `$120.0` (1:2.0 RR)
- **Position Size**: `1.0 units` (Notional Value: `$0.00`)
- **Max Favorable Excursion (MFE)**: `+1.65 R`
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
- **Summary**: Dynamic trailing stop locked in +0.87R profit as momentum cooled off after peaking at +1.65R MFE.
- **Key Determining Factors**:
  - Dynamic stop protection prevented giving back gains
  - MFE reached +1.65R before trailing SL secured profit
