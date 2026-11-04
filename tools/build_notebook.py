"""Build PROMETHEE_Colab.ipynb – a self-contained notebook for Google Colab.

The notebook embeds the current source files (via %%writefile), so it runs
without cloning the repository. Re-run after changing the code:

    python tools/build_notebook.py               # builds and executes (outputs saved)
    python tools/build_notebook.py --no-execute  # structure only

Executing needs: pip install nbclient ipykernel
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = "KarolKolodziejczyk/PromeetheePython"
BRANCH = "claude/wizardly-edison-vn4pzz"
NB = "PROMETHEE_Colab.ipynb"

EMBED = ["promethee/__init__.py", "promethee/core.py", "promethee/sensitivity.py",
         "promethee/sort.py", "run_analysis.py", "data/problem.json"]


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text: str, hidden: bool = False) -> dict:
    meta = {"cellView": "form"} if hidden else {}
    return {"cell_type": "code", "metadata": meta, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


def show(title: str, fig: str | None = None, csv: str | None = None, note: str = "") -> dict:
    lines = [f'display(Markdown("### {title}"))']
    if note:
        lines.append(f"display(Markdown({note!r}))")
    if csv:
        lines.append(f'display(pd.read_csv("results/{csv}", index_col=0).round(3))')
    if fig:
        lines.append(f'display(Image("results/figures/{fig}", width=900))')
    return code("\n".join(lines))


cells = [
    md(f"""
# Task 2 – PROMETHEE: which 3D printer should I buy?

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/{REPO}/blob/{BRANCH}/{NB})

Own Python implementation of **PROMETHEE I / II** (no Visual PROMETHEE) for the Task 1 problem
(4 FDM printers, 6 criteria, data from `KK_MCDM_1.xlsx`), with:

* comparison with the Task 1 WSM (P × W) under 7 weight configurations,
* extended sensitivity analysis (exact weight stability intervals, Monte-Carlo, thresholds, H2D price what-if),
* the **FlowSort** (PROMETHEE SORT) extension.

**How to use:** `Runtime → Run all`. The notebook is self-contained – it writes the code files itself,
so no repository access is needed. To change the data or weights, edit the `data/problem.json` cell
(section 1) and run everything again. The full interpretation is in `REPORT.md` in the repository.
"""),
    md("## 0. Code (PROMETHEE package) – run, no need to read"),
    code("import os\nos.makedirs('promethee', exist_ok=True)\nos.makedirs('data', exist_ok=True)"),
]
for rel in EMBED:
    src = (ROOT / rel).read_text(encoding="utf-8")
    if rel == "data/problem.json":
        cells.append(md("""
## 1. Problem data – **edit here**

Printers, criteria (direction, preference function, thresholds q / p / s), weights,
weight scenarios, the what-if setup and the FlowSort profiles.
Preference functions: `usual`, `u-shape` (q), `v-shape` (p), `level` (q, p), `linear` (q, p), `gaussian` (s).
"""))
    cells.append(code(f"%%writefile {rel}\n{src}"))

cells += [
    md("## 2. Run the analysis"),
    code("!python run_analysis.py > /dev/null && echo 'done – results in results/'"),
    code("import pandas as pd\nfrom IPython.display import Markdown, Image, display\n"
         "pd.set_option('display.width', 200)"),
    md("## 3. PROMETHEE II and PROMETHEE I"),
    show("Performance table", csv="performance_table.csv"),
    show("Criteria parameters and base weights", csv="criteria_parameters.csv"),
    show("PROMETHEE II – flows and ranking", "01_net_flows.png", "promethee_flows.csv"),
    show("Aggregated preference indices π(a, b)", csv="preference_index_matrix.csv",
         note="π(a, b) = weighted degree to which row printer is preferred to column printer"),
    show("PROMETHEE I – partial ranking", "02_promethee_I.png", "promethee_I_relations.csv",
         "P = row outranks column, `-` = column outranks row, R = incomparable"),
    show("Unicriterion net flows (strengths / weaknesses)", "03_unicriterion_profiles.png",
         "unicriterion_net_flows.csv"),
    md("## 4. Comparison of rankings (weight scenarios, PROMETHEE vs WSM P × W)"),
    show("Ranks under every method and weight scenario", "04_ranking_comparison.png",
         "ranking_comparison_ranks.csv"),
    show("Scores", csv="ranking_comparison_scores.csv",
         note="Net flow φ for PROMETHEE, Task 1 WSM score for P × W"),
    md("## 5. Sensitivity analysis"),
    show("5.1 Weight stability intervals", "05_weight_sweeps.png", "weight_stability_intervals.csv"),
    show("5.2 Monte-Carlo rank acceptability (±20 % / ±50 % / any weights)", "06_rank_acceptability.png"),
    code('for f in ["local20", "local50", "simplex"]:\n'
         '    display(Markdown(f"**{f}**"))\n'
         '    display(pd.read_csv(f"results/rank_acceptability_{f}.csv", index_col=0).round(3))'),
    show("5.3 Thresholds and preference functions", "07_threshold_sweeps.png", "threshold_sensitivity.csv"),
    show("5.4 What if the Bambu H2D goes on sale?", "08_what_if.png", "what_if.csv"),
    md("## 6. Extension – FlowSort (PROMETHEE SORT)"),
    show("Assignment with base weights", "09_flowsort.png", "flowsort_base.csv"),
    show("Assignment under every weight scenario", csv="flowsort_scenarios.csv"),
    show("Class acceptability under random weights", "10_flowsort_acceptability.png",
         "flowsort_acceptability.csv"),
    md("## 7. Full auto-generated results (markdown) and download"),
    code("display(Markdown(open('results/results.md', encoding='utf-8').read()))"),
    code("# optional: download all tables and figures as a zip\n"
         "import shutil\nshutil.make_archive('promethee_results', 'zip', 'results')\n"
         "try:\n    from google.colab import files\n    files.download('promethee_results.zip')\n"
         "except ImportError:\n    print('saved promethee_results.zip')"),
]

# every table and figure produced by run_analysis.py must be shown somewhere
shown = "".join("".join(c["source"]) for c in cells)
produced = [p.name for p in (ROOT / "results").glob("*.csv")] + \
           [p.name for p in (ROOT / "results" / "figures").glob("*.png")]
missing = [f for f in produced if f not in shown and
           not f.startswith("rank_acceptability_")]  # shown by a loop
if missing:
    raise SystemExit(f"not displayed in notebook: {missing}")

nb = {"nbformat": 4, "nbformat_minor": 5,
      "metadata": {"kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}, "colab": {"provenance": []}},
      "cells": cells}
for i, c in enumerate(nb["cells"]):
    c["id"] = f"cell-{i:02d}"
(ROOT / NB).write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
if "--no-execute" not in sys.argv:
    # run it so the saved notebook already contains every figure and table
    import tempfile

    import nbformat
    from nbclient import NotebookClient

    nbo = nbformat.reads(json.dumps(nb), as_version=4)
    with tempfile.TemporaryDirectory() as tmp:
        NotebookClient(nbo, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": tmp}}).execute()
    for c in nbo.cells:
        for o in c.get("outputs", []):
            if o.get("output_type") == "error":
                raise SystemExit(f"notebook error: {o['ename']}: {o['evalue']}")
    nbformat.write(nbo, ROOT / NB)
print(f"wrote {NB} with {len(cells)} cells")
