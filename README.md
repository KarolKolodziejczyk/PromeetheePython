# PROMETHEE in Python – Task 2 (MCDM)

Own implementation of **PROMETHEE I / II** (numpy only, Visual PROMETHEE not used),
applied to the Task 1 problem **"Which 3D printer should I buy?"** (4 FDM printers,
6 criteria, data from `KK_MCDM_1.xlsx`), with comparison against the Task 1 WSM,
extended sensitivity analysis (stability intervals, Monte Carlo, thresholds), **F-PROMETHEE**
(uncertain values as triangular fuzzy numbers) and the **efficiency measuring** extension.

**Read the analysis and interpretation in [`REPORT.md`](REPORT.md).** Code walkthrough (PL): [`WYJASNIENIE_KODU.md`](WYJASNIENIE_KODU.md).

## Run in Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/KarolKolodziejczyk/PromeetheePython/blob/claude/wizardly-edison-vn4pzz/KK_Task2_Efficency.ipynb)

Open [`KK_Task2_Efficency.ipynb`](KK_Task2_Efficency.ipynb) in Colab – it is saved with all outputs, so every figure and table is visible immediately. Choose **Runtime → Run all** to recompute.
The notebook is self-contained (it writes the code and data files itself), so it also works
if the repository is private: download the `.ipynb` and upload it in Colab via
*File → Upload notebook*. Edit the `data/problem.json` cell to change the data or weights.
After changing the code, regenerate the notebook with `python tools/build_notebook.py`.

## Layout

| Path | Content |
|---|---|
| `data/problem.json` | the whole problem: printers, criteria (direction, preference function, q/p/s), performance table, weights, weight scenarios, what-if setup, efficiency settings |
| `promethee/core.py` | 6 preference functions, PROMETHEE I & II, WSM (P×W, Task 1 ratio normalisation), Kendall τ / Spearman ρ |
| `promethee/sensitivity.py` | exact weight-stability intervals, one-at-a-time sweeps, Monte-Carlo rank acceptability, threshold sensitivity |
| `promethee/fuzzy.py` | F-PROMETHEE: triangular fuzzy values and weights, α-cuts, fuzzy net flows, guaranteed winner |
| `promethee/efficiency.py` | cost vs. benefit flows, efficient (non-dominated) printers, best printer for a given budget |
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
