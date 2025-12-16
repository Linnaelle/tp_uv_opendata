"""Configuration centralisée du pipeline météo."""
from pathlib import Path
from dataclasses import dataclass

# === Chemins ===
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = DATA_DIR / "reports"

for dir_path in [RAW_DIR, PROCESSED_DIR, REPORTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)


@dataclass
class APIConfig:
    """Configuration d'une API."""
    name: str
    base_url: str
    timeout: int
    rate_limit: float  # secondes entre requêtes
    headers: dict = None
    
    def __post_init__(self):
        self.headers = self.headers or {}


# === Configurations des APIs ===
OPENMETEO_CONFIG = APIConfig(
    name="OpenMeteo",
    base_url="https://api.open-meteo.com/v1",
    timeout=30,
    rate_limit=0.5,  # 2 requêtes par seconde max
    headers={}
)

ADRESSE_CONFIG = APIConfig(
    name="API Adresse",
    base_url="https://api-adresse.data.gouv.fr",
    timeout=10,
    rate_limit=0.1,  # Très rapide
    headers={}
)

# === Paramètres d'acquisition ===
MAX_CITIES = 50  # Nombre de villes à traiter
FORECAST_DAYS = 7  # Jours de prévisions

# === Liste des grandes villes françaises ===
FRENCH_CITIES = [
    "Paris", "Marseille", "Lyon", "Toulouse", "Nice",
    "Nantes", "Strasbourg", "Montpellier", "Bordeaux", "Lille",
    "Rennes", "Reims", "Saint-Étienne", "Toulon", "Le Havre",
    "Grenoble", "Dijon", "Angers", "Nîmes", "Villeurbanne",
    "Saint-Denis", "Clermont-Ferrand", "Le Mans", "Aix-en-Provence", "Brest",
    "Tours", "Amiens", "Limoges", "Annecy", "Perpignan",
    "Besançon", "Metz", "Orléans", "Rouen", "Mulhouse",
    "Caen", "Nancy", "Argenteuil", "Montreuil", "Saint-Paul",
    "Roubaix", "Tourcoing", "Nanterre", "Avignon", "Vitry-sur-Seine",
    "Créteil", "Dunkerque", "Poitiers", "Asnières-sur-Seine", "Courbevoie"
]

# === Seuils de qualité ===
QUALITY_THRESHOLDS = {
    "completeness_min": 0.8,      # 80% des champs remplis
    "geocoding_score_min": 0.7,   # Score géocodage minimum
    "duplicates_max_pct": 2.0,    # Max 2% de doublons
    "valid_coords_min": 0.95,     # 95% coordonnées valides
}