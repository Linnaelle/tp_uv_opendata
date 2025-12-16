# TP2 - Pipeline Météo + Géo

## 🎯 Objectif

Pipeline d'acquisition, enrichissement et transformation de données météorologiques françaises avec géolocalisation précise.

## 🌤️ Description

Ce pipeline combine deux APIs Open Data :
- **OpenMeteo** : Prévisions météo sur 7 jours
- **API Adresse** : Géocodage précis des villes françaises

Le résultat est un dataset enrichi contenant des prévisions météo géolocalisées pour les principales villes de France.

## 🏗️ Architecture

```
Pipeline Météo + Géo
├── 1. Géocodage des villes (API Adresse)
├── 2. Récupération météo (OpenMeteo)
├── 3. Enrichissement croisé
├── 4. Transformation et nettoyage
├── 5. Scoring de qualité
├── 6. Génération de rapport
└── 7. Stockage Parquet
```

## 🛠️ Technologies

- **Python 3.12+** avec `uv`
- **httpx** : Requêtes HTTP async
- **pandas** : Manipulation de données
- **pydantic** : Validation de modèles
- **tenacity** : Retry automatique
- **pytest** : Tests unitaires
- **pyarrow** : Format Parquet

## 📦 Installation

### Prérequis
- Python 3.12+
- uv installé
- (Optionnel) Ollama pour recommandations IA

### Installation

```bash
# Se placer dans le dossier
cd tp2-pipeline

# Installer les dépendances
uv sync

# Vérifier l'installation
uv run python -c "import httpx, pandas, pydantic; print('✅ OK')"
```

## 🚀 Utilisation

### Exécution simple

```bash
# Pipeline complet (50 villes, 7 jours)
uv run python -m pipeline.main

# Personnalisé
uv run python -m pipeline.main --max-cities 20 --forecast-days 3
```

### Depuis Python

```python
from pipeline.main import run_weather_pipeline

# Exécuter le pipeline
stats = run_weather_pipeline(
    max_cities=30,
    forecast_days=5,
    verbose=True
)

print(f"Qualité : {stats['quality']['quality_grade']}")
```

### Options CLI

```bash
# Aide
uv run python -m pipeline.main --help

# Options disponibles
--max-cities, -m   # Nombre de villes (défaut: 50)
--forecast-days, -d # Jours de prévisions (défaut: 7)
--verbose, -v       # Mode verbeux
```

## 📊 Données générées

### Structure du dataset final

| Colonne | Type | Description |
|---------|------|-------------|
| city | str | Nom de la ville |
| forecast_date | date | Date de la prévision |
| temperature_max | float | Température max (°C) |
| temperature_min | float | Température min (°C) |
| temperature_avg | float | Température moyenne (calculée) |
| precipitation_sum | float | Précipitations totales (mm) |
| rain_sum | float | Pluie (mm) |
| snowfall_sum | float | Neige (cm) |
| wind_speed_max | float | Vitesse vent max (km/h) |
| latitude | float | Latitude |
| longitude | float | Longitude |
| city_code | str | Code INSEE |
| department | str | Département |
| region | str | Région |
| geocoding_score | float | Score géocodage (0-1) |

### Colonnes dérivées

- `temperature_range` : Amplitude thermique
- `temp_category` : Catégorie de température
- `precip_intensity` : Intensité des précipitations
- `has_snow` : Présence de neige
- `is_windy` : Conditions venteuses
- `day_of_week` : Jour de la semaine
- `is_weekend` : Week-end ou non

## 📂 Structure du projet

```
tp2-pipeline/
├── pipeline/
│   ├── __init__.py
│   ├── config.py              # Configuration centralisée
│   ├── models.py              # Modèles Pydantic
│   ├── fetchers/
│   │   ├── base.py           # Classe abstraite
│   │   ├── openmeteo.py      # API météo
│   │   └── adresse.py        # API géocodage
│   ├── enricher.py           # Enrichissement croisé
│   ├── transformer.py        # Transformations
│   ├── quality.py            # Scoring et rapport
│   ├── storage.py            # Stockage Parquet
│   └── main.py               # Orchestration
├── tests/
│   ├── test_fetchers.py
│   └── test_transformer.py
├── data/
│   ├── raw/                  # JSON bruts
│   ├── processed/            # Parquet nettoyés
│   └── reports/              # Rapports qualité
├── pyproject.toml
├── README.md
└── .gitignore
```

## 🧪 Tests

```bash
# Tous les tests
uv run pytest tests/ -v

# Tests spécifiques
uv run pytest tests/test_fetchers.py::TestAdresseFetcher::test_geocode_paris -v

# Avec couverture
uv run pytest tests/ --cov=pipeline --cov-report=html
open htmlcov/index.html
```

## 📈 Exemple de rapport qualité

Le pipeline génère automatiquement un rapport Markdown :

```
Rapport de Qualité - Données Météo
===================================

Note globale : A
Total prévisions : 350
Villes : 50
Complétude : 95.2%
Géocodage : 98.0%
```

## 🎯 Cas d'usage

1. **Dashboard météo régional** : Visualiser les prévisions par région
2. **Analyse climatique** : Comparer les tendances entre villes
3. **Alertes météo** : Détecter les conditions extrêmes
4. **Planification logistique** : Optimiser les déplacements selon météo
5. **Agriculture** : Prévisions pour gestion des cultures

## 📚 APIs utilisées

### OpenMeteo
- **URL** : https://api.open-meteo.com/v1/forecast
- **Limite** : 10 000 requêtes/jour (gratuit)
- **Documentation** : https://open-meteo.com/en/docs

### API Adresse
- **URL** : https://api-adresse.data.gouv.fr
- **Limite** : Aucune (service public)
- **Documentation** : https://adresse.data.gouv.fr/api-doc/adresse

## ⚙️ Configuration

Modifiez `pipeline/config.py` pour personnaliser :

```python
# Nombre de villes par défaut
MAX_CITIES = 50

# Jours de prévisions
FORECAST_DAYS = 7

# Liste des villes
FRENCH_CITIES = ["Paris", "Lyon", ...]

# Seuils de qualité
QUALITY_THRESHOLDS = {
    "completeness_min": 0.8,
    "geocoding_score_min": 0.7,
}
```

## 🔗 Ressources

- [Documentation uv](https://docs.astral.sh/uv/)
- [OpenMeteo API](https://open-meteo.com/)
- [API Adresse](https://adresse.data.gouv.fr/)
- [Pydantic](https://docs.pydantic.dev/)
- [pytest](https://docs.pytest.org/)
