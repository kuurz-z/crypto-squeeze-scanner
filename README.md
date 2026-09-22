# Crypto scanner and paper forward test

The paper account defaults to **Trend Pullback Confluence, 15-minute candles,
$1 original risk per trade**, retaining existing parameters, position limits and
exit milestones. All optimizers are **report-only**. Profitability is **not
validated**; subsequent paper trades measure it.

## Run locally

```powershell
python -m pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:8000. Startup starts the paper worker. Imports alone do not
create a bot or touch its ledger. No exchange orders are placed. Existing API
routes remain available.

## Execution and accounting

- Signals require completed candles and 200 bars of indicator history.
  Completed anchors are 5m → 30m, 15m → 1h, 30m → 4h. Neutral is allowed;
  missing, stale and opposing anchors reject entries.
- Simulations enter at the next candle's open; paper entries use the next
  observed price. Stops and targets use the slipped entry.
- A shared engine resolves existing stops before ambiguous targets, adverse
  opening gaps at the open, and standing targets before new protective states.
  Raised stops apply only to subsequent observations; old wicks are not reused.
- Candle guards persist across restart. Missed completed candles are fetched
  and processed chronologically. Historical execution is a **conservative
  candle approximation**, not a tick-level reconstruction.
- Default modeling assumptions are **0.05% fee and 0.02% adverse slippage per
  fill**. Optional constructor arguments `fee_pct` and `slippage_pct` use
  percentage units. Slippage changes each fill price once; fees apply to
  executed notional. Funding and borrowing costs are not modeled.
- Entry, partial and final fills have separate quantities and cash flows.
  Partial proceeds are credited once; final closure credits the remainder.
  Exit reason and net financial outcome are separate. Slippage in the cost
  breakdown is already included in PnL.

## Persistence and migration

`portfolio_snapshot.json` and the database store complete version-2 revisions:
wallet, positions, trades, configuration, forward-test ID and execution guards.
Database writes are transactional; JSON replacement is atomic. Recovery uses
the newest valid complete revision without combining legacy files. If both
canonical stores fail, entries are disabled.

SQLite/PostgreSQL trades have a nullable `record_json` column. Legacy rows
retain available fields without invented costs or partial fills. Positions
already open during migration retain legacy accounting and are excluded from
the new cohort. Manual configuration changes start a separate forward-test ID.

The dashboard separates cohort net PnL, costs, closed-trade expectancy,
cash-flow drawdown, sample size and rejection reasons from unverified history.
Drawdown includes initial equity, entry fees and partial cash flows; it is not
an intrabar mark-to-market estimate. Empty performance shows **Not validated**.

## Research evaluations

Every mode uses common chronological **60% training / 20% validation / 20%
final-test** windows across symbols and timeframes, with earlier candles used
only for warmup. Windows start flat; remaining positions close at the final
price with costs and reason `WINDOW_END`, reported separately.

Candidates freeze before scoring. Existing sample-size, profit-factor and
expectancy screens remain; win rate is descriptive. Rank by net expectancy,
then lower drawdown. Only the selected candidate and incumbent reach the
final window. The persistent evaluation ledger reserves consumed holdouts and
caches repeats; overlapping final windows cannot select new candidates.
Keep that ledger with the experiment. Passing remains a research result and
never changes the paper configuration. All-time ranking is historical comparison.

## Offline verification

```powershell
python -B verify_repairs.py
python -B verify_repairs.py --pattern test*.py
node --check static/js/app.js
```

The runner uses disposable storage, clears inherited database configuration,
disables external HTTP and hashes user ledgers/reports before and after tests.
API tests inject temporary bot instances. Use this runner rather than running
old tests against a live account. The offline suite exercises SQLite and SQL
behavior; it does not connect to a production PostgreSQL server.
