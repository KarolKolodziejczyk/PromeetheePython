# PROMETHEE in Python – Task 2 (MCDM)

Own implementation of **PROMETHEE I / II** (numpy only, Visual PROMETHEE not used),
applied to the Task 1 problem **"Which 3D printer should I buy?"** (4 FDM printers,
6 criteria, data from `KK_MCDM_1.xlsx`), with comparison against the Task 1 WSM,
extended sensitivity analysis and the **FlowSort** (PROMETHEE SORT) extension.

**Read the analysis and interpretation in [`REPORT.md`](REPORT.md).**

## Layout

| Path | Content |
|---|---|
| `data/problem.json` | the whole problem: printers, criteria (direction, preference function, q/p/s), performance table, weights, weight scenarios, what-if setup, FlowSort profiles |
| `promethee/core.py` | 6 preference functions, PROMETHEE I & II, WSM (P×W, Task 1 ratio normalisation), Kendall τ / Spearman ρ |
| `promethee/sensitivity.py` | exact weight-stability intervals, one-at-a-time sweeps, Monte-Carlo rank acceptability, threshold sensitivity |
| `promethee/sort.py` | FlowSort assignment (φ, φ+, φ−) and class acceptability under random weights |
| `run_analysis.py` | runs everything → `results/*.csv`, `results/figures/*.png`, `results/results.md` |
| `tests/` | hand-computed example and consistency checks |

## Run

```bash
pip install -r requirements.txt
python run_analysis.py                 # uses data/problem.json
python run_analysis.py other.json      # any problem with the same JSON schema
python -m pytest -q
```

Preference functions available in `problem.json`: `usual`, `u-shape` (q),
`v-shape` (p), `level` (q, p), `linear` (q, p), `gaussian` (s).
