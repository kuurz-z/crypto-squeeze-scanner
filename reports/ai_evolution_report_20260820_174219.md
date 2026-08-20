# Dynamic Multi-Timeframe Strategy Evolution Report
*Generated on: 2026-08-20 17:42:19*

## 1. Executive Summary
- **Strategy Name**: `Squeeze_Momentum_Breakout`
- **Optimal Timeframe Selected**: `1h` (Evaluated: 5m, 15m, 1h, 4h)
- **Timeframe Switched**: `Yes`
- **Active Target RR**: `1:2.5 RR` (Minimum floor: >= 1:2)

## 2. Tested Parameter Benchmarks
```json
{
  "rvol_min": 1.25,
  "atr_sl_mult": 1.4,
  "target_rr": 2.5,
  "rsi_min_long": 50.0,
  "rsi_max_short": 50.0
}
```

## 3. Walk-Forward Diagnostic Metrics
- **Timeframe**: `1h`
- **Tested Out-of-Sample Trades**: `27`
- **Win Rate**: `81.48%`
- **Net Expectancy**: `+1.772 R`
- **Total Net Return**: `47.84 R`
