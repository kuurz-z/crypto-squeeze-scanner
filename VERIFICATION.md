# Execution repair verification

Verified locally on 2026-09-22 with Python 3.14 on Windows.

| Check | Result |
| --- | --- |
| `python -B verify_repairs.py --pattern test*.py` | 165 tests passed, 11.953 seconds |
| `node --check static/js/app.js` | Passed |
| Python AST parsing of all 30 root Python files | Passed |
| `git diff --check` | Passed |
| User ledger/database/report integrity | All 444 protected files unchanged |

Aggregate SHA-256 before and after:
`b4b353fb4261d36a29399b35ac29f5355d2c8575e164a2c6d3c9204c4bc52564`.
Existing workspace edits, including pre-existing report changes, were retained.

The suite covers repeated polling, restart and entry guards, stale observations,
missed-candle recovery, required completed anchors, future-data isolation,
Binance pagination and close timestamps, long/short ambiguous candles and gaps,
deferred stop activation, partial/final fill quantities and costs, wallet/API/
snapshot reconciliation, transaction rollback, initial-loss drawdown, report-only
optimizers, and final-test selection/cache isolation. The obsolete synthetic
80% win-rate requirement was replaced with execution and truthful-reporting tests.

Tests use disposable accounts and databases. Imports do not instantiate the
production bot. External HTTP is disabled and inherited production database
settings are cleared. The test run emitted one Starlette/httpx deprecation
warning; it did not affect results.

SQLite persistence and isolated API behavior were exercised. A live PostgreSQL
server and a live Binance session were not used for verification. Historical
fills remain a conservative candle approximation; fees and slippage are modeling
assumptions. No profitability claim follows from these software tests.

Restart the local application with `python app.py` to load the repaired code.
The first startup persists the new forward-test identity; subsequent entries
carry that identity and their configuration. Previously open legacy positions
retain legacy accounting and are excluded from the cohort.
