# ⚡ Plugged in or left out? — France's public EV charging network

A data-storytelling dashboard built with **Streamlit** on the French national registry of
public electric-vehicle charging points (IRVE). It answers one question for local decision-makers:

> **France is racing towards 400,000 public charge points by 2030 — but is everyone getting
> plugged in, or are some territories being left out?**

*Individual student project — EFREI Paris, Data Visualization 2026 · #EFREIDataStories2026*

---

## 1. The story

| Step | Section in the app | Question | Main visual |
|---|---|---|---|
| Hook | *The question* | Why does public charging matter? | Live headline: per-capita gap between best and worst department |
| Context | *Key figures* | How big is the network today? | KPI header tied to filters |
| Analysis | 1 · Growth | How fast is it growing? | Cumulative stacked area by power class + yearly bars, 100k milestone annotated |
| Analysis | 2 · Geography | Where are the chargers vs where people live? | Department choropleth + top/bottom ranking |
| Analysis | 3 · Urban vs rural | Is access fair between dense and rural areas? | Density scatter (log) + Lorenz curve & Gini |
| Analysis | 4 · Fast charging | Is fast charging (≥50 kW) spread as widely? | 100 % stacked bars by region + **small multiples** over time |
| Analysis | 5 · Who builds it | Who operates the network? | Operator shares + Herfindahl index |
| Drill-down | 6 · Zoom | What does my department look like? | Station map (click the choropleth or pick a department) |
| What-if | 7 · 2030 | Will the target be reached? | Projection with scenario sliders and documented assumptions |
| Transparency | Data quality | Can we trust the data? | Validation checks, missingness chart, provenance |
| Implications | Takeaways | So what? | Insights computed live + recommendations + next steps |

**Audience:** elected officials and planners in departments, regions and energy syndicates
(*syndicats d'énergie*) who allocate public funding for chargers; secondary audience: EV drivers.

Every headline sentence (blue boxes) is **computed from the filtered data**, so the story
re-tells itself when you filter on a region, a period or a charger type.

## 2. Data

| | |
|---|---|
| **Dataset** | *Fichier consolidé des Bornes de Recharge pour Véhicules Électriques (IRVE)* |
| **Portal** | data.gouv.fr — <https://www.data.gouv.fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques/> |
| **File used** | Consolidated CSV, latest schema version (stable URL): <https://www.data.gouv.fr/api/1/datasets/r/eb76d20a-8501-400e-b336-d85724de5435> |
| **Schema** | [etalab/schema-irve-statique](https://schema.data.gouv.fr/etalab/schema-irve-statique/latest.html) v2.3.x — one row per *point de charge* |
| **Licence** | Licence Ouverte / Open Licence 2.0 (Etalab) — reuse allowed with attribution |
| **Size** | ≈ 90 MB CSV — the submitted zip includes the 23 Oct 2026 snapshot (`data/raw/`); the GitHub repo does not, `scripts/download_data.py` fetches it |
| **Note** | data.gouv.fr announces the dataset is migrating to [transport.data.gouv.fr](https://transport.data.gouv.fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques) and the old page stays until 31/12/2026. If the URL changes, set `IRVE_URL=<new url>`; no code change needed. |

**Bundled reference data** (small, in the repo, rebuilt by `scripts/build_reference.py`):

- `data/reference/departements.csv` — 101 departments with region, **population** (INSEE populations
  légales in force on 1 Jan 2026, via the `@etalab/decoupage-administratif` 6.0.0 package, Licence Ouverte)
  and **area** (km², equal-area projection).
- `assets/departements.geojson` — department boundaries, IGN Admin Express (Licence Ouverte) via
  [gregoiredavid/france-geojson](https://github.com/gregoiredavid/france-geojson), re-simplified (≈ 280 kB).

**Reference figures quoted in the app:** national target of 100,000 public points (end-2021), reached on
5 May 2023 according to Avere-France; government target of 400,000 points by 2030; Avere-France barometer:
200,045 public points on 31 July 2026.

## 3. Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/download_data.py      # ~90 MB once, then cached (or: make data)
streamlit run app.py                 # http://localhost:8501
```

- **Using the submitted zip?** The data snapshot is already included: skip `download_data.py` and run `streamlit run app.py` directly.
- If the download step is skipped and no data is present, the app downloads the file itself on first launch.
- Already have the CSV? `python scripts/download_data.py --from-file path/to/file.csv`
- Get the latest version: `python scripts/download_data.py --force` (or `--max-age 7`).
- Tests (no download needed): `pip install -r requirements-dev.txt && pytest -q`
- With `make`: `make install`, `make data`, `make run`, `make test`.

### Deploy on Streamlit Community Cloud

1. Push this folder to a public GitHub repository (the `.gitignore` keeps raw data out).
2. On <https://share.streamlit.io>, *New app* → pick the repo, branch, `app.py`; under *Advanced settings*
   choose Python 3.12.
3. First load downloads and processes the file (~30 s); later loads use the cache.

## 4. Project structure

```
app.py                  # page config, sidebar filters, section order
sections/
  intro.py              # hook, audience, questions, caveats
  overview.py           # KPI header + 1 · growth
  deep_dives.py         # 2 · geography, 3 · urban/rural, 4 · fast charging, 5 · operators, 6 · zoom
  whatif.py             # 7 · projection to 2030 with scenario sliders
  quality.py            # validation checks, missingness, provenance, ethics
  conclusions.py        # takeaways, implications, next steps
utils/
  constants.py          # URLs, validation thresholds, colours, targets, seed
  io.py                 # download + cache + manifest (SHA-256), raw/processed loading
  prep.py               # cleaning, validation, department assignment, feature engineering, Gini
  context.py            # cached loading/filtering for Streamlit
  viz.py                # every chart (one consistent style)
  ui.py                 # headline boxes, accessible chart wrapper, data tables
scripts/
  download_data.py      # fetch & process (cached, resumable-safe)
  build_reference.py    # rebuild population table + boundaries
data/reference/         # bundled small reference tables
assets/                 # department GeoJSON
tests/test_prep.py      # unit tests for cleaning rules
docs/storyboard.md      # storyboard + demo-video script
```

## 5. Data work

The raw file is read **as text** (only the 26 columns used), then every rule below is applied and
logged; the app's *Data quality* section shows how many rows each rule touched.

| Check | Rule | Action |
|---|---|---|
| Exact duplicates | identical rows | dropped |
| Duplicate charge-point ID | same `id_pdc_itinerance` | keep the most recently updated (`date_maj`) |
| Power in W | `puissance_nominale` > 1,000 | ÷ 1,000 |
| Power = 0 | placeholder | set to missing |
| Implausible power | outside 1–500 kW | set to missing |
| Swapped coordinates | valid only once lon/lat inverted | swapped back |
| Outside France | not in metropole or the 5 DROM (e.g. 0,0; lon = lat; overseas collectivities) | set to missing |
| Coordinates fallback | consolidated lon/lat missing | parsed from `coordonneesXY` |
| Dates | unparsable, before 2010 (e.g. `0001-01-01`) or after the data snapshot | set to missing |
| Department | point-in-polygon on boundaries, snapping ≤ 5 km for points just off the simplified coastline; fallback = INSEE commune code | unlocated points excluded from geo analyses |

**Feature engineering:** power classes (≤7.4 / 7.4–22 / 22–50 / 50–150 / ≥150 kW), `is_fast` (≥50 kW),
commissioning year/month, normalised operator name (case, accents, legal suffixes, eMI3 IDs),
English labels for location and access type; per-department indicators: points, stations, MW,
points / fast points per 100k inhabitants, kW per 1,000 inhabitants, fast share, population density;
inequality metrics (population-weighted Lorenz curve and Gini), Spearman correlation, Herfindahl index.

**Snapshot date:** the reference "today" is the latest plausible `date_maj` in the file (≤ download date),
so "last 12 months" figures are not distorted by publication lag.

## 6. Visual design & accessibility

- One chart style for the whole app (`utils/viz.py`): system sans font, recessive grid, axis titles
  with units, hover tooltips on every mark, legends + direct labels.
- **Colour:** power classes are ordered, so they use a single-hue blue ramp (light → dark), not a
  rainbow; categorical colours follow a fixed order. Both palettes were checked with a colour-vision-
  deficiency and contrast validator; the ramp's lightest step keeps ≥ 2:1 contrast on the background.
  Light theme enforced in `.streamlit/config.toml` so contrast is what was validated.
- **Alt text:** every chart passes a meaningful `alt` description to `st.plotly_chart` and prints it as a
  visible caption; every chart has a downloadable data table.
- Colour never carries meaning alone (labels, symbols — e.g. diamonds for overseas departments).

## 7. Performance

`usecols` + text dtypes on read; processed table saved as Parquet and **reused while the raw file's SHA-256
is unchanged**; `st.cache_data` on loading, filtering and department aggregation; spatial join run on
*unique* coordinates with an STR-tree; station map thinned to 6,000 stations with a fixed seed
(`seeds.json`). Full pipeline ≈ 3 s; filter changes are instant.

## 8. Limitations & ethics

- **Declared, not audited:** operators publish their own data; coverage is uneven and totals differ from
  the Avere-France barometer. No information on closures, availability or price.
- **A large share of points has no usable commissioning date** (29 % in the 23 Oct 2026 snapshot) — time charts show dated points only and say so; the projection scales them explicitly (assumption stated in the app).
- **Per-capita ≠ need:** through-traffic, tourism and home-charging access vary by territory.
  Correlations are described, never presented as causes.
- **Privacy:** operator contact e-mails and phone numbers present in the source are not loaded; all
  results are aggregated to stations or administrative areas.
- **Licences:** data under Licence Ouverte 2.0 (attribution in the app footer and here); code under MIT.

## 9. Submission

| | |
|---|---|
| **Student** | Ilyes Ben Said — 20230357 — group BIA |
| **Repository** | <https://github.com/ilyes064/irve-dashboard> |
| **Data snapshot** | downloaded 23 Oct 2026 (SHA-256 in `data/raw/manifest.json`); included in the submitted zip so the app runs offline |
| **Demo video** | submitted with this zip (script in `docs/storyboard.md`) |

## Sources

- Dataset: data.gouv.fr — Fichier consolidé des Bornes de Recharge pour Véhicules Électriques (Licence Ouverte 2.0)
- INSEE populations légales (via `@etalab/decoupage-administratif`), IGN Admin Express
- Avere-France / press coverage: 100,000 points reached 5 May 2023 ([Option Finance](https://www.optionfinance.fr/info-financiere-en-continu/d/2023-05-05-mobilite-electrique-lobjectif-de-100-000-bornes-de-recharge-en-france-atteint-ce-5-mai-avere.html));
  200,045 points on 31 July 2026 and the 400,000 target for 2030 ([Automobile Propre](https://www.automobile-propre.com/articles/cest-fait-la-france-passe-le-cap-des-200-000-points-de-recharge-ouverts-au-public/))
