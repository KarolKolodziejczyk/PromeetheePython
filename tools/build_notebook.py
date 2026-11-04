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
         "promethee/efficiency.py", "promethee/fuzzy.py", "run_analysis.py", "data/problem.json"]


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text: str, hidden: bool = False) -> dict:
    meta = {"cellView": "form"} if hidden else {}
    return {"cell_type": "code", "metadata": meta, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


def note(text: str) -> dict:
    """Short personal study note (Polish) shown as a quote block."""
    body = "\n".join("> " + ln if ln.strip() else ">" for ln in text.strip("\n").splitlines())
    return md("> **Notatka:**\n>\n" + body)


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
* the **efficiency analysis / PROMETHEE V** extension.

**How to use:** `Runtime → Run all`. The notebook is self-contained – it writes the code files itself,
so no repository access is needed. To change the data or weights, edit the `data/problem.json` cell
(section 1) and run everything again. The full interpretation is in `REPORT.md` in the repository.
"""),
    md("## 0. Code (PROMETHEE package) – run, no need to read"),
    note("""
Tu tylko **zapisuję pliki z kodem**, nic się jeszcze nie liczy.
- `core.py`: sama metoda PROMETHEE (funkcje preferencji → π(a,b) → φ⁺, φ⁻, φ) i WSM z Task 1
- `sensitivity.py`: analiza wrażliwości (wagi, Monte Carlo, progi)
- `efficiency.py`: rozszerzenie Efficiency / PROMETHEE V (co dostaję za swoje pieniądze)
- `fuzzy.py`: stabilność przez zbiory rozmyte
- `run_analysis.py`: odpala wszystko po kolei i zapisuje tabele/wykresy do `results/`
"""),
    code("import os\nos.makedirs('promethee', exist_ok=True)\nos.makedirs('data', exist_ok=True)"),
]
NOTES_BEFORE = {
    "promethee/core.py": """
Najważniejszy plik, tu jest PROMETHEE:
- `_usual`, `_v_shape`, `_level`, `_linear`…: **funkcje preferencji**, zamieniają różnicę d = g(a) − g(b) na liczbę 0–1 (progi q, p)
- `Criterion.preference`: dla kryteriów *min* (cena, hałas) odwraca znak różnicy
- `preference_matrices`: dla każdego kryterium porównuje **każdą parę drukarek** → P_j(a,b)
- `promethee`: **π(a,b) = Σ w_j·P_j(a,b)**, potem **φ⁺ = średnia wiersza**, **φ⁻ = średnia kolumny**, **φ = φ⁺ − φ⁻**
- `promethee_I`: ranking częściowy (P / I / R) z φ⁺ i φ⁻ osobno
- `weighted_sum`: WSM z Task 1 (min/x, x/max) do porównania
""",
    "promethee/sensitivity.py": """
Wrażliwość. Trik: **φ = Σ w_j·φ_j** (φ jest liniowe w wagach), więc:
- `stability_intervals`: dokładnie liczy, przy jakiej wadze drukarki zamieniają się miejscami
- `monte_carlo`: losuje 20 000 zestawów wag i patrzy, jak często która drukarka jest 1., 2., …
- `threshold_sensitivity`: zmienia progi q, p i sprawdza, czy ranking się trzyma
""",
    "promethee/efficiency.py": """
Rozszerzenie **Efficiency / PROMETHEE V**:
- `split_flows`: dzieli przepływ na **φ korzyści** (5 kryteriów bez ceny) i **φ kosztu** (cena)
- `efficient_set`: drukarka jest **efektywna**, jeśli żadna inna nie jest jednocześnie lepsza i tańsza
- `promethee_v`: PROMETHEE V = wybierz drukarki o max sumie φ przy ograniczeniach (budżet, liczba sztuk), tu: kup 1 drukarkę
- `budget_sweep`: najlepsza drukarka dla każdego budżetu
""",
    "promethee/fuzzy.py": """
Stabilność przez **zbiory rozmyte (fuzzy sets)**: każda waga to liczba trójkątna (w·(1−s), w, w·(1+s)).
Dla każdego poziomu α liczę **najmniejsze i największe φ** po wszystkich wagach z α-przekroju (suma = 1).
`extreme_linear`: dokładne min/max (φ jest liniowe w wagach → wystarczy „dosypywać” wagę zachłannie).
`robust_spread`: jak duży rozrzut wag U1 wytrzymuje i nadal na pewno wygrywa.
""",
    "run_analysis.py": """
Skrypt „dyrygent”: wczytuje JSON, woła funkcje z `promethee/` sekcja po sekcji
(ranking → porównanie z WSM → wrażliwość → fuzzy → what-if H2D → efficiency) i zapisuje wyniki.
""",
}
for rel in EMBED:
    src = (ROOT / rel).read_text(encoding="utf-8")
    if rel == "data/problem.json":
        cells.append(md("""
## 1. Problem data – **edit here**

Printers, criteria (direction, preference function, thresholds q / p / s), weights,
weight scenarios, the what-if setup and the efficiency settings.
Preference functions: `usual`, `u-shape` (q), `v-shape` (p), `level` (q, p), `linear` (q, p), `gaussian` (s).
"""))
        cells.append(note("""
Dane z Task 1 + **moje wybory dla PROMETHEE** (funkcja preferencji i progi):

| kryterium | funkcja | q | p | dlaczego |
|---|---|---|---|---|
| cena (min) | linear | 50 € | 300 € | cena jest dla mnie bardzo ważna: do 50 € bez różnicy, już 300 € taniej (~12% budżetu) = zdecydowanie lepsza |
| hałas (min) | linear | 2 dB | 7 dB | w Task 1: różnice 1–3 dB nic nie znaczą (różne źródła) |
| prędkość (max) | linear | 50 | 400 | małe różnice niezauważalne |
| objętość (max) | linear | 2 | 20 | 20 dm³ to inna klasa drukarki |
| łatwość (max) | level | 0.5 | 1.5 | skala 1–5: 1 pkt różnicy → 0.5, 2+ pkt → 1 |
| dysze (max) | v-shape | – | 3 | każda dysza więcej się liczy (1/3 za dyszę) |

**q** = poniżej tej różnicy „tak samo dobre”, **p** = od tej różnicy „zdecydowanie lepsza”.
Wagi bazowe = metoda 1 z Task 1 (punkty): 0.30 / 0.15 / 0.10 / 0.12 / 0.08 / 0.25.
"""))
    elif rel in NOTES_BEFORE:
        cells.append(note(NOTES_BEFORE[rel]))
    cells.append(code(f"%%writefile {rel}\n{src}"))

cells += [
    md("## 2. Run the analysis"),
    note("Jedna komenda liczy wszystko (ranking, porównanie, wrażliwość, fuzzy, efficiency). Wyniki → folder `results/`."),
    code("!python run_analysis.py > /dev/null && echo 'done – results in results/'"),
    code("import pandas as pd\nfrom IPython.display import Markdown, Image, display\n"
         "pd.set_option('display.width', 200)"),
    md("## 3. PROMETHEE II and PROMETHEE I"),
    show("Performance table", csv="performance_table.csv"),
    note("Dane wejściowe z Task 1, tutaj nic nie jest jeszcze policzone."),
    show("Criteria parameters and base weights", csv="criteria_parameters.csv"),
    show("PROMETHEE II – flows and ranking", "01_net_flows.png", "promethee_flows.csv"),
    note("""
**Kluczowy wynik.** φ⁺ = jak bardzo drukarka przewyższa inne, φ⁻ = jak bardzo inne przewyższają ją,
**φ = φ⁺ − φ⁻** → ranking PROMETHEE II: **U1 > K2 Plus > H2D > Prusa**.
U1 ma dużą przewagę (φ = +0.295, jedyna dodatnia), K2 i H2D prawie remis (różnica 0.014).
"""),
    show("Aggregated preference indices π(a, b)", csv="preference_index_matrix.csv",
         note="π(a, b) = weighted degree to which row printer is preferred to column printer"),
    note("""
Stąd biorą się przepływy. Np. **π(U1, H2D) = 0.467**: cena 0.30·1 (U1 tańsza o 1226 € > p = 300 €) + dysze 0.25·(2/3).
φ⁺(U1) = średnia z **wiersza** U1 = (0.576 + 0.467 + 0.569)/3 = 0.537;
φ⁻(U1) = średnia z **kolumny** U1 = (0.224 + 0.338 + 0.164)/3 = 0.242.
"""),
    show("PROMETHEE I – partial ranking", "02_promethee_I.png", "promethee_I_relations.csv",
         "P = row outranks column, `-` = column outranks row, R = incomparable"),
    note("""
PROMETHEE I patrzy na φ⁺ i φ⁻ **osobno**. Lepsza tylko gdy wyższe φ⁺ **i** niższe φ⁻.
Gdy jedno mówi „lepsza”, a drugie „gorsza” → **R (nieporównywalne)**, na wykresie linie się krzyżują.
**U1 jest lepsza od wszystkich trzech** (najwyższe φ⁺ i najniższe φ⁻), więc PROMETHEE I potwierdza wynik.
H2D jest nieporównywalna z K2 i Prusą: świetna w wielu rzeczach, ale bardzo droga.
"""),
    show("Unicriterion net flows (strengths / weaknesses)", "03_unicriterion_profiles.png",
         "unicriterion_net_flows.csv"),
    note("""
φ_j = przepływ liczony tylko na jednym kryterium → **mocne (niebieskie) i słabe (czerwone) strony**.
φ = Σ w_j·φ_j. U1 wygrywa, bo jest mocna na cenie i dyszach, czyli moich dwóch najważniejszych kryteriach (55% wagi).
"""),
    md("## 4. Comparison of rankings (weight scenarios, PROMETHEE vs WSM P × W)"),
    show("Ranks under every method and weight scenario", "04_ranking_comparison.png",
         "ranking_comparison_ranks.csv"),
    note("""
Górna część = PROMETHEE, dolna = WSM z Task 1, dla 7 zestawów wag.
- M1 i M2 → U1 w obu metodach (wynik Task 1 potwierdzony)
- równe wagi / cena mniej ważna → H2D (PROMETHEE), WSM często dalej U1
- duże wydruki → K2 Plus; bez multi-colour → U1, ale prawie remis z K2
- Prusa zawsze ostatnia
"""),
    show("Scores", csv="ranking_comparison_scores.csv",
         note="Net flow φ for PROMETHEE, Task 1 WSM score for P × W"),
    note("""
**Różnica WSM vs PROMETHEE:** WSM sumuje znormalizowane wartości (każda różnica liczy się proporcjonalnie).
PROMETHEE porównuje **pary** i używa progów: małe różnice (< q) pomija, duże (> p) „ucina” na 1.
Dlatego przy „price matters less” WSM dalej wybiera U1, a PROMETHEE już H2D.
"""),
    md("## 5. Sensitivity analysis"),
    show("5.1 Weight stability intervals", "05_weight_sweeps.png", "weight_stability_intervals.csv"),
    note("""
Zmieniam wagę **jednego** kryterium (reszta proporcjonalnie). Niebieski pas = ranking się nie zmienia.
U1 zostaje 1. dla wagi ceny ≥ 0.148 i **dowolnej** wagi dysz; inne kryteria musiałyby mieć co najmniej 2.4× większą wagę.
"""),
    show("5.2 Monte-Carlo rank acceptability (±20 % / ±50 % / any weights)", "06_rank_acceptability.png"),
    note("""
Losowe wagi: ±20% wokół moich → U1 1. w 100%; ±50% → 97%; zupełnie losowe → H2D 62%.
Czyli: **H2D to obiektywnie najmocniejsza drukarka, U1 wygrywa przez moje priorytety** (cena + dysze).
"""),
    code('for f in ["local20", "local50", "simplex"]:\n'
         '    display(Markdown(f"**{f}**"))\n'
         '    display(pd.read_csv(f"results/rank_acceptability_{f}.csv", index_col=0).round(3))'),
    show("5.3 Thresholds and preference functions", "07_threshold_sweeps.png", "threshold_sensitivity.csv"),
    note("Progi q, p to moja subiektywna decyzja, więc sprawdzam: mnożę wszystkie ×0.25 … ×2 → **U1 zawsze 1.** Zmieniają się tylko miejsca 2–3."),
    show("5.4 Fuzzy-set stability (triangular fuzzy weights)", "11_fuzzy_stability.png",
         "fuzzy_stability.csv"),
    note("""
**Fuzzy zamiast losowania:** waga ceny to nie „dokładnie 0.30”, tylko „około 0.30” = trójkąt (0.24; 0.30; 0.36) przy ±20%.
- **α = 1** (czubek trójkąta) = moje dokładne wagi → zwykłe φ
- **α = 0** (podstawa) = najszerszy zakres wag → φ jako przedział
- szerokość „trójkąta” φ na wysokości α = ile może się zmienić φ, gdy wagi są niepewne

Wynik: przy ±20% **U1 wygrywa dla każdej wagi** w całym zakresie. Przy ±50% pewna wygrana dopiero od α ≈ 0.41.
Największy rozrzut, przy którym U1 wygrywa na pewno: **±29.7%** każdej wagi.
"""),
    show("5.5 What if the Bambu H2D goes on sale?", "08_what_if.png", "what_if.csv"),
    note("""
Kontynuacja sekcji 6 z Task 1: H2D wygrywa, jeśli kosztuje **< ok. 1096 €** (~48% taniej).
WSM w Task 1 mówił, że H2D nie wygrywa nawet przy cenie U1, więc tu PROMETHEE daje inny wniosek.
Powyżej ~1580 € linia H2D jest płaska: różnica ceny > p = 300 €, więc preferencja i tak = 1.
"""),
    md("## 6. Extension – Efficiency analysis and PROMETHEE V"),
    note("""
**Dlaczego Efficiency:** cel z Task 1 to *„find the printer that gives me the most for my money”*.
Dzielę kryteria na **koszt** (cena) i **korzyści** (hałas, prędkość, objętość, łatwość, dysze).
Dla każdej drukarki liczę **φ korzyści** i **φ kosztu** (z tych samych przepływów co w rankingu).
**Efektywna** = żadna inna nie jest jednocześnie lepsza i tańsza.
"""),
    show("Cost vs. benefit and the efficient set", "09_efficiency_frontier.png", "efficiency.csv"),
    note("""
Efektywne są tylko **U1** (najtańsza, 899 €) i **H2D** (najlepsza, φ korzyści +0.345).
**K2 Plus i Prusa są zdominowane:** U1 jest od nich tańsza i jednocześnie lepsza na pozostałych kryteriach.
Przejście U1 → H2D: **+1226 €** za **+0.345** φ korzyści (ok. 355 € za każde +0.1).
"""),
    show("PROMETHEE V – best printer for each budget", "10_promethee_v_budget.png",
         "promethee_v_budget.csv"),
    note("""
**PROMETHEE V:** wybierz drukarkę o największym φ korzyści, której cena ≤ budżet (kupuję dokładnie 1).
Budżet 899–2124 € → **U1**; od 2125 € → **H2D**.
Przy budżecie 2500 € i **samych korzyściach** wygrałaby H2D. Ale cena jest dla mnie kryterium (waga 0.30), nie tylko limitem,
więc z pełnym φ (cena + korzyści) PROMETHEE V wybiera **U1**, tak jak ranking.
"""),
    show("Robustness – how often is a printer efficient under random weights", csv="efficiency_acceptability.csv"),
    note("U1 i H2D są efektywne prawie zawsze (U1 zawsze, bo jest najtańsza). Prusa prawie nigdy, więc to najsłabszy wybór."),
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
