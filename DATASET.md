# Dataset used

**Fichier consolidé des Bornes de Recharge pour Véhicules Électriques (IRVE)**
Publisher: data.gouv.fr (consolidation of operators' declarations, schema `etalab/schema-irve-statique`)
Licence: Licence Ouverte / Open Licence 2.0 (Etalab)

- Dataset page: https://www.data.gouv.fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques/
- File (consolidated CSV, latest schema version — stable URL used by the app):
  https://www.data.gouv.fr/api/1/datasets/r/eb76d20a-8501-400e-b336-d85724de5435
- Schema documentation: https://schema.data.gouv.fr/etalab/schema-irve-statique/latest.html
- Successor page (migration announced, old page kept until 31/12/2026):
  https://transport.data.gouv.fr/datasets/fichier-consolide-des-bornes-de-recharge-pour-vehicules-electriques

The raw CSV (~86 MB) is not included in the zip: `python scripts/download_data.py` downloads it,
records its SHA-256 and download date in `data/raw/manifest.json`, and builds the processed table.

Reference data bundled in the repository:
- `data/reference/departements.csv` — INSEE populations légales (in force 1 Jan 2026) via
  `@etalab/decoupage-administratif` 6.0.0 (Licence Ouverte); area computed from IGN boundaries.
- `assets/departements.geojson` — IGN Admin Express (Licence Ouverte) via github.com/gregoiredavid/france-geojson.

Suggested citation: *data.gouv.fr (2026). Fichier consolidé des Bornes de Recharge pour Véhicules
Électriques. Licence Ouverte 2.0. Downloaded on <date in manifest.json>.*
