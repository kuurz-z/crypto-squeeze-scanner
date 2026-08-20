# Automated Crypto Simulation & Strategy Validation Report
*Generated on: 2026-08-20 16:56:12*

## 1. Strategy Performance Summary (Strict >= 1:3 RR)
| Strategy | Target RR | Total Trades | Win Rate | Profit Factor | Net Return (R) | Expectancy / Trade | Max Drawdown |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Squeeze_Momentum_Breakout** | 1:3.0 | 21 | 42.86% | 1.55 | 8.73R | +0.416R | 3.16R |
| **Liquidity_Sweep_Reversal** | 1:3.0 | 30 | 23.33% | 0.63 | -10.31R | +-0.344R | 16.04R |
| **Trend_Pullback_Confluence** | 1:3.0 | 54 | 42.59% | 0.78 | -15.49R | +-0.287R | 38.74R |

## 2. In-Depth Trade Diagnostics Log
Total Simulated Trades Logged: **105**

### 🔴 Trade #1: ETHUSDT LONG (-1.69R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$1933.05` (2026-08-19 20:30) | **Exit**: `$1929.13` (2026-08-19 21:30)
- **Stop Loss**: `$1929.13` | **Take Profit**: `$1944.82`
- **Performance**: Net R: `-1.69R` | Max Drawdown (MAE): `1.26R` | Max Run (MFE): `2.59R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `4.11` | RSI: `69.6` | ATR: `3.0171`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Failed Continuation / Reversal**
- *Diagnosis*: Trade initially moved favorable (+2.59R MFE), but stalled before the 3.0R target and completely reversed into stop loss.
- *Key Contributing Factors*: Reached 2.59R favorable before exhausting momentum, Failed to break key structural barrier
---
### 🔴 Trade #2: SOLUSDT LONG (-1.43R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$77.48` (2026-08-19 16:30) | **Exit**: `$77.23` (2026-08-19 17:30)
- **Stop Loss**: `$77.23` | **Take Profit**: `$78.23`
- **Performance**: Net R: `-1.43R` | Max Drawdown (MAE): `1.03R` | Max Run (MFE): `0.24R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `4.09` | RSI: `66.4` | ATR: `0.1936`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #3: XRPUSDT LONG (+2.19R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$1.01` (2026-08-19 20:30) | **Exit**: `$1.02` (2026-08-19 21:00)
- **Stop Loss**: `$1.01` | **Take Profit**: `$1.02`
- **Performance**: Net R: `+2.19R` | Max Drawdown (MAE): `0.51R` | Max Run (MFE): `3.13R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `3.61` | RSI: `66.2` | ATR: `0.0013`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 2 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.51R)
---
### 🔴 Trade #4: BNBUSDT LONG (-2.34R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$604.68` (2026-08-19 20:30) | **Exit**: `$604.05` (2026-08-19 21:00)
- **Stop Loss**: `$604.05` | **Take Profit**: `$606.57`
- **Performance**: Net R: `-2.34R` | Max Drawdown (MAE): `1.06R` | Max Run (MFE): `1.08R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `1.64` | RSI: `73.0` | ATR: `0.4857`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #5: BNBUSDT LONG (+2.62R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$630.18` (2026-08-20 14:45) | **Exit**: `$637.09` (2026-08-20 16:00)
- **Stop Loss**: `$627.88` | **Take Profit**: `$637.09`
- **Performance**: Net R: `+2.62R` | Max Drawdown (MAE): `0.96R` | Max Run (MFE): `5.72R` | Bars: `5`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `1.47` | RSI: `75.8` | ATR: `1.7729`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 5 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.96R), Volume surge confirmed direction
---
### 🔴 Trade #6: ZECUSDT LONG (-1.11R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$573.61` (2026-08-20 05:00) | **Exit**: `$565.97` (2026-08-20 05:30)
- **Stop Loss**: `$565.97` | **Take Profit**: `$596.53`
- **Performance**: Net R: `-1.11R` | Max Drawdown (MAE): `1.45R` | Max Run (MFE): `0.11R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `2.55` | RSI: `85.5` | ATR: `5.8771`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #7: LINKUSDT LONG (+2.87R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$9.92` (2026-08-19 23:30) | **Exit**: `$10.25` (2026-08-20 04:15)
- **Stop Loss**: `$9.81` | **Take Profit**: `$10.25`
- **Performance**: Net R: `+2.87R` | Max Drawdown (MAE): `0.69R` | Max Run (MFE): `3.3R` | Bars: `19`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `4.13` | RSI: `62.8` | ATR: `0.0841`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 19 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #8: SNDKBUSDT LONG (-1.2R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$1630.4` (2026-08-20 14:30) | **Exit**: `$1618.88` (2026-08-20 15:00)
- **Stop Loss**: `$1618.88` | **Take Profit**: `$1664.97`
- **Performance**: Net R: `-1.2R` | Max Drawdown (MAE): `1.32R` | Max Run (MFE): `0.05R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `4.59` | RSI: `72.0` | ATR: `8.8643`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #9: PEPEUSDT LONG (-1.19R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$3e-06` (2026-08-19 20:30) | **Exit**: `$3e-06` (2026-08-19 21:15)
- **Stop Loss**: `$3e-06` | **Take Profit**: `$3e-06`
- **Performance**: Net R: `-1.19R` | Max Drawdown (MAE): `1.03R` | Max Run (MFE): `0.51R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `2.75` | RSI: `63.6` | ATR: `0.0`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #10: PEPEUSDT LONG (+2.86R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$3e-06` (2026-08-19 22:45) | **Exit**: `$3e-06` (2026-08-19 23:15)
- **Stop Loss**: `$3e-06` | **Take Profit**: `$3e-06`
- **Performance**: Net R: `+2.86R` | Max Drawdown (MAE): `0.74R` | Max Run (MFE): `4.08R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `5.96` | RSI: `75.0` | ATR: `0.0`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 2 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.74R)
---
### 🔴 Trade #11: PEPEUSDT LONG (-1.1R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$3e-06` (2026-08-19 23:15) | **Exit**: `$3e-06` (2026-08-19 23:45)
- **Stop Loss**: `$3e-06` | **Take Profit**: `$3e-06`
- **Performance**: Net R: `-1.1R` | Max Drawdown (MAE): `1.28R` | Max Run (MFE): `0.26R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `7.2` | RSI: `88.9` | ATR: `0.0`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #12: PEPEUSDT LONG (+2.9R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$3e-06` (2026-08-20 05:00) | **Exit**: `$3e-06` (2026-08-20 09:45)
- **Stop Loss**: `$3e-06` | **Take Profit**: `$3e-06`
- **Performance**: Net R: `+2.9R` | Max Drawdown (MAE): `0.51R` | Max Run (MFE): `3.08R` | Bars: `19`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `5.2` | RSI: `88.9` | ATR: `0.0`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 19 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #13: PEPEUSDT LONG (+2.91R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$3e-06` (2026-08-20 16:00) | **Exit**: `$3e-06` (2026-08-20 16:30)
- **Stop Loss**: `$3e-06` | **Take Profit**: `$3e-06`
- **Performance**: Net R: `+2.91R` | Max Drawdown (MAE): `0.22R` | Max Run (MFE): `3.02R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `3.37` | RSI: `69.6` | ATR: `0.0`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 2 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.22R)
---
### 🟢 Trade #14: SUIUSDT LONG (+2.75R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$0.6704` (2026-08-19 22:45) | **Exit**: `$0.681877` (2026-08-19 23:00)
- **Stop Loss**: `$0.666574` | **Take Profit**: `$0.681877`
- **Performance**: Net R: `+2.75R` | Max Drawdown (MAE): `0.18R` | Max Run (MFE): `3.53R` | Bars: `1`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `6.34` | RSI: `71.3` | ATR: `0.0029`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 1 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.18R)
---
### 🟢 Trade #15: SUIUSDT LONG (+2.81R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$0.6824` (2026-08-19 23:00) | **Exit**: `$0.697415` (2026-08-19 23:15)
- **Stop Loss**: `$0.677395` | **Take Profit**: `$0.697415`
- **Performance**: Net R: `+2.81R` | Max Drawdown (MAE): `0.5R` | Max Run (MFE): `4.02R` | Bars: `1`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `6.46` | RSI: `82.0` | ATR: `0.0038`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 1 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.5R)
---
### 🔴 Trade #16: SUIUSDT LONG (-1.14R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$0.7001` (2026-08-19 23:15) | **Exit**: `$0.693089` (2026-08-19 23:45)
- **Stop Loss**: `$0.693089` | **Take Profit**: `$0.721132`
- **Performance**: Net R: `-1.14R` | Max Drawdown (MAE): `3.11R` | Max Run (MFE): `0.09R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `8.63` | RSI: `87.4` | ATR: `0.0054`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #17: TRUMPUSDT LONG (-1.53R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$1.42` (2026-08-19 20:30) | **Exit**: `$1.41` (2026-08-19 21:00)
- **Stop Loss**: `$1.41` | **Take Profit**: `$1.43`
- **Performance**: Net R: `-1.53R` | Max Drawdown (MAE): `1.62R` | Max Run (MFE): `0.81R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `1.41` | RSI: `56.0` | ATR: `0.0029`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #18: TRUMPUSDT LONG (+2.71R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$1.42` (2026-08-19 22:45) | **Exit**: `$1.44` (2026-08-19 23:15)
- **Stop Loss**: `$1.42` | **Take Profit**: `$1.44`
- **Performance**: Net R: `+2.71R` | Max Drawdown (MAE): `0.14R` | Max Run (MFE): `6.17R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `4.61` | RSI: `61.2` | ATR: `0.0054`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 2 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.14R), Volume surge confirmed direction
---
### 🔴 Trade #19: TRUMPUSDT LONG (-1.18R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$1.46` (2026-08-19 23:15) | **Exit**: `$1.45` (2026-08-19 23:45)
- **Stop Loss**: `$1.45` | **Take Profit**: `$1.49`
- **Performance**: Net R: `-1.18R` | Max Drawdown (MAE): `1.75R` | Max Run (MFE): `0.53R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `8.52` | RSI: `82.1` | ATR: `0.0088`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #20: XPLUSDT LONG (-0.43R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$0.08326` (2026-08-20 16:00) | **Exit**: `$0.08308` (2026-08-20 16:45)
- **Stop Loss**: `$0.082574` | **Take Profit**: `$0.085319`
- **Performance**: Net R: `-0.43R` | Max Drawdown (MAE): `0.99R` | Max Run (MFE): `0.42R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `2.79` | RSI: `68.8` | ATR: `0.0005`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #21: BCHUSDT LONG (-1.55R)
- **Strategy**: `Squeeze_Momentum_Breakout` | **Target R:R**: `1:3.0`
- **Entry**: `$204.7` (2026-08-19 20:30) | **Exit**: `$204.18` (2026-08-19 21:30)
- **Stop Loss**: `$204.18` | **Take Profit**: `$206.26`
- **Performance**: Net R: `-1.55R` | Max Drawdown (MAE): `1.35R` | Max Run (MFE): `0.58R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Bullish Trend & Volatility Expansion
- *Rationale*: Squeeze fired bullishly above BB upper band with volume surge
- *Metrics*: RVOL: `1.16` | RSI: `66.7` | ATR: `0.4`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #1: BTCUSDT SHORT (-1.41R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$69804.0` (2026-08-20 15:00) | **Exit**: `$70043.8` (2026-08-20 16:00)
- **Stop Loss**: `$70043.8` | **Take Profit**: `$69084.6`
- **Performance**: Net R: `-1.41R` | Max Drawdown (MAE): `6.51R` | Max Run (MFE): `1.24R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (69927.97) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.17` | RSI: `74.7` | ATR: `184.4036`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #2: XRPUSDT SHORT (-1.16R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$1.07` (2026-08-19 23:45) | **Exit**: `$1.08` (2026-08-20 04:15)
- **Stop Loss**: `$1.08` | **Take Profit**: `$1.04`
- **Performance**: Net R: `-1.16R` | Max Drawdown (MAE): `1.45R` | Max Run (MFE): `1.66R` | Bars: `18`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (1.0741) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.23` | RSI: `89.7` | ATR: `0.0095`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Failed Continuation / Reversal**
- *Diagnosis*: Trade initially moved favorable (+1.66R MFE), but stalled before the 3.0R target and completely reversed into stop loss.
- *Key Contributing Factors*: Reached 1.66R favorable before exhausting momentum, Failed to break key structural barrier
---
### 🔴 Trade #3: BNBUSDT SHORT (-1.71R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$604.28` (2026-08-19 20:45) | **Exit**: `$605.47` (2026-08-19 21:30)
- **Stop Loss**: `$605.47` | **Take Profit**: `$600.72`
- **Performance**: Net R: `-1.71R` | Max Drawdown (MAE): `1.32R` | Max Run (MFE): `0.23R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (604.68) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.64` | RSI: `68.3` | ATR: `0.5521`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #4: BNBUSDT SHORT (-0.37R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$639.93` (2026-08-20 16:15) | **Exit**: `$641.12` (2026-08-20 16:45)
- **Stop Loss**: `$645.51` | **Take Profit**: `$623.2`
- **Performance**: Net R: `-0.37R` | Max Drawdown (MAE): `0.44R` | Max Run (MFE): `0.33R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (643.37) and rejected aggressively with upper wick
- *Metrics*: RVOL: `4.98` | RSI: `76.8` | ATR: `3.0214`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 2 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #5: ZECUSDT SHORT (-1.21R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$512.58` (2026-08-19 21:00) | **Exit**: `$515.99` (2026-08-19 22:00)
- **Stop Loss**: `$515.99` | **Take Profit**: `$502.35`
- **Performance**: Net R: `-1.21R` | Max Drawdown (MAE): `1.34R` | Max Run (MFE): `0.89R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (514.49) and rejected aggressively with upper wick
- *Metrics*: RVOL: `4.55` | RSI: `67.3` | ATR: `2.1357`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #6: ZECUSDT SHORT (-1.11R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$550.46` (2026-08-20 00:00) | **Exit**: `$557.48` (2026-08-20 00:45)
- **Stop Loss**: `$557.48` | **Take Profit**: `$529.39`
- **Performance**: Net R: `-1.11R` | Max Drawdown (MAE): `1.36R` | Max Run (MFE): `0.06R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (553.5) and rejected aggressively with upper wick
- *Metrics*: RVOL: `7.8` | RSI: `94.1` | ATR: `7.0236`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #7: DOGEUSDT SHORT (-1.56R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.07014` (2026-08-19 16:45) | **Exit**: `$0.070316` (2026-08-19 20:30)
- **Stop Loss**: `$0.070316` | **Take Profit**: `$0.069612`
- **Performance**: Net R: `-1.56R` | Max Drawdown (MAE): `2.27R` | Max Run (MFE): `0.8R` | Bars: `15`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.0703) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.59` | RSI: `55.2` | ATR: `0.0001`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 15 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #8: DOGEUSDT SHORT (+2.81R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.07593` (2026-08-20 05:30) | **Exit**: `$0.074274` (2026-08-20 06:45)
- **Stop Loss**: `$0.076482` | **Take Profit**: `$0.074274`
- **Performance**: Net R: `+2.81R` | Max Drawdown (MAE): `0.85R` | Max Run (MFE): `3.5R` | Bars: `5`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.0762) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.22` | RSI: `90.2` | ATR: `0.0006`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 5 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.85R), Volume surge confirmed direction
---
### 🔴 Trade #9: PLUMEUSDT SHORT (-1.2R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.01249` (2026-08-19 16:15) | **Exit**: `$0.012579` (2026-08-19 16:30)
- **Stop Loss**: `$0.012579` | **Take Profit**: `$0.012222`
- **Performance**: Net R: `-1.2R` | Max Drawdown (MAE): `1.68R` | Max Run (MFE): `0.11R` | Bars: `1`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.0125) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.51` | RSI: `65.6` | ATR: `0.0001`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 1 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #10: REUSDT SHORT (-1.12R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.4114` (2026-08-19 18:45) | **Exit**: `$0.416193` (2026-08-19 19:15)
- **Stop Loss**: `$0.416193` | **Take Profit**: `$0.397021`
- **Performance**: Net R: `-1.12R` | Max Drawdown (MAE): `1.5R` | Max Run (MFE): `0.08R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.4148) and rejected aggressively with upper wick
- *Metrics*: RVOL: `5.58` | RSI: `73.0` | ATR: `0.0048`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #11: REUSDT SHORT (-1.11R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.4204` (2026-08-19 19:45) | **Exit**: `$0.425729` (2026-08-19 20:00)
- **Stop Loss**: `$0.425729` | **Take Profit**: `$0.404414`
- **Performance**: Net R: `-1.11R` | Max Drawdown (MAE): `1.48R` | Max Run (MFE): `0.08R` | Bars: `1`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.4213) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.83` | RSI: `82.6` | ATR: `0.0053`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 1 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #12: REUSDT SHORT (-1.1R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.4269` (2026-08-19 20:15) | **Exit**: `$0.432993` (2026-08-19 22:00)
- **Stop Loss**: `$0.432993` | **Take Profit**: `$0.408621`
- **Performance**: Net R: `-1.1R` | Max Drawdown (MAE): `1.36R` | Max Run (MFE): `1.76R` | Bars: `7`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.4283) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.48` | RSI: `86.5` | ATR: `0.0061`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Failed Continuation / Reversal**
- *Diagnosis*: Trade initially moved favorable (+1.76R MFE), but stalled before the 3.0R target and completely reversed into stop loss.
- *Key Contributing Factors*: Reached 1.76R favorable before exhausting momentum, Failed to break key structural barrier
---
### 🔴 Trade #13: REUSDT SHORT (-1.05R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.4956` (2026-08-20 00:45) | **Exit**: `$0.50935` (2026-08-20 02:00)
- **Stop Loss**: `$0.50935` | **Take Profit**: `$0.45435`
- **Performance**: Net R: `-1.05R` | Max Drawdown (MAE): `1.43R` | Max Run (MFE): `1.32R` | Bars: `5`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.5039) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.85` | RSI: `88.2` | ATR: `0.0112`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 5 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #14: LINKUSDT SHORT (-1.3R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$10.65` (2026-08-20 16:15) | **Exit**: `$10.7` (2026-08-20 16:45)
- **Stop Loss**: `$10.7` | **Take Profit**: `$10.5`
- **Performance**: Net R: `-1.3R` | Max Drawdown (MAE): `1.16R` | Max Run (MFE): `0.41R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (10.667) and rejected aggressively with upper wick
- *Metrics*: RVOL: `3.54` | RSI: `74.1` | ATR: `0.0489`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #15: SNDKBUSDT SHORT (+2.92R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$1684.25` (2026-08-19 21:15) | **Exit**: `$1592.71` (2026-08-19 21:45)
- **Stop Loss**: `$1714.76` | **Take Profit**: `$1592.71`
- **Performance**: Net R: `+2.92R` | Max Drawdown (MAE): `0.57R` | Max Run (MFE): `3.65R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (1706.99) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.27` | RSI: `69.8` | ATR: `22.3693`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 2 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.57R)
---
### 🔴 Trade #16: SNDKBUSDT SHORT (-1.18R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$1591.45` (2026-08-20 05:15) | **Exit**: `$1603.59` (2026-08-20 06:30)
- **Stop Loss**: `$1603.59` | **Take Profit**: `$1555.03`
- **Performance**: Net R: `-1.18R` | Max Drawdown (MAE): `1.25R` | Max Run (MFE): `0.56R` | Bars: `5`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (1598.36) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.69` | RSI: `66.9` | ATR: `12.1407`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 5 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #17: XAUTUSDT LONG (+1.7R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$4462.0` (2026-08-20 13:45) | **Exit**: `$4476.41` (2026-08-20 16:15)
- **Stop Loss**: `$4457.2` | **Take Profit**: `$4476.41`
- **Performance**: Net R: `+1.7R` | Max Drawdown (MAE): `0.29R` | Max Run (MFE): `3.79R` | Bars: `10`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bull Trap Clearance)
- *Rationale*: Price pierced 20-bar swing low (4459.29) and rejected aggressively with lower wick
- *Metrics*: RVOL: `1.28` | RSI: `35.7` | ATR: `4.8029`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 10 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #18: PEPEUSDT SHORT (-1.09R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$3e-06` (2026-08-20 08:45) | **Exit**: `$3e-06` (2026-08-20 09:45)
- **Stop Loss**: `$3e-06` | **Take Profit**: `$3e-06`
- **Performance**: Net R: `-1.09R` | Max Drawdown (MAE): `1.14R` | Max Run (MFE): `0.45R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.0) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.24` | RSI: `60.0` | ATR: `0.0`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #19: SUIUSDT SHORT (+2.83R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.7205` (2026-08-20 05:30) | **Exit**: `$0.702779` (2026-08-20 07:45)
- **Stop Loss**: `$0.726407` | **Take Profit**: `$0.702779`
- **Performance**: Net R: `+2.83R` | Max Drawdown (MAE): `0.74R` | Max Run (MFE): `3.1R` | Bars: `9`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.724) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.19` | RSI: `92.1` | ATR: `0.0059`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 9 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #20: TRUMPUSDT SHORT (-1.3R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$1.41` (2026-08-19 20:45) | **Exit**: `$1.42` (2026-08-19 22:45)
- **Stop Loss**: `$1.42` | **Take Profit**: `$1.39`
- **Performance**: Net R: `-1.3R` | Max Drawdown (MAE): `2.58R` | Max Run (MFE): `1.36R` | Bars: `8`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (1.416) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.98` | RSI: `56.0` | ATR: `0.0031`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 8 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #21: TRUMPUSDT SHORT (-1.09R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$1.52` (2026-08-20 04:15) | **Exit**: `$1.54` (2026-08-20 04:30)
- **Stop Loss**: `$1.54` | **Take Profit**: `$1.45`
- **Performance**: Net R: `-1.09R` | Max Drawdown (MAE): `1.26R` | Max Run (MFE): `0.22R` | Bars: `1`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (1.529) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.39` | RSI: `78.4` | ATR: `0.0143`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 1 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #22: TRUMPUSDT SHORT (-1.04R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$1.77` (2026-08-20 07:15) | **Exit**: `$1.83` (2026-08-20 07:45)
- **Stop Loss**: `$1.83` | **Take Profit**: `$1.59`
- **Performance**: Net R: `-1.04R` | Max Drawdown (MAE): `1.04R` | Max Run (MFE): `0.19R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (1.788) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.62` | RSI: `84.9` | ATR: `0.055`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #23: XPLUSDT SHORT (-1.33R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.0758` (2026-08-19 16:30) | **Exit**: `$0.076124` (2026-08-19 18:30)
- **Stop Loss**: `$0.076124` | **Take Profit**: `$0.074827`
- **Performance**: Net R: `-1.33R` | Max Drawdown (MAE): `1.17R` | Max Run (MFE): `0.74R` | Bars: `8`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.076) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.25` | RSI: `64.1` | ATR: `0.0003`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 8 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #24: XPLUSDT SHORT (-1.23R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.08172` (2026-08-20 09:45) | **Exit**: `$0.082221` (2026-08-20 11:45)
- **Stop Loss**: `$0.082221` | **Take Profit**: `$0.080216`
- **Performance**: Net R: `-1.23R` | Max Drawdown (MAE): `1.06R` | Max Run (MFE): `1.46R` | Bars: `8`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.0819) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.93` | RSI: `60.5` | ATR: `0.0005`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 8 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #25: XPLUSDT SHORT (-1.1R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.08188` (2026-08-20 12:00) | **Exit**: `$0.082991` (2026-08-20 16:00)
- **Stop Loss**: `$0.082991` | **Take Profit**: `$0.078547`
- **Performance**: Net R: `-1.1R` | Max Drawdown (MAE): `1.5R` | Max Run (MFE): `0.96R` | Bars: `16`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.0823) and rejected aggressively with upper wick
- *Metrics*: RVOL: `2.63` | RSI: `59.0` | ATR: `0.0006`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 16 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #26: BCHUSDT SHORT (-1.17R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$203.6` (2026-08-19 16:45) | **Exit**: `$205.25` (2026-08-19 22:30)
- **Stop Loss**: `$205.25` | **Take Profit**: `$198.65`
- **Performance**: Net R: `-1.17R` | Max Drawdown (MAE): `1.15R` | Max Run (MFE): `0.3R` | Bars: `23`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (203.9) and rejected aggressively with upper wick
- *Metrics*: RVOL: `3.33` | RSI: `58.8` | ATR: `0.5571`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 23 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #27: PAXGUSDT SHORT (-1.77R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$4495.26` (2026-08-20 03:30) | **Exit**: `$4503.42` (2026-08-20 04:15)
- **Stop Loss**: `$4503.42` | **Take Profit**: `$4470.78`
- **Performance**: Net R: `-1.77R` | Max Drawdown (MAE): `1.63R` | Max Run (MFE): `0.16R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (4496.54) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.13` | RSI: `54.2` | ATR: `8.1593`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #28: PAXGUSDT LONG (+1.78R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$4467.99` (2026-08-20 13:45) | **Exit**: `$4483.32` (2026-08-20 16:15)
- **Stop Loss**: `$4462.88` | **Take Profit**: `$4483.32`
- **Performance**: Net R: `+1.78R` | Max Drawdown (MAE): `0.17R` | Max Run (MFE): `3.52R` | Bars: `10`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bull Trap Clearance)
- *Rationale*: Price pierced 20-bar swing low (4466.01) and rejected aggressively with lower wick
- *Metrics*: RVOL: `1.13` | RSI: `30.4` | ATR: `5.11`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 10 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #29: ADAUSDT SHORT (+2.56R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.1755` (2026-08-19 20:45) | **Exit**: `$0.173829` (2026-08-19 21:45)
- **Stop Loss**: `$0.176057` | **Take Profit**: `$0.173829`
- **Performance**: Net R: `+2.56R` | Max Drawdown (MAE): `0.36R` | Max Run (MFE): `3.05R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bear Trap Clearance)
- *Rationale*: Price swept 20-bar swing high (0.1758) and rejected aggressively with upper wick
- *Metrics*: RVOL: `1.57` | RSI: `62.5` | ATR: `0.0006`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 4 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.36R)
---
### 🟢 Trade #30: ADAUSDT LONG (+2.8R)
- **Strategy**: `Liquidity_Sweep_Reversal` | **Target R:R**: `1:3.0`
- **Entry**: `$0.1826` (2026-08-20 12:00) | **Exit**: `$0.186393` (2026-08-20 16:00)
- **Stop Loss**: `$0.181336` | **Take Profit**: `$0.186393`
- **Performance**: Net R: `+2.8R` | Max Drawdown (MAE): `0.24R` | Max Run (MFE): `4.03R` | Bars: `16`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Liquidity Hunt Reversal (Bull Trap Clearance)
- *Rationale*: Price pierced 20-bar swing low (0.182) and rejected aggressively with lower wick
- *Metrics*: RVOL: `1.6` | RSI: `29.5` | ATR: `0.0013`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 16 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #1: BTCUSDT SHORT (-1.79R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$64413.95` (2026-08-19 16:45) | **Exit**: `$64528.64` (2026-08-19 19:00)
- **Stop Loss**: `$64528.64` | **Take Profit**: `$64069.88`
- **Performance**: Net R: `-1.79R` | Max Drawdown (MAE): `1.09R` | Max Run (MFE): `0.46R` | Bars: `9`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.54` | RSI: `53.5` | ATR: `81.9221`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 9 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #2: BTCUSDT SHORT (-2.22R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$64505.8` (2026-08-19 20:00) | **Exit**: `$64579.92` (2026-08-19 20:30)
- **Stop Loss**: `$64579.92` | **Take Profit**: `$64283.44`
- **Performance**: Net R: `-2.22R` | Max Drawdown (MAE): `5.96R` | Max Run (MFE): `0.33R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.57` | RSI: `57.1` | ATR: `52.9436`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #3: BTCUSDT LONG (+2.72R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$69190.35` (2026-08-20 11:30) | **Exit**: `$70222.88` (2026-08-20 16:00)
- **Stop Loss**: `$68846.17` | **Take Profit**: `$70222.88`
- **Performance**: Net R: `+2.72R` | Max Drawdown (MAE): `0.09R` | Max Run (MFE): `6.32R` | Bars: `18`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.82` | RSI: `38.9` | ATR: `245.84`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 18 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #4: ETHUSDT LONG (+2.44R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1918.99` (2026-08-19 18:30) | **Exit**: `$1933.49` (2026-08-19 20:30)
- **Stop Loss**: `$1914.16` | **Take Profit**: `$1933.49`
- **Performance**: Net R: `+2.44R` | Max Drawdown (MAE): `0.08R` | Max Run (MFE): `3.0R` | Bars: `8`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.23` | RSI: `46.4` | ATR: `3.4521`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 8 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #5: ETHUSDT LONG (+2.6R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$2234.52` (2026-08-20 11:15) | **Exit**: `$2284.0` (2026-08-20 16:45)
- **Stop Loss**: `$2216.64` | **Take Profit**: `$2288.16`
- **Performance**: Net R: `+2.6R` | Max Drawdown (MAE): `0.0R` | Max Run (MFE): `2.95R` | Bars: `22`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `1.03` | RSI: `39.8` | ATR: `12.7721`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Time-Horizon PnL Capture**
- *Diagnosis*: Position closed in profit (+2.6R) at maximum trade horizon.
- *Key Contributing Factors*: Volume surge confirmed direction
---
### 🔴 Trade #6: SOLUSDT LONG (-1.17R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$85.07` (2026-08-20 09:30) | **Exit**: `$84.36` (2026-08-20 11:00)
- **Stop Loss**: `$84.36` | **Take Profit**: `$87.21`
- **Performance**: Net R: `-1.17R` | Max Drawdown (MAE): `1.49R` | Max Run (MFE): `0.53R` | Bars: `6`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.4` | RSI: `38.3` | ATR: `0.5093`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 6 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #7: SOLUSDT LONG (+2.77R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$84.62` (2026-08-20 12:00) | **Exit**: `$86.19` (2026-08-20 15:45)
- **Stop Loss**: `$84.1` | **Take Profit**: `$86.19`
- **Performance**: Net R: `+2.77R` | Max Drawdown (MAE): `0.38R` | Max Run (MFE): `3.02R` | Bars: `15`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.44` | RSI: `35.1` | ATR: `0.3743`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 15 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #8: XRPUSDT LONG (+2.4R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1.0` (2026-08-19 18:15) | **Exit**: `$1.01` (2026-08-19 20:45)
- **Stop Loss**: `$1.0` | **Take Profit**: `$1.01`
- **Performance**: Net R: `+2.4R` | Max Drawdown (MAE): `0.17R` | Max Run (MFE): `3.62R` | Bars: `10`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.59` | RSI: `47.9` | ATR: `0.0017`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 10 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #9: XRPUSDT LONG (+2.77R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1.1` (2026-08-20 12:45) | **Exit**: `$1.12` (2026-08-20 16:00)
- **Stop Loss**: `$1.09` | **Take Profit**: `$1.12`
- **Performance**: Net R: `+2.77R` | Max Drawdown (MAE): `0.01R` | Max Run (MFE): `4.31R` | Bars: `13`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.77` | RSI: `35.9` | ATR: `0.0049`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 13 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #10: BNBUSDT SHORT (-2.16R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$602.78` (2026-08-19 16:45) | **Exit**: `$603.51` (2026-08-19 20:30)
- **Stop Loss**: `$603.51` | **Take Profit**: `$600.6`
- **Performance**: Net R: `-2.16R` | Max Drawdown (MAE): `2.61R` | Max Run (MFE): `1.06R` | Bars: `15`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `1.23` | RSI: `59.6` | ATR: `0.52`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 15 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #11: BNBUSDT LONG (+2.65R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$615.45` (2026-08-20 03:30) | **Exit**: `$622.74` (2026-08-20 04:45)
- **Stop Loss**: `$613.02` | **Take Profit**: `$622.74`
- **Performance**: Net R: `+2.65R` | Max Drawdown (MAE): `0.07R` | Max Run (MFE): `3.77R` | Bars: `5`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `1.02` | RSI: `43.5` | ATR: `1.7364`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 5 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.07R), Volume surge confirmed direction
---
### 🔴 Trade #12: BNBUSDT LONG (-1.31R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$625.35` (2026-08-20 10:30) | **Exit**: `$622.56` (2026-08-20 11:00)
- **Stop Loss**: `$622.56` | **Take Profit**: `$633.72`
- **Performance**: Net R: `-1.31R` | Max Drawdown (MAE): `1.1R` | Max Run (MFE): `0.09R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.51` | RSI: `39.9` | ATR: `1.9936`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🟢 Trade #13: BNBUSDT LONG (+2.69R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$625.14` (2026-08-20 11:30) | **Exit**: `$633.63` (2026-08-20 16:00)
- **Stop Loss**: `$622.31` | **Take Profit**: `$633.63`
- **Performance**: Net R: `+2.69R` | Max Drawdown (MAE): `0.22R` | Max Run (MFE): `6.44R` | Bars: `18`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.72` | RSI: `39.8` | ATR: `2.0221`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 18 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #14: ZECUSDT SHORT (-1.23R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$507.9` (2026-08-19 16:45) | **Exit**: `$510.94` (2026-08-19 20:30)
- **Stop Loss**: `$510.94` | **Take Profit**: `$498.79`
- **Performance**: Net R: `-1.23R` | Max Drawdown (MAE): `1.68R` | Max Run (MFE): `0.98R` | Bars: `15`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `1.79` | RSI: `62.9` | ATR: `2.1693`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 15 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #15: ZECUSDT LONG (-1.13R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$563.1` (2026-08-20 09:30) | **Exit**: `$557.05` (2026-08-20 10:45)
- **Stop Loss**: `$557.05` | **Take Profit**: `$581.24`
- **Performance**: Net R: `-1.13R` | Max Drawdown (MAE): `1.12R` | Max Run (MFE): `0.23R` | Bars: `5`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.32` | RSI: `38.5` | ATR: `4.32`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 5 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #16: ZECUSDT LONG (+2.06R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$552.8` (2026-08-20 12:45) | **Exit**: `$562.71` (2026-08-20 16:45)
- **Stop Loss**: `$548.36` | **Take Profit**: `$566.12`
- **Performance**: Net R: `+2.06R` | Max Drawdown (MAE): `0.48R` | Max Run (MFE): `2.92R` | Bars: `16`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.76` | RSI: `35.5` | ATR: `3.1707`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Time-Horizon PnL Capture**
- *Diagnosis*: Position closed in profit (+2.06R) at maximum trade horizon.
- *Key Contributing Factors*: Volume surge confirmed direction
---
### 🔴 Trade #17: DOGEUSDT SHORT (-1.55R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.07014` (2026-08-19 16:45) | **Exit**: `$0.070318` (2026-08-19 20:30)
- **Stop Loss**: `$0.070318` | **Take Profit**: `$0.069606`
- **Performance**: Net R: `-1.55R` | Max Drawdown (MAE): `2.25R` | Max Run (MFE): `0.79R` | Bars: `15`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `1.59` | RSI: `55.2` | ATR: `0.0001`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 15 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #18: DOGEUSDT LONG (+2.82R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.07484` (2026-08-20 11:30) | **Exit**: `$0.076595` (2026-08-20 16:15)
- **Stop Loss**: `$0.074255` | **Take Profit**: `$0.076595`
- **Performance**: Net R: `+2.82R` | Max Drawdown (MAE): `0.67R` | Max Run (MFE): `3.35R` | Bars: `19`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.53` | RSI: `46.5` | ATR: `0.0004`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 19 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #19: PLUMEUSDT LONG (-1.09R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.01284` (2026-08-19 21:30) | **Exit**: `$0.01265` (2026-08-19 22:15)
- **Stop Loss**: `$0.01265` | **Take Profit**: `$0.01341`
- **Performance**: Net R: `-1.09R` | Max Drawdown (MAE): `1.21R` | Max Run (MFE): `0.0R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `1.25` | RSI: `47.1` | ATR: `0.0001`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #20: PLUMEUSDT LONG (-1.1R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.01276` (2026-08-19 22:45) | **Exit**: `$0.012581` (2026-08-20 14:45)
- **Stop Loss**: `$0.012581` | **Take Profit**: `$0.013297`
- **Performance**: Net R: `-1.1R` | Max Drawdown (MAE): `2.07R` | Max Run (MFE): `2.91R` | Bars: `64`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.75` | RSI: `35.7` | ATR: `0.0001`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Failed Continuation / Reversal**
- *Diagnosis*: Trade initially moved favorable (+2.91R MFE), but stalled before the 3.0R target and completely reversed into stop loss.
- *Key Contributing Factors*: Reached 2.91R favorable before exhausting momentum, Failed to break key structural barrier
---
### 🔴 Trade #21: REUSDT SHORT (-1.18R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.3939` (2026-08-19 16:00) | **Exit**: `$0.39701` (2026-08-19 17:00)
- **Stop Loss**: `$0.39701` | **Take Profit**: `$0.38457`
- **Performance**: Net R: `-1.18R` | Max Drawdown (MAE): `3.99R` | Max Run (MFE): `0.96R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.59` | RSI: `48.7` | ATR: `0.0022`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #22: REUSDT LONG (+1.01R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.523` (2026-08-20 06:45) | **Exit**: `$0.5451` (2026-08-20 16:45)
- **Stop Loss**: `$0.50171` | **Take Profit**: `$0.58687`
- **Performance**: Net R: `+1.01R` | Max Drawdown (MAE): `0.67R` | Max Run (MFE): `2.46R` | Bars: `40`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.8` | RSI: `42.6` | ATR: `0.0152`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Time-Horizon PnL Capture**
- *Diagnosis*: Position closed in profit (+1.01R) at maximum trade horizon.
- *Key Contributing Factors*: Volume surge confirmed direction
---
### 🟢 Trade #23: LINKUSDT LONG (+2.79R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$9.7` (2026-08-19 22:00) | **Exit**: `$9.89` (2026-08-19 23:15)
- **Stop Loss**: `$9.63` | **Take Profit**: `$9.89`
- **Performance**: Net R: `+2.79R` | Max Drawdown (MAE): `0.39R` | Max Run (MFE): `5.77R` | Bars: `5`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `1.7` | RSI: `41.9` | ATR: `0.0471`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 5 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.39R), Volume surge confirmed direction
---
### 🔴 Trade #24: LINKUSDT LONG (-1.16R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$10.54` (2026-08-20 10:00) | **Exit**: `$10.45` (2026-08-20 11:00)
- **Stop Loss**: `$10.45` | **Take Profit**: `$10.81`
- **Performance**: Net R: `-1.16R` | Max Drawdown (MAE): `1.94R` | Max Run (MFE): `0.0R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.28` | RSI: `38.0` | ATR: `0.0645`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #25: LINKUSDT LONG (+2.84R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$10.43` (2026-08-20 11:15) | **Exit**: `$10.7` (2026-08-20 16:45)
- **Stop Loss**: `$10.34` | **Take Profit**: `$10.7`
- **Performance**: Net R: `+2.84R` | Max Drawdown (MAE): `0.24R` | Max Run (MFE): `3.04R` | Bars: `22`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.74` | RSI: `37.2` | ATR: `0.0641`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 22 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #26: SNDKBUSDT SHORT (-1.16R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1597.38` (2026-08-20 08:00) | **Exit**: `$1611.25` (2026-08-20 08:45)
- **Stop Loss**: `$1611.25` | **Take Profit**: `$1555.77`
- **Performance**: Net R: `-1.16R` | Max Drawdown (MAE): `1.05R` | Max Run (MFE): `0.8R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `2.55` | RSI: `61.7` | ATR: `9.9079`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #27: SNDKBUSDT SHORT (-1.13R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1600.79` (2026-08-20 09:00) | **Exit**: `$1617.88` (2026-08-20 14:30)
- **Stop Loss**: `$1617.88` | **Take Profit**: `$1549.52`
- **Performance**: Net R: `-1.13R` | Max Drawdown (MAE): `1.99R` | Max Run (MFE): `0.49R` | Bars: `22`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.71` | RSI: `58.6` | ATR: `12.2064`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 22 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #28: UUSDT LONG (-9.75R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1.0` (2026-08-19 16:00) | **Exit**: `$1.0` (2026-08-19 16:30)
- **Stop Loss**: `$1.0` | **Take Profit**: `$1.0`
- **Performance**: Net R: `-9.75R` | Max Drawdown (MAE): `1.25R` | Max Run (MFE): `0.0R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.33` | RSI: `50.0` | ATR: `0.0001`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #29: UUSDT LONG (-8.78R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1.0` (2026-08-19 17:15) | **Exit**: `$1.0` (2026-08-19 18:00)
- **Stop Loss**: `$1.0` | **Take Profit**: `$1.0`
- **Performance**: Net R: `-8.78R` | Max Drawdown (MAE): `1.11R` | Max Run (MFE): `0.56R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `2.09` | RSI: `42.9` | ATR: `0.0001`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #30: UUSDT SHORT (-6.6R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.9998` (2026-08-20 08:00) | **Exit**: `$1.0` (2026-08-20 09:00)
- **Stop Loss**: `$1.0` | **Take Profit**: `$0.99905`
- **Performance**: Net R: `-6.6R` | Max Drawdown (MAE): `1.6R` | Max Run (MFE): `0.0R` | Bars: `4`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.32` | RSI: `60.0` | ATR: `0.0002`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 4 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #31: UUSDT SHORT (-6.81R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.9999` (2026-08-20 09:30) | **Exit**: `$1.0` (2026-08-20 16:45)
- **Stop Loss**: `$1.0` | **Take Profit**: `$0.99924`
- **Performance**: Net R: `-6.81R` | Max Drawdown (MAE): `0.91R` | Max Run (MFE): `0.45R` | Bars: `29`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.33` | RSI: `62.5` | ATR: `0.0002`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 29 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #32: XAUTUSDT LONG (+2.43R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4469.3` (2026-08-20 02:30) | **Exit**: `$4502.13` (2026-08-20 04:45)
- **Stop Loss**: `$4458.36` | **Take Profit**: `$4502.13`
- **Performance**: Net R: `+2.43R` | Max Drawdown (MAE): `0.03R` | Max Run (MFE): `3.09R` | Bars: `9`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.59` | RSI: `51.6` | ATR: `7.8157`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 9 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #33: XAUTUSDT LONG (-1.88R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4492.23` (2026-08-20 08:00) | **Exit**: `$4485.08` (2026-08-20 08:30)
- **Stop Loss**: `$4485.08` | **Take Profit**: `$4513.69`
- **Performance**: Net R: `-1.88R` | Max Drawdown (MAE): `1.53R` | Max Run (MFE): `0.68R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `4.03` | RSI: `41.3` | ATR: `5.11`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #34: XAUTUSDT LONG (-1.59R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4474.02` (2026-08-20 11:15) | **Exit**: `$4463.43` (2026-08-20 13:15)
- **Stop Loss**: `$4463.43` | **Take Profit**: `$4505.78`
- **Performance**: Net R: `-1.59R` | Max Drawdown (MAE): `1.02R` | Max Run (MFE): `0.73R` | Bars: `8`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.13` | RSI: `37.5` | ATR: `7.5629`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 8 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #35: XAUTUSDT LONG (+0.29R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4462.0` (2026-08-20 13:45) | **Exit**: `$4470.21` (2026-08-20 16:45)
- **Stop Loss**: `$4455.28` | **Take Profit**: `$4482.17`
- **Performance**: Net R: `+0.29R` | Max Drawdown (MAE): `0.21R` | Max Run (MFE): `2.71R` | Bars: `12`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `1.28` | RSI: `35.7` | ATR: `4.8029`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Time-Horizon PnL Capture**
- *Diagnosis*: Position closed in profit (+0.29R) at maximum trade horizon.
- *Key Contributing Factors*: Volume surge confirmed direction
---
### 🔴 Trade #36: PEPEUSDT SHORT (-1.17R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$3e-06` (2026-08-19 19:30) | **Exit**: `$3e-06` (2026-08-19 20:15)
- **Stop Loss**: `$3e-06` | **Take Profit**: `$3e-06`
- **Performance**: Net R: `-1.17R` | Max Drawdown (MAE): `1.43R` | Max Run (MFE): `0.0R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.25` | RSI: `50.0` | ATR: `0.0`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #37: SUIUSDT LONG (-1.45R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.658` (2026-08-19 19:45) | **Exit**: `$0.65593` (2026-08-19 20:30)
- **Stop Loss**: `$0.65593` | **Take Profit**: `$0.66421`
- **Performance**: Net R: `-1.45R` | Max Drawdown (MAE): `1.16R` | Max Run (MFE): `0.53R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.3` | RSI: `48.6` | ATR: `0.0015`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 3 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #38: SUIUSDT LONG (-1.14R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.7073` (2026-08-20 09:30) | **Exit**: `$0.70042` (2026-08-20 11:00)
- **Stop Loss**: `$0.70042` | **Take Profit**: `$0.72794`
- **Performance**: Net R: `-1.14R` | Max Drawdown (MAE): `2.44R` | Max Run (MFE): `0.44R` | Bars: `6`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.4` | RSI: `37.5` | ATR: `0.0049`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 6 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #39: SUIUSDT LONG (+2.84R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.6996` (2026-08-20 11:30) | **Exit**: `$0.71772` (2026-08-20 16:15)
- **Stop Loss**: `$0.69356` | **Take Profit**: `$0.71772`
- **Performance**: Net R: `+2.84R` | Max Drawdown (MAE): `0.45R` | Max Run (MFE): `3.06R` | Bars: `19`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.38` | RSI: `35.7` | ATR: `0.0043`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 19 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #40: TRUMPUSDT LONG (+2.65R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1.41` (2026-08-19 22:00) | **Exit**: `$1.43` (2026-08-19 22:45)
- **Stop Loss**: `$1.4` | **Take Profit**: `$1.43`
- **Performance**: Net R: `+2.65R` | Max Drawdown (MAE): `0.36R` | Max Run (MFE): `3.75R` | Bars: `3`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `1.26` | RSI: `45.9` | ATR: `0.004`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Impulsive Momentum Expansion**
- *Diagnosis*: Rapid target hit in 3 bars. Strong order flow propelled price directly to 3.0R target without significant drawdown.
- *Key Contributing Factors*: High institutional velocity, Low adverse excursion (MAE: 0.36R)
---
### 🟢 Trade #41: TRUMPUSDT LONG (+0.1R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$1.68` (2026-08-20 11:15) | **Exit**: `$1.69` (2026-08-20 16:45)
- **Stop Loss**: `$1.61` | **Take Profit**: `$1.9`
- **Performance**: Net R: `+0.1R` | Max Drawdown (MAE): `0.81R` | Max Run (MFE): `0.25R` | Bars: `22`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.35` | RSI: `36.5` | ATR: `0.0509`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Time-Horizon PnL Capture**
- *Diagnosis*: Position closed in profit (+0.1R) at maximum trade horizon.
- *Key Contributing Factors*: Volume surge confirmed direction
---
### 🟢 Trade #42: XPLUSDT LONG (+2.3R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.08069` (2026-08-20 07:15) | **Exit**: `$0.08308` (2026-08-20 16:45)
- **Stop Loss**: `$0.079699` | **Take Profit**: `$0.083663`
- **Performance**: Net R: `+2.3R` | Max Drawdown (MAE): `0.39R` | Max Run (MFE): `2.89R` | Bars: `38`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.24` | RSI: `48.3` | ATR: `0.0007`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Time-Horizon PnL Capture**
- *Diagnosis*: Position closed in profit (+2.3R) at maximum trade horizon.
- *Key Contributing Factors*: Volume surge confirmed direction
---
### 🔴 Trade #43: BCHUSDT SHORT (-1.46R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$202.9` (2026-08-19 16:00) | **Exit**: `$203.52` (2026-08-19 16:30)
- **Stop Loss**: `$203.52` | **Take Profit**: `$201.04`
- **Performance**: Net R: `-1.46R` | Max Drawdown (MAE): `1.61R` | Max Run (MFE): `0.32R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `0.25` | RSI: `48.1` | ATR: `0.4429`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #44: BCHUSDT SHORT (-1.37R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$203.6` (2026-08-19 16:45) | **Exit**: `$204.38` (2026-08-19 20:30)
- **Stop Loss**: `$204.38` | **Take Profit**: `$201.26`
- **Performance**: Net R: `-1.37R` | Max Drawdown (MAE): `1.41R` | Max Run (MFE): `0.64R` | Bars: `15`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bearish Trend Pullback
- *Rationale*: Retracement into EMA20/50 resistance band with RSI overbought reset and bearish candle confirmation
- *Metrics*: RVOL: `3.33` | RSI: `58.8` | ATR: `0.5571`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 15 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #45: BCHUSDT LONG (+2.86R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$206.2` (2026-08-20 02:30) | **Exit**: `$212.2` (2026-08-20 05:00)
- **Stop Loss**: `$204.2` | **Take Profit**: `$212.2`
- **Performance**: Net R: `+2.86R` | Max Drawdown (MAE): `0.25R` | Max Run (MFE): `3.35R` | Bars: `10`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.04` | RSI: `46.7` | ATR: `1.4286`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 10 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #46: BCHUSDT LONG (-1.17R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$211.4` (2026-08-20 09:30) | **Exit**: `$209.67` (2026-08-20 11:00)
- **Stop Loss**: `$209.67` | **Take Profit**: `$216.59`
- **Performance**: Net R: `-1.17R` | Max Drawdown (MAE): `1.68R` | Max Run (MFE): `0.52R` | Bars: `6`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.15` | RSI: `47.6` | ATR: `1.2357`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 6 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #47: BCHUSDT LONG (+2.78R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$211.2` (2026-08-20 12:00) | **Exit**: `$215.16` (2026-08-20 16:00)
- **Stop Loss**: `$209.88` | **Take Profit**: `$215.16`
- **Performance**: Net R: `+2.78R` | Max Drawdown (MAE): `0.38R` | Max Run (MFE): `4.09R` | Bars: `16`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.13` | RSI: `37.1` | ATR: `0.9429`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 16 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🟢 Trade #48: PAXGUSDT LONG (+2.47R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4479.62` (2026-08-20 02:30) | **Exit**: `$4514.94` (2026-08-20 05:00)
- **Stop Loss**: `$4467.85` | **Take Profit**: `$4514.94`
- **Performance**: Net R: `+2.47R` | Max Drawdown (MAE): `0.12R` | Max Run (MFE): `3.24R` | Bars: `10`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.82` | RSI: `51.4` | ATR: `8.4093`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 10 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---
### 🔴 Trade #49: PAXGUSDT LONG (-1.79R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4501.39` (2026-08-20 08:00) | **Exit**: `$4493.45` (2026-08-20 08:30)
- **Stop Loss**: `$4493.45` | **Take Profit**: `$4525.22`
- **Performance**: Net R: `-1.79R` | Max Drawdown (MAE): `1.57R` | Max Run (MFE): `0.61R` | Bars: `2`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `3.32` | RSI: `40.7` | ATR: `5.6729`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Immediate Liquidity Wick / Trap**
- *Diagnosis*: Quick stop-out within 2 bars. Invalidation level was breached almost immediately by aggressive counter-flow.
- *Key Contributing Factors*: Fast hostile volume against entry position, Possible false breakout or front-running liquidity sweep
---
### 🔴 Trade #50: PAXGUSDT LONG (-1.54R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4484.47` (2026-08-20 11:30) | **Exit**: `$4472.82` (2026-08-20 13:00)
- **Stop Loss**: `$4472.82` | **Take Profit**: `$4519.44`
- **Performance**: Net R: `-1.54R` | Max Drawdown (MAE): `1.07R` | Max Run (MFE): `0.16R` | Bars: `6`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.83` | RSI: `35.4` | ATR: `8.325`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 6 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #51: PAXGUSDT LONG (-1.31R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$4478.77` (2026-08-20 14:00) | **Exit**: `$4474.91` (2026-08-20 16:45)
- **Stop Loss**: `$4471.03` | **Take Profit**: `$4501.99`
- **Performance**: Net R: `-1.31R` | Max Drawdown (MAE): `0.98R` | Max Run (MFE): `0.93R` | Bars: `11`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.85` | RSI: `49.8` | ATR: `5.5286`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 11 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #52: ADAUSDT LONG (-1.31R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.1748` (2026-08-19 19:00) | **Exit**: `$0.17401` (2026-08-19 21:30)
- **Stop Loss**: `$0.17401` | **Take Profit**: `$0.17717`
- **Performance**: Net R: `-1.31R` | Max Drawdown (MAE): `1.01R` | Max Run (MFE): `1.39R` | Bars: `10`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `1.11` | RSI: `45.8` | ATR: `0.0006`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 10 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🔴 Trade #53: ADAUSDT LONG (-1.12R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.1869` (2026-08-20 09:30) | **Exit**: `$0.18478` (2026-08-20 11:00)
- **Stop Loss**: `$0.18478` | **Take Profit**: `$0.19326`
- **Performance**: Net R: `-1.12R` | Max Drawdown (MAE): `2.08R` | Max Run (MFE): `0.47R` | Bars: `6`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.28` | RSI: `35.1` | ATR: `0.0015`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Regime Resistance / Range Consolidation**
- *Diagnosis*: Position was caught in choppy chop/counter-trend pressure over 6 bars and eventually triggered 1R SL.
- *Key Contributing Factors*: Lack of sustained volume follow-through
---
### 🟢 Trade #54: ADAUSDT LONG (+2.85R)
- **Strategy**: `Trend_Pullback_Confluence` | **Target R:R**: `1:3.0`
- **Entry**: `$0.1831` (2026-08-20 12:15) | **Exit**: `$0.18814` (2026-08-20 16:15)
- **Stop Loss**: `$0.18142` | **Take Profit**: `$0.18814`
- **Performance**: Net R: `+2.85R` | Max Drawdown (MAE): `0.48R` | Max Run (MFE): `3.15R` | Bars: `16`

**Pre-Trade Analysis (Why Entered):**
- *Regime*: Structured Bullish Trend Pullback
- *Rationale*: Retracement into EMA20/50 support band with RSI reset and bullish candle confirmation
- *Metrics*: RVOL: `0.43` | RSI: `36.0` | ATR: `0.0012`

**Post-Trade Diagnostic (Root Cause & Outcome):**
- *Catalyst Category*: **Sustained Trend Continuation**
- *Diagnosis*: Trade navigated intermediate pullbacks and successfully reached full 3.0R extension over 16 bars.
- *Key Contributing Factors*: Trend structure remained intact above invalidation level, Volume surge confirmed direction
---