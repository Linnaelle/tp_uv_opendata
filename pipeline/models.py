"""Modèles de données avec validation."""
from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime, date


class WeatherForecast(BaseModel):
    """Modèle d'une prévision météo."""
    # Identification
    city: str
    forecast_date: date
    
    # Données météo OpenMeteo
    temperature_max: Optional[float] = None  # °C
    temperature_min: Optional[float] = None  # °C
    precipitation_sum: Optional[float] = None  # mm
    rain_sum: Optional[float] = None  # mm
    snowfall_sum: Optional[float] = None  # cm
    wind_speed_max: Optional[float] = None  # km/h
    wind_gusts_max: Optional[float] = None  # km/h
    
    # Données enrichies (API Adresse)
    city_label: Optional[str] = None  # Nom complet normalisé
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    postal_code: Optional[str] = None
    city_code: Optional[str] = None  # Code INSEE
    department: Optional[str] = None
    region: Optional[str] = None
    population: Optional[int] = None
    geocoding_score: Optional[float] = None
    
    # Métadonnées
    fetched_at: datetime = Field(default_factory=datetime.now)
    quality_score: Optional[float] = None
    
    @validator('temperature_max', 'temperature_min')
    def validate_temperature(cls, v):
        """Valide que la température est dans une plage réaliste."""
        if v is not None and (v < -50 or v > 60):
            return None
        return v
    
    @validator('precipitation_sum', 'rain_sum', 'snowfall_sum')
    def validate_positive(cls, v):
        """Valide que les précipitations sont positives."""
        if v is not None and v < 0:
            return None
        return v
    
    @validator('wind_speed_max', 'wind_gusts_max')
    def validate_wind(cls, v):
        """Valide la vitesse du vent."""
        if v is not None and (v < 0 or v > 300):
            return None
        return v


class GeocodingResult(BaseModel):
    """Résultat de géocodage d'une ville."""
    original_city: str
    label: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    score: float = 0.0
    postal_code: Optional[str] = None
    city_code: Optional[str] = None  # Code INSEE
    city: Optional[str] = None
    context: Optional[str] = None  # département, région
    population: Optional[int] = None
    
    @property
    def is_valid(self) -> bool:
        """Vérifie si le géocodage est valide."""
        return self.score >= 0.7 and self.latitude is not None
    
    @property
    def department(self) -> Optional[str]:
        """Extrait le département du contexte."""
        if self.context:
            parts = self.context.split(", ")
            if len(parts) >= 1:
                return parts[0]
        return None
    
    @property
    def region(self) -> Optional[str]:
        """Extrait la région du contexte."""
        if self.context:
            parts = self.context.split(", ")
            if len(parts) >= 2:
                return parts[1]
        return None


class QualityMetrics(BaseModel):
    """Métriques de qualité du dataset météo."""
    total_records: int
    valid_records: int
    completeness_score: float
    duplicates_count: int
    duplicates_pct: float
    geocoding_success_rate: float
    avg_geocoding_score: float
    valid_coordinates_pct: float
    cities_count: int
    forecast_days_avg: float
    null_counts: dict
    quality_grade: str  # A, B, C, D, F
    
    @property
    def is_acceptable(self) -> bool:
        return self.quality_grade in ['A', 'B', 'C']