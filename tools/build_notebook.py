"""Build KK_Task2_Efficency.ipynb – a self-contained notebook for Google Colab.

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
NB = "KK_Task2_Efficency.ipynb"

EMBED = ["promethee/__init__.py", "promethee/core.py", "promethee/sensitivity.py",
         "promethee/efficiency.py", "promethee/fuzzy.py", "run_analysis.py", "data/problem.json"]


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text: str, hidden: bool = False) -> dict:
    meta = {"cellView": "form"} if hidden else {}
    return {"cell_type": "code", "metadata": meta, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


def interp(text: str) -> dict:
    """Short interpretation of the result right above it."""
    return md("**Interpretation.** " + text.strip("\n"))


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
    md("## 0. Code (PROMETHEE package) – run, no need to read"),
    code("import os\nos.makedirs('promethee', exist_ok=True)\nos.makedirs('data', exist_ok=True)"),
]
for rel in EMBED:
    src = (ROOT / rel).read_text(encoding="utf-8")
    if rel == "data/problem.json":
        cells.append(md("""
## 1. Problem data

All inputs are in this one file (the code contains no numbers from Task 1):

| part of the file | what it is |
|---|---|
| `alternatives` | the 4 printers A1–A4 |
| `criteria` | the 6 criteria: `direction` (min = lower is better, max = higher is better), `function` (preference function) and its thresholds `q`, `p` |
| `performance` | the decision matrix from Task 1 (one row per printer, columns = criteria C1–C6) |
| `weights` | my weights from Task 1, method 1 (points) |
| `weight_scenarios` | other weight sets for the comparison with the WSM (incl. method 2 and the Task 1 "what if" cases) |
| `fuzzy` | which values are uncertain (triangular fuzzy numbers) and the fuzzy weights (±10 %) |
| `efficiency` | which criterion is the input (price); all others are outputs |
"""))
    cells.append(code(f"%%writefile {rel}\n{src}"))

cells += [
    md("## 2. Run the analysis"),
    code("!python run_analysis.py > /dev/null && echo 'done – results in results/'"),
    code("import pandas as pd\nfrom IPython.display import Markdown, Image, display\n"
         "pd.set_option('display.width', 200)"),

    md("## 3. PROMETHEE I and II"),
    show("Performance table (from Task 1)", csv="performance_table.csv"),
    show("Inputs overview – what each input is and what it means", csv="inputs_overview.csv"),
    interp("""
One row per criterion. The decision matrix and the weights are the same as in Task 1. New for
PROMETHEE is the **preference function**: it says how big a difference has to be before it
matters to me. **q** = the difference I ignore, **p** = the difference from which one printer is
clearly better (column "what the thresholds mean"). For noise q = 2 dB because my noise values come
from different sources, and p = 7 dB, which you clearly hear. Price is very important to me, so
already 300 € is decisive. Ease of use is my own 1–5 score, so I used the level function.
The last two columns are the inputs for the F-PROMETHEE (which values are uncertain) and for the
efficiency analysis (price = input, everything else = output).
"""),
    show("PROMETHEE II – flows and complete ranking", "01_net_flows.png", "promethee_flows.csv"),
    interp("""
φ⁺ shows how much a printer is better than the others and φ⁻ how much the others are better than
it. The net flow φ = φ⁺ − φ⁻ gives the ranking: **Snapmaker U1 > Creality K2 Plus > Bambu H2D >
Prusa CORE One**. U1 is the only printer with a positive net flow (+0.295) and it is far ahead.
K2 Plus and H2D are almost tied (−0.044 vs −0.059), so I would not read too much into which of
them is 2nd.
"""),
    show("PROMETHEE I – partial ranking", "02_promethee_I.png", "promethee_I_relations.csv",
         "P = row outranks column, `-` = column outranks row, R = incomparable"),
    interp("""
In PROMETHEE I a printer is better only if it has a higher φ⁺ **and** a lower φ⁻ at the same time.
U1 is better than all three others in this sense, so PROMETHEE I agrees with PROMETHEE II about the
winner. H2D is incomparable (R) with K2 Plus and with the Prusa: it is very good in speed, ease of
use and noise, but much more expensive, so φ⁺ and φ⁻ say different things (the lines cross).
"""),
    show("Strengths and weaknesses (unicriterion net flows)", "03_unicriterion_profiles.png",
         "unicriterion_net_flows.csv"),
    interp("""
This shows why U1 wins: it is the best on price and on nozzles, which are my two most important
criteria (together 55 % of the weight). It is the loudest and slowest printer and has a small
build volume, but these criteria have lower weights. H2D is best on speed and ease of use but has
the worst price.
"""),

    md("## 4. Comparison with the WSM from Task 1"),
    show("Ranks of PROMETHEE II and WSM for different weights", "04_ranking_comparison.png",
         "ranking_comparison_ranks.csv"),
    interp("""
With my real weights (method 1 and method 2) both PROMETHEE and the WSM choose **U1**, so the
result of Task 1 is confirmed. The methods differ in the details: with method 1 the WSM has H2D in
2nd place, PROMETHEE has K2 Plus. When price matters less ("Price matters less", "0.2 / 0.15") the
WSM still chooses U1, but PROMETHEE chooses H2D. As I understand it, this is because the WSM counts
every difference proportionally, while PROMETHEE compares pairs and ignores small differences
(below q) and caps big ones (above p). For example U1's advantage of having 4 nozzles counts a lot
in the WSM normalisation, but in PROMETHEE it is limited by the preference function.
"""),

    md("## 5. Sensitivity analysis"),
    show("Weight stability intervals", "05_weight_sweeps.png", "weight_stability_intervals.csv"),
    interp("""
Here I change the weight of one criterion and keep the others in proportion. U1 stays the winner
for every price weight above 0.148 (mine is 0.30) and for any nozzle weight. The other criteria
would need about 2.4 times or more of their weight to change the winner. So the winner is stable;
only the order of places 2 and 3 changes easily.
"""),
    show("Random weights (Monte Carlo)", "06_rank_acceptability.png"),
    interp("""
With weights randomly changed by ±20 % around mine, U1 is first in 100 % of cases, and with ±50 %
in 97 %. With completely random weights H2D wins most often (62 %). So H2D is probably the
"objectively" strongest printer, and U1 wins because of my priorities (low price, multi-colour).
"""),
    show("Changing the thresholds q and p", csv="threshold_sensitivity.csv"),
    interp("""
The thresholds are my own choice, so I multiplied all of them by 0.25 to 2. U1 is first in every
case, only places 2–4 change. So my choice of q and p does not decide the winner.
"""),

    md("## 6. Extension (4c) – Efficiency measuring"),
    show("Efficient frontier – input: price, output: benefit", "09_efficiency_frontier.png",
         "efficiency.csv"),
    interp("""
My goal in Task 1 was "the printer that gives me the most for my money", so I chose efficiency
measuring. The input is the price and the outputs are the other five criteria (their PROMETHEE
flow = "benefit"). A printer is efficient if no other printer is cheaper and better at the same
time. Only **U1** (cheapest) and **H2D** (best benefit) are efficient. **K2 Plus and Prusa are
dominated by U1**: U1 is cheaper and gives more. So the real choice is only between U1 and paying
1226 € more for H2D. Because price is an important criterion for me, I stay with U1.
"""),

    md("## 7. Uncertainty (5a) – F-PROMETHEE"),
    show("Fuzzy decision matrix (triangular fuzzy numbers l; m; u)", csv="fuzzy_decision_matrix.csv"),
    interp("""
I replaced the values I am not sure about with triangular fuzzy numbers (lowest; used value;
highest): price ±5 % (different shops) and U1 (899; 899; 1099) because 899 € is a sale price;
noise ±2 dB (different sources) and K2 Plus (45; 50; 52) because the manufacturer says 45 dB;
ease of use ±0.5 because it is my own opinion. The weights are fuzzy too, ±10 %.
Speed, volume and nozzles stay exact (manufacturer data).
"""),
    show("Fuzzy net flows and F-PROMETHEE ranking", "11_f_promethee.png", "fuzzy_promethee.csv"),
    interp("""
Every PROMETHEE step is done on the three numbers (l; m; u), so each printer gets a triangular
net flow; the middle value m is the normal φ. Ranked by the centroid (l + m + u)/3 the order is the
same as before: **U1 > K2 Plus > H2D > Prusa**. U1 is the only printer whose whole triangle is on
the positive side, so even in the worst plausible case it is not worse than average. The K2 Plus
triangle is the widest because its noise value is the most uncertain.
"""),

    md("## 8. Conclusion"),
    md("""
**I would buy the Snapmaker U1.** It wins in PROMETHEE II and PROMETHEE I, the same as the WSM in
Task 1, it stays first when I change the weights or the thresholds, it is efficient and dominates
the K2 Plus and the Prusa, and it still wins when the uncertain values are fuzzy. The Bambu H2D is
the better machine overall, but for my priorities (price and multi-colour) it is not worth 1226 €
more.
"""),
]

# every table and figure produced by run_analysis.py must be shown somewhere
shown = "".join("".join(c["source"]) for c in cells)
produced = [p.name for p in (ROOT / "results").glob("*.csv")] + \
           [p.name for p in (ROOT / "results" / "figures").glob("*.png")]
# deliberately not shown (kept in results/ and REPORT.md, not needed in the notebook)
HIDDEN = {"criteria_parameters.csv", "preference_index_matrix.csv", "ranking_comparison_scores.csv",
          "rank_acceptability_local20.csv", "rank_acceptability_local50.csv",
          "rank_acceptability_simplex.csv", "07_threshold_sweeps.png", "what_if.csv",
          "08_what_if.png", "budget_choice.csv", "10_budget_choice.png",
          "efficiency_acceptability.csv"}
missing = [f for f in produced if f not in shown and f not in HIDDEN]
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
