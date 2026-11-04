# PROMETHEE in Python – Task 2 (MCDM)

Own implementation of **PROMETHEE I / II** (numpy only, Visual PROMETHEE not used),
with ranking comparison, extended sensitivity analysis and a
**group decision-making** extension (PROMETHEE GDSS).

**Read the analysis and interpretation in [`REPORT.md`](REPORT.md).**

## Layout

| Path | Content |
|---|---|
| `data/problem.json` | the whole problem: alternatives, criteria (direction, preference function, q/p/s), performance table, weights, weight scenarios, decision makers |
| `promethee/core.py` | 6 preference functions, PROMETHEE I & II, weighted sum (P×W), Kendall τ / Spearman ρ |
| `promethee/sensitivity.py` | exact weight-stability intervals, one-at-a-time sweeps, Monte-Carlo rank acceptability, threshold sensitivity |
| `promethee/group.py` | multi-DM aggregation, consensus, robustness to DM importance |
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
