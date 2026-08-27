# Trade Record & Post-Mortem Diagnostic #1: BTCUSDT (LONG)
*Closed on: 2026-08-28 01:04:15*

## 1. Trade Execution Summary
- **Outcome**: `LOSS`
- **Realized PnL**: `$+2.62 USD` (+2.62 R)
- **Resulting Account Balance**: `$102.62 USD`
- **Entry Price**: `$100.0` | **Exit Price**: `$127.0`
- **Stop Loss**: `$127.0` | **Take Profit**: `$130.0` (1:3.0 RR)
- **Position Size**: `1.0 units` (Notional Value: `$0.00`)
- **Max Favorable Excursion (MFE)**: `+3.2 R`
- **Max Adverse Excursion (MAE)**: `-0.0 R`
- **Bars / Candles Held**: `4 bars`

## 2. Pre-Trade Quantitative Context (Why Entered)
- **Regime**: `N/A`
- **Technical Catalyst**: Test setup
- **Relative Volume Surge (RVOL)**: `N/Ax` (vs 20-bar SMA)
- **RSI (14)**: `N/A`
- **Momentum Oscillator**: `N/A`
- **Volatility (ATR14)**: `N/A`

## 3. Post-Trade Root Cause Diagnostic
- **Diagnostic Classification**: `ATR Trailing Stop Protected Profit`
- **Summary**: Dynamic trailing stop locked in +2.62R profit as momentum cooled off after peaking at +3.2R MFE.
- **Key Determining Factors**:
  - Dynamic stop protection prevented giving back gains
  - MFE reached +3.2R before trailing SL secured profit
