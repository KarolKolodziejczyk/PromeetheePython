# Wyjaśnienie kodu – PROMETHEE dla wyboru drukarki 3D

Ten dokument tłumaczy krok po kroku, co robi każdy plik i każda ważna funkcja.
Na końcu jest lista pytań, które może zadać prowadzący, razem z odpowiedziami.

---

## 0. Jak to wszystko działa razem (obraz ogólny)

```
data/problem.json          ← dane z Task 1 + parametry PROMETHEE
        │
        ▼
promethee/core.py          ← funkcje preferencji, PROMETHEE I i II, WSM (P×W)
promethee/sensitivity.py   ← analiza wrażliwości (wagi, Monte Carlo, progi)
promethee/fuzzy.py         ← F-PROMETHEE (niepewne wartości jako liczby rozmyte)
promethee/efficiency.py    ← rozszerzenie: Efficiency measuring
        │
        ▼
run_analysis.py            ← uruchamia wszystko po kolei, zapisuje tabele i wykresy
        │
        ▼
results/*.csv, results/figures/*.png, results/results.md
        │
        ▼
REPORT.md (interpretacja)    PROMETHEE_Colab.ipynb (to samo w Colabie)
```

* **Biblioteki:** `numpy` liczy, `pandas` robi tabele, `matplotlib` rysuje
  wykresy. Nie ma żadnej gotowej biblioteki PROMETHEE: cały algorytm jest
  napisany od zera, zgodnie z wymaganiem zadania („your own Python code”).
* **Dane są oddzielone od kodu.** Kod nie zawiera żadnej liczby z Task 1.
  Wszystko czyta z pliku JSON, więc ten sam program działa dla dowolnego
  problemu.

---

## 1. `data/problem.json` – dane wejściowe

| Pole | Co zawiera |
|---|---|
| `alternatives` | 4 drukarki: A1 Creality K2 Plus, A2 Snapmaker U1, A3 Bambu H2D, A4 Prusa CORE One |
| `criteria` | 6 kryteriów. Dla każdego: `direction` (`min` albo `max`), `function` (typ funkcji preferencji) oraz progi `q`, `p`, `s` |
| `performance` | tabela wartości z Task 1 (cena, hałas, prędkość, objętość, łatwość obsługi, liczba dysz) |
| `weights` | wagi bazowe: metoda 1 z Task 1 (punkty / 100) = 0.30, 0.15, 0.10, 0.12, 0.08, 0.25 |
| `weight_scenarios` | 7 zestawów wag do porównania: M1, M2 (rank sum), równe, 0.2/0.15 i 3 scenariusze z Task 1 |
| `weighted_sum_normalisation` | `"ratio"`: normalizacja taka jak w arkuszu z Task 1 (min/x oraz x/max) |
| `what_if` | analiza „co jeśli H2D będzie tańszy” (kontynuacja sekcji 6 z Task 1) |
| `fuzzy` | które wartości są niepewne i jakie mają trójkątne liczby rozmyte (wymaganie 5) |
| `efficiency` | które kryterium jest wejściem/kosztem (cena) i zakres budżetów |

---

## 2. `promethee/core.py` – serce metody

### 2.1 Funkcje preferencji (linie 30–62)

PROMETHEE nie porównuje samych wartości, tylko **różnice** między dwiema
alternatywami na danym kryterium: d = g(a) − g(b). Funkcja preferencji
zamienia tę różnicę na stopień preferencji P(a, b) z przedziału [0, 1]:

* 0 oznacza „a nie jest lepsze od b”,
* 1 oznacza „a jest zdecydowanie lepsze od b”.

| Funkcja w kodzie | Typ (Brans) | Wzór |
|---|---|---|
| `_usual` | I – zwykłe | P = 1, gdy d > 0 |
| `_u_shape` | II – U-shape | P = 1, gdy d > q |
| `_v_shape` | III – V-shape | P = d / p, obcięte do [0, 1] |
| `_level` | IV – poziomowe | P = 0 dla d ≤ q, 0.5 dla q < d ≤ p, 1 dla d > p |
| `_linear` | V – liniowe z obojętnością | P = 0 dla d ≤ q, (d − q)/(p − q) dla q < d ≤ p, 1 dla d > p |
| `_gaussian` | VI – gaussowskie | P = 1 − exp(−d² / 2s²) |

* **q (próg obojętności):** różnica, poniżej której alternatywy są „tak samo
  dobre”.
* **p (próg ścisłej preferencji):** różnica, od której preferencja jest pełna.

Funkcje działają na całych macierzach naraz (`np.where`, `np.clip`), bez
pętli.

**Nasze wybory:**
* cena: liniowa, q = 50 €, p = 300 € (cena jest bardzo ważna, już 300 € różnicy przesądza);
* hałas: liniowa, q = 2 dB, p = 7 dB. q = 2 dB, bo w Task 1 napisałeś, że
  różnice 1–3 dB nic nie znaczą;
* prędkość: liniowa, q = 50, p = 400;
* objętość: liniowa, q = 2, p = 20;
* łatwość obsługi (skala porządkowa 1–5): poziomowa, q = 0.5, p = 1.5;
* dysze: V-shape, p = 3.

### 2.2 Klasa `Criterion` (linie 65–80)

Przechowuje opis jednego kryterium. Metoda `preference(d)` robi dwie rzeczy:
1. Jeśli kryterium jest typu `min` (cena, hałas), **odwraca znak** różnicy:
   tańsza drukarka ma wtedy „dodatnią” różnicę.
2. Wywołuje odpowiednią funkcję preferencji.

### 2.3 Klasa `Problem` i `from_json` (linie 82–113)

* Wczytuje JSON i buduje z niego:
  * macierz `X` (4 × 6),
  * listę obiektów `Criterion`,
  * wagi znormalizowane do sumy 1 (funkcja `normalise`).
* Pełny JSON zostaje zapamiętany w `config`, żeby później odczytać z niego
  sekcje `efficiency` i `what_if`.

### 2.4 `preference_matrices` (linie 128–136) – krok 1 PROMETHEE

```python
d = X[:, j][:, None] - X[:, j][None, :]
```

To jest *broadcasting* w numpy: z wektora 4 wartości powstaje od razu
macierz 4 × 4 wszystkich różnic d(a, b). Wynikiem funkcji jest tablica
`P[j, a, b]` o kształcie (6 kryteriów, 4, 4). Przekątna jest zerowana, bo
alternatywy nie porównujemy z samą sobą.

### 2.5 `promethee` (linie 169–179) – krok 2 i 3

**Indeks preferencji (wielokryterialny):**

  π(a, b) = Σⱼ wⱼ · Pⱼ(a, b)

W kodzie robi to `np.tensordot(w, P, axes=1)`, czyli suma ważona po
kryteriach.

**Przepływy:**

* φ⁺(a) = 1/(n−1) · Σ_b π(a, b) – **przepływ dodatni**: jak bardzo a
  przewyższa inne. To suma **wiersza** macierzy π.
* φ⁻(a) = 1/(n−1) · Σ_b π(b, a) – **przepływ ujemny**: jak bardzo inne
  przewyższają a. To suma **kolumny** macierzy π.
* φ(a) = φ⁺(a) − φ⁻(a) – **przepływ netto**. Według niego powstaje ranking
  PROMETHEE II.

Funkcja zwraca obiekt `PrometheeResult`. Metody `ranking()` i `ranks()`
sortują alternatywy po φ malejąco.

**Ważna własność, z której korzysta reszta kodu:** φ(a) = Σⱼ wⱼ · φⱼ(a),
gdzie φⱼ to przepływ netto liczony tylko na kryterium j
(`unicriterion_flows`, linie 139–142). Oznacza to, że **przepływ netto jest
liniowy względem wag**. Test `test_net_flow_is_weighted_unicriterion_flows`
to sprawdza.

### 2.6 Przykład liczbowy: Snapmaker U1 vs Bambu H2D (wagi M1)

| Kryterium (waga) | różnica | P(U1, H2D) | P(H2D, U1) |
|---|---|---|---|
| Cena (0.30) | U1 tańsza o 1226 € > p = 300 | **1.000** | 0 |
| Hałas (0.15) | H2D cichsza o 5.9 dB → (5.9 − 2)/(7 − 2) | 0 | **0.780** |
| Prędkość (0.10) | H2D szybsza o 500 > p = 400 | 0 | **1.000** |
| Objętość (0.12) | H2D większa o 14.1 → (14.1 − 2)/(20 − 2) | 0 | **0.673** |
| Łatwość (0.08) | H2D lepsza o 1 → poziom „q < d ≤ p” | 0 | **0.500** |
| Dysze (0.25) | U1 ma 2 dysze więcej → 2/3 | **0.667** | 0 |

* π(U1, H2D) = 0.30·1 + 0.25·0.667 = **0.467**
* π(H2D, U1) = 0.15·0.78 + 0.10·1 + 0.12·0.673 + 0.08·0.5 = **0.338**

Pełna macierz π (wiersz = a, kolumna = b):

|  | K2 | U1 | H2D | Prusa |
|---|---|---|---|---|
| K2 | 0 | 0.224 | 0.347 | 0.174 |
| U1 | 0.576 | 0 | 0.467 | 0.569 |
| H2D | 0.263 | 0.338 | 0 | 0.336 |
| Prusa | 0.040 | 0.164 | 0.300 | 0 |

Dla U1:
* φ⁺ = (0.576 + 0.467 + 0.569)/3 = **0.537** (suma wiersza U1),
* φ⁻ = (0.224 + 0.338 + 0.164)/3 = **0.242** (suma kolumny U1),
* φ = **+0.295**, czyli pierwsze miejsce.

### 2.7 `promethee_I` (linie 182–210) – ranking częściowy

Dla każdej pary (a, b) kod porównuje osobno φ⁺ i φ⁻:

* **P** (a lepsze od b): φ⁺(a) ≥ φ⁺(b) **i** φ⁻(a) ≤ φ⁻(b), przy czym co
  najmniej jedna nierówność jest ostra.
* **I** (obojętność): oba przepływy są równe.
* **−**: odwrotnie, b jest lepsze od a.
* **R** (nieporównywalność): przepływy „się krzyżują”. Na przykład H2D i K2:
  H2D ma wyższe φ⁺ (0.313 vs 0.249), ale K2 ma niższe φ⁻ (0.293 vs 0.371).

`tol = 1e-9` chroni przed błędami zaokrągleń liczb zmiennoprzecinkowych.

### 2.8 `normalised_matrix` i `weighted_sum` (linie 216–246) – P × W

To metoda WSM z Task 1, użyta do porównania z PROMETHEE:
* normalizacja `ratio`: dla kryterium min wartość min/x, dla max wartość x/max;
* wynik = macierz znormalizowana × wektor wag.

Odtwarza wyniki arkusza co do 4. miejsca po przecinku (U1 0.850, H2D 0.673).
Sprawdza to test `test_wsm_reproduces_task1_spreadsheet`.

### 2.9 `kendall_tau` i `spearman_rho` (linie 249–262)

Miary zgodności dwóch rankingów:
* 1 oznacza identyczne,
* 0 oznacza brak związku,
* −1 oznacza odwrotne.

**Kendall τ** liczy pary alternatyw ułożone w tej samej kolejności minus pary
ułożone odwrotnie, podzielone przez liczbę par. **Spearman ρ** liczy się ze
wzoru 1 − 6Σd² / (n(n² − 1)).

---

## 3. `promethee/sensitivity.py` – analiza wrażliwości

Każdy przedział i każdą ocenę „rankingu bez zmian” liczymy przy tej samej
zasadzie: **gdy zmieniamy wagę kryterium j na t, pozostałe wagi zachowują
swoje proporcje i są przeskalowane tak, żeby suma wynosiła 1 − t.**

### 3.1 `phi_with_weight` (linie 27–37)

Z liniowości przepływów wynika:

  φ(t) = t · φⱼ + (1 − t) · φ_reszta

gdzie φ_reszta to przepływ policzony z pozostałych kryteriów
(`_phi_rest`). Nie trzeba więc za każdym razem liczyć PROMETHEE od nowa.

### 3.2 `stability_intervals` (linie 40–80) – dokładne przedziały stabilności

* Dla pary (a, b) różnica φ_a(t) − φ_b(t) jest **funkcją liniową** zmiennej
  t, więc ta para może zamienić się miejscami najwyżej raz.
* Punkt zamiany to t* = −dr / (dj − dr), gdzie:
  * dr = różnica przepływów z pozostałych kryteriów,
  * dj = różnica przepływów na kryterium j.
* Najbliższe punkty zamiany poniżej i powyżej obecnej wagi wyznaczają
  przedział, w którym **cały ranking** się nie zmienia.
* Gdy bierzemy pod uwagę tylko pary ze zwycięzcą, dostajemy przedział, w
  którym **zwycięzca** się nie zmienia.

Wynik jest dokładny (analityczny), a nie przybliżony siatką.
`test_stability_intervals_are_exact` sprawdza, że tuż wewnątrz przedziału
ranking jest taki sam, a tuż za granicą już inny.

Przykład: U1 pozostaje najlepsza dla wagi ceny w przedziale [0.148, 1].
Poniżej 0.148 wygrywa H2D.

### 3.3 `weight_sweep` (linie 83–87)

Zmienia wagę jednego kryterium od 0 do 1 w 101 krokach. Na tej podstawie
powstaje wykres `05_weight_sweeps.png`.

### 3.4 `monte_carlo` (linie 90–120) – akceptowalność pozycji

Losujemy 20 000 wektorów wag i dla każdego liczymy ranking. Są dwa tryby:

* `"local"`: każda waga bazowa jest mnożona przez losową liczbę z przedziału
  U(1 − spread, 1 + spread), potem wagi są normalizowane. Używamy ±20 % i
  ±50 %, co odpowiada pytaniu „moje wagi są niedokładne”.
* `"simplex"`: rozkład Dirichleta(1, …, 1), czyli wagi równomiernie losowe
  na całym zbiorze dopuszczalnych wag. Odpowiada to pytaniu „nie wiem nic o
  wagach”.

Trik wydajnościowy: `PHI = W @ phi_j.T`. Funkcje preferencji nie zależą od
wag, więc wszystkie 20 000 rankingów to jedno mnożenie macierzy.

Wynik `acc[a, r]` to odsetek losowań, w których alternatywa a była na
miejscu r + 1. Dla U1 przy ±20 % wynosi 100 % na 1. miejscu.

### 3.5 `threshold_sensitivity` i `single_threshold_sweep` (linie 123–162)

* Mnożymy **wszystkie** progi q, p, s przez 0.25, 0.5, …, 2 i liczymy
  ranking od nowa.
* Osobno sprawdzamy wariant, w którym każde kryterium ma funkcję „usual”
  (bez progów).
* `single_threshold_sweep` zmienia próg p jednego kryterium; na tej podstawie
  powstaje wykres `07_threshold_sweeps.png`.

Tutaj trzeba liczyć PROMETHEE od nowa, bo zmiana progów zmienia macierze P.
`copy.deepcopy` zapewnia, że oryginalne kryteria zostają nienaruszone.

### 3.6 `promethee/fuzzy.py` – F-PROMETHEE (wymaganie 5a)

Niepewne wartości z macierzy to **trójkątne liczby rozmyte (l; m; u)**:
* cena ±5 %, a dla U1 (899; 899; 1099), bo to promocja;
* hałas ±2 dB, a dla K2 (45; 50; 52), bo producent podaje 45 dB;
* łatwość obsługi ±0.5, bo to moja ocena.

Wagi też są trójkątami, ±10 %: (0.9w; w; 1.1w), np. cena (0.27; 0.30; 0.33).

* `fuzzy_matrix`: buduje trzy macierze L, M, U (min, wartość, max). M to
  zwykła macierz z Task 1.
* `fuzzy_promethee`: zwykłe PROMETHEE, tylko **na trzech liczbach naraz**:
  1. różnica: (a_l − b_u; a_m − b_m; a_u − b_l). Najmniejsza różnica to
     najgorsze a minus najlepsze b;
  2. preferencja: funkcja preferencji osobno na każdej z trzech różnic;
  3. π~ = Σ w~ⱼ · P~ⱼ, czyli trójkąt wagi razy trójkąt preferencji:
     dolna × dolna, środkowa × środkowa, górna × górna;
  4. φ⁺~ i φ⁻~ to średnie, a φ~ = φ⁺~ − φ⁻~ = (φ⁺_l − φ⁻_u; φ⁺_m − φ⁻_m; φ⁺_u − φ⁻_l);
  5. ranking według **środka ciężkości** (l + m + u) / 3.

  Wynik to **trójkąt** dla każdej drukarki, a środkowa liczba m to dokładnie
  zwykłe φ.

Testy:
* m = zwykłe φ;
* l ≤ m ≤ u;
* dokładne dane dają dokładny wynik;
* 2000 losowych macierzy z zakresu niepewności zawsze daje φ między l a u.

---

## 4. `promethee/efficiency.py` – rozszerzenie Efficiency measuring

Cel z Task 1: *„find the printer that gives me the most for my money”*. Ta
analiza oddziela **to, co płacę** od **tego, co dostaję**.

### 4.1 `split_flows` – φ korzyści i φ kosztu

Bierze przepływy jednokryterialne φⱼ (te same co w rankingu) i dzieli je na
dwie grupy:
* **φ kosztu** = φ kryterium ceny (wyżej = taniej);
* **φ korzyści** = średnia ważona φⱼ z 5 pozostałych kryteriów. Wagi
  0.15 / 0.10 / 0.12 / 0.08 / 0.25 są przeskalowane tak, żeby sumowały się do 1.

Sprawdzenie: 0.30 · φ kosztu + 0.70 · φ korzyści = zwykłe φ z rankingu
(test `test_efficiency_and_budget_choice`).

W języku doktora: cena to **wejście (input)**, a pozostałe kryteria to **wyjścia (outputs)**.

### 4.2 `efficient_set` – kto jest efektywny

Drukarka jest **efektywna** (niezdominowana, Pareto), jeśli **żadna inna nie
jest jednocześnie lepsza i tańsza**. Kod sprawdza każdą parę: jeśli b ma φ
korzyści i φ kosztu nie gorsze od a, a w jednym z nich jest lepsza, to a jest
zdominowana.

Wynik:
* efektywne są tylko U1 (najtańsza) i H2D (najlepsza);
* K2 Plus i Prusa są zdominowane przez U1.

### 4.3 `best_within_budget` i `budget_sweep` – odczyt z granicy efektywności

Dla budżetu B bierze drukarki z ceną ≤ B i wybiera tę o największym φ
korzyści. `budget_sweep` robi to dla budżetów od 800 do 2500 € co 1 €:
* 899–2124 € → U1,
* od 2125 € → H2D.

**To nie jest PROMETHEE V.** PROMETHEE V wybiera **portfel**, czyli
kombinację kilku alternatyw (np. flotę samochodów dla firmy). Doktor pisze,
że ma sens tylko wtedy, gdy łączy się alternatywy. Ja kupuję jedną drukarkę,
więc PROMETHEE V nie pasuje.

### 4.5 `efficiency_acceptability` – odporność

Losuje 20 000 zestawów wag (jak Monte Carlo z punktu 3.4) i liczy, jak często
każda drukarka jest efektywna:
* U1: 100 % (zawsze, bo jest najtańsza),
* H2D: prawie 100 %,
* Prusa: prawie nigdy.

---

## 5. `run_analysis.py` – uruchomienie całości

Funkcja `main` wykonuje kolejne sekcje. Każda zapisuje plik CSV, wykres PNG
i fragment `results.md`.

| Sekcja w kodzie | Co liczy | Pliki |
|---|---|---|
| `data` | tabela wejściowa i parametry kryteriów | `performance_table.csv`, `criteria_parameters.csv` |
| `PROMETHEE I/II` | φ⁺, φ⁻, φ, ranking; macierz π; φⱼ; relacje PROMETHEE I | `promethee_flows.csv`, `01_…`, `02_…`, `03_…` |
| `ranking comparison` | ranking PROMETHEE i WSM dla 7 zestawów wag, τ Kendalla, ρ Spearmana | `ranking_comparison_*.csv`, `04_…` |
| `sensitivity: weights` | przedziały stabilności, wykresy wag, Monte Carlo | `weight_stability_intervals.csv`, `05_…`, `06_…` |
| `sensitivity: thresholds` | skalowanie progów i wariant „usual” | `threshold_sensitivity.csv`, `07_…` |
| `what-if` | cena H2D od 700 do 2500 € w 361 krokach; punkt zmiany zwycięzcy liczony interpolacją liniową (≈ 1096 €) | `what_if.csv`, `08_…` |
| `F-PROMETHEE` | macierz TFN, trójkątne przepływy φ~ = (l; m; u), ranking według środka ciężkości | `fuzzy_decision_matrix.csv`, `fuzzy_promethee.csv`, `11_…` |
| `efficiency` | φ korzyści i kosztu, zbiór efektywny (granica), wybór dla każdego budżetu, odporność | `efficiency*.csv`, `budget_choice.csv`, `09_…`, `10_…` |

Funkcje pomocnicze:
* `md_table` zamienia tabelę pandas na tabelę Markdown;
* `spread_labels` rozsuwa etykiety na wykresie PROMETHEE I, żeby na siebie
  nie nachodziły;
* `save` zapisuje wykres.

Uruchomienie: `python run_analysis.py` (domyślnie `data/problem.json`) albo
`python run_analysis.py inny_plik.json`.

---

## 6. `tests/test_promethee.py` – testy (pytest)

| Test | Co sprawdza |
|---|---|
| `test_preference_functions_shapes` | każda z 6 funkcji preferencji daje poprawne wartości dla znanych różnic |
| `test_hand_computed_example` | mały przykład 3 × 2 policzony ręcznie: π, φ⁺, φ⁻, φ i relacje PROMETHEE I |
| `test_net_flow_is_weighted_unicriterion_flows` | φ = Σ wⱼ φⱼ oraz Σ φ = 0 |
| `test_stability_intervals_are_exact` | ranking jest stały wewnątrz przedziału, a zmienia się tuż za granicą |
| `test_monte_carlo_rows_sum_to_one` | macierz akceptowalności jest poprawna: wiersze i kolumny sumują się do 1 |
| `test_wsm_reproduces_task1_spreadsheet` | WSM daje dokładnie wyniki z arkusza Task 1 |
| `test_efficiency_and_budget_choice` | φ korzyści i kosztu składają się na φ; najtańsza i najlepsza są efektywne; przy zbyt małym budżecie nic nie jest wybierane, a bez limitu wybierana jest najlepsza |
| `test_kendall_tau` | τ = 1 dla identycznych i −1 dla odwróconych rankingów |

Uruchomienie: `python -m pytest -q`.

---

## 7. `tools/build_notebook.py` – notebook do Colaba

* Wkleja aktualne pliki kodu i dane do notebooka jako komórki `%%writefile`,
  więc w Colabie nie trzeba niczego klonować.
* Dodaje komórki wyświetlające wszystkie tabele i wykresy.
* Uruchamia notebook i zapisuje go razem z wynikami.
* Przerywa z błędem, jeśli jakiś plik z `results/` nie byłby nigdzie
  pokazany.

---

## 8. Pytania, które może zadać prowadzący

**Dlaczego własny kod, a nie Visual PROMETHEE?**
Zadanie pozwala na jedno albo drugie. Własny kod pozwala zrobić analizy,
których VP nie ma: dokładne przedziały stabilności, Monte Carlo, F-PROMETHEE, efficiency i
analizę ceny H2D. Zgodnie z instrukcją nie odtwarzam wyników VP, w tym
płaszczyzny GAIA.

**Skąd wiadomo, że kod liczy poprawnie?**
* Testy z przykładem policzonym ręcznie.
* Σ φ = 0, co zawsze zachodzi w PROMETHEE.
* WSM odtwarza arkusz Task 1 co do cyfry.
* W tym dokumencie jest ręcznie przeliczone π(U1, H2D) = 0.467.

**Po co φ⁺ i φ⁻, skoro jest φ?**
φ (PROMETHEE II) daje pełny ranking, ale gubi informację. φ⁺ i φ⁻
(PROMETHEE I) pokazują, czy alternatywa jest dobra „wszędzie po trochu”, czy
„bardzo dobra w jednym, bardzo słaba w drugim”. Tak jest z H2D, która jest
nieporównywalna z K2 i Prusą.

**Skąd progi q i p?**
To moja ocena, czyli tak zwana informacja dodatkowa od decydenta. Jest
uzasadniona w REPORT.md, sekcja 1. Analiza 5.3 pokazuje, że przy skalowaniu
wszystkich progów od ×0.25 do ×2 zwycięzca się nie zmienia.

**Czym PROMETHEE różni się od WSM?**
* WSM jest w pełni kompensacyjny i liniowy: każda różnica liczy się
  proporcjonalnie do swojej wielkości.
* PROMETHEE porównuje pary alternatyw i używa progów:
  * małe różnice (poniżej q) są pomijane;
  * duże różnice (powyżej p) dają pełną preferencję, która dalej już nie
    rośnie, jak przy cenie H2D.

  Dlatego np. w scenariuszu „price matters less” WSM wybiera U1, a PROMETHEE
  wybiera H2D.

**Dlaczego przedziały stabilności są „dokładne”?**
Przepływ netto jest liniowy względem wag, więc każda para alternatyw zmienia
kolejność w dokładnie jednym punkcie, który da się wyliczyć wzorem. Nie
trzeba przeszukiwać siatki wartości.

**Dlaczego rozszerzenie Efficiency?**
* Cel z Task 1 to dosłownie *„the printer that gives me the most for my
  money”*, a analiza efektywności odpowiada dokładnie na to pytanie.
* Mam naturalne wejście (cena) i wyjścia (to, co drukarka oferuje).
* Pokazuje, że K2 Plus i Prusa są zdominowane: U1 jest od nich tańsza i
  lepsza.
* Pokazuje, że jedyny prawdziwy wybór to „U1 albo dopłacić 1226 € do H2D”.
* Jest jeden decydent, więc GDSS nie ma sensu. PROMETHEE V służy do łączenia
  alternatyw w portfel, a ja kupuję jedną drukarkę.

**Dlaczego F-PROMETHEE, a nie Monte Carlo, w wymaganiu 5?**
* Niepewność w moich danych to przedziały typu „od–do” (45–50 dB, 899–1099 €),
  a nie rozkłady prawdopodobieństwa, których nie znam. Trójkątna liczba
  rozmyta opisuje to naturalnie.
* Doktor zaleca F-PROMETHEE osobom, które piszą własny kod w Pythonie.
* Monte Carlo na wagach zostało jako zwykła analiza wrażliwości (5.2).

**Co oznacza 62 % dla H2D w Monte Carlo przy losowych wagach?**
Gdyby wagi były zupełnie przypadkowe, H2D wygrywałaby najczęściej, bo
obiektywnie jest najmocniejszą maszyną. U1 wygrywa dzięki moim priorytetom:
cena i liczba dysz mają razem 55 % wagi.
