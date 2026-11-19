# SQL Analysis

A small relational SQLite database built from the cleaned dataset, plus 17 analytical queries organized by theme.

## Files

| File | Contents |
|---|---|
| `schema.sql` | Table definitions and the reasoning behind the three-table split |
| `build_database.py` | Reproducible script: cleaned CSV -> `hospital_patient_flow.db` |
| `hospital_patient_flow.db` | The built SQLite database (generated — delete and rebuild any time) |
| `queries/01_volume_and_trends.sql` | Patient volume, daily/monthly trends, peak hours, rolling averages |
| `queries/02_waiting_time_analysis.sql` | Average/median wait, long-wait patients, by priority/age/department |
| `queries/03_performance_ranking.sql` | Consultation duration, length of stay, department ranking, doctor workload |

Department handling note: Python baseline tables retain `Unknown` as a separate data-quality category so the affected encounters remain visible for audit. SQL department-level rankings exclude `Unknown`, because it is not a valid clinical department. Do not compare those department totals without accounting for this difference.

## A real bug this project caught — and why the fix matters

While building the `doctors` dimension table, joining it naively to `Department` from the flat encounter table produced doctors who appeared to work across multiple departments (e.g. `DOC-EMG-1` showing up under Emergency, Paediatrics, *and* "Unknown"). That wasn't a coding mistake in the join — it was the **injected "incorrect department value" data-quality problem** (see the notebook, Section 2) leaking into a dimension table: ~0.3% of encounter rows have a corrupted `Department` value, but their `Doctor_ID` is untouched, so building the doctors table from the raw `Department` column inherited that corruption.

The fix (`build_database.py`): derive each doctor's department from the code embedded in their own ID (`"DOC-EMG-1"` → Emergency) instead of from the encounter-level `Department` column. This is worth documenting rather than quietly patching, because it's a realistic example of how a data-quality problem in one field can silently corrupt a downstream reference table if you're not deliberate about which column a dimension table is really keyed on.

## Why a relational database instead of querying the flat CSV directly

`build_database.py` splits the single cleaned flat file into three related tables:

- **`encounters`** — one row per patient visit (the fact table)
- **`departments`** — one row per clinical department
- **`doctors`** — one row per distinct doctor, correctly keyed to their real department (see above)

This lets the SQL queries demonstrate genuine JOINs, not just filters on one file, and mirrors how a real hospital records system separates encounter data from reference/dimension data.

## How to reproduce

```bash
cd sql
python build_database.py
sqlite3 hospital_patient_flow.db < queries/01_volume_and_trends.sql
# or open hospital_patient_flow.db in DB Browser for SQLite / any SQLite client
```

## Query techniques demonstrated

- `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `LIMIT` — all files
- `CASE` — `02_waiting_time_analysis.sql` (readable wait-speed labels)
- `JOIN` (encounters ↔ departments ↔ doctors) — `03_performance_ranking.sql`
- CTEs (`WITH`) — median calculation, rolling averages, monthly trends, department ranking
- Window functions: `PERCENT_RANK()`, `RANK()`, `AVG() OVER()` with a rolling frame — used for median estimation, department ranking, and 7-day rolling volume
- Date/time functions (`STRFTIME`) — daily/monthly aggregation

## Business questions each file answers

- **01 — Volume & trends:** How many patients, when, and is there a real trend or just daily noise?
- **02 — Waiting time:** How long do patients wait by department, recorded priority and age group? Priority differences are descriptive: the simulation uses first-come, first-served consultation queues, so this query does not test triage effectiveness.
- **03 — Performance ranking:** Which department most needs operational attention, and is that attention question answerable with a single number rather than four separate charts?
