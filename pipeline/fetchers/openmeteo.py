"""Fetcher pour l'API OpenMeteo."""
from typing import Generator
from datetime import datetime, timedelta
from tqdm import tqdm

from .base import BaseFetcher
from ..config import OPENMETEO_CONFIG, FORECAST_DAYS


class OpenMeteoFetcher(BaseFetcher):
    """Fetcher pour OpenMeteo."""
    
    def __init__(self):
        super().__init__(OPENMETEO_CONFIG)
    
    def fetch_forecast(
        self, 
        latitude: float, 
        longitude: float,
        days: int = FORECAST_DAYS
    ) -> dict:
        """
        Récupère les prévisions météo pour une coordonnée.
        
        Args:
            latitude: Latitude
            longitude: Longitude
            days: Nombre de jours de prévisions
        
        Returns:
            Données météo brutes
        """
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_sum",
                "rain_sum",
                "snowfall_sum",
                "wind_speed_10m_max",
                "wind_gusts_10m_max"
            ],
            "timezone": "Europe/Paris",
            "forecast_days": days
        }
        
        try:
            data = self._make_request("/forecast", params)
            self.stats["items_fetched"] += 1
            return data
        except Exception as e:
            self.stats["requests_failed"] += 1
            print(f"⚠️ Erreur météo pour ({latitude}, {longitude}): {e}")
            return {}
    
    def fetch_batch(
        self, 
        coordinates: list[tuple[float, float]],
        days: int = FORECAST_DAYS
    ) -> list[dict]:
        """
        Récupère les prévisions pour plusieurs coordonnées.
        
        Args:
            coordinates: Liste de (latitude, longitude)
            days: Nombre de jours de prévisions
        
        Returns:
            Liste des données météo
        """
        forecasts = []
        
        for lat, lon in coordinates:
            forecast = self.fetch_forecast(lat, lon, days)
            if forecast:
                forecast['request_coords'] = (lat, lon)
                forecasts.append(forecast)
            self._rate_limit()
        
        return forecasts
    
    def fetch_all(
        self, 
        coordinates: list[tuple[float, float]],
        days: int = FORECAST_DAYS,
        verbose: bool = True
    ) -> Generator[dict, None, None]:
        """
        Récupère toutes les prévisions météo.
        
        Args:
            coordinates: Liste de (latitude, longitude)
            days: Nombre de jours
            verbose: Afficher la progression
        
        Yields:
            Données météo individuelles
        """
        self.stats["start_time"] = datetime.now()
        
        iterator = tqdm(coordinates, desc="OpenMeteo", disable=not verbose)
        
        for lat, lon in iterator:
            forecast = self.fetch_forecast(lat, lon, days)
            if forecast:
                forecast['request_coords'] = (lat, lon)
                yield forecast
            self._rate_limit()
        
        self.stats["end_time"] = datetime.now()
        
        if verbose:
            duration = (self.stats["end_time"] - self.stats["start_time"]).seconds
            print(f"✅ {self.stats['items_fetched']} prévisions récupérées en {duration}s")


class WeatherDataParser:
    """Parse les données OpenMeteo en format exploitable."""
    
    @staticmethod
    def parse_forecast(raw_data: dict, city_name: str = "Unknown") -> list[dict]:
        """
        Parse les données météo brutes en liste de prévisions journalières.
        
        Args:
            raw_data: Données brutes OpenMeteo
            city_name: Nom de la ville
        
        Returns:
            Liste de dictionnaires (une entrée par jour)
        """
        if not raw_data or 'daily' not in raw_data:
            return []
        
        daily = raw_data['daily']
        dates = daily.get('time', [])
        
        forecasts = []
        for i, date_str in enumerate(dates):
            forecast = {
                'city': city_name,
                'forecast_date': date_str,
                'temperature_max': daily.get('temperature_2m_max', [])[i] if i < len(daily.get('temperature_2m_max', [])) else None,
                'temperature_min': daily.get('temperature_2m_min', [])[i] if i < len(daily.get('temperature_2m_min', [])) else None,
                'precipitation_sum': daily.get('precipitation_sum', [])[i] if i < len(daily.get('precipitation_sum', [])) else None,
                'rain_sum': daily.get('rain_sum', [])[i] if i < len(daily.get('rain_sum', [])) else None,
                'snowfall_sum': daily.get('snowfall_sum', [])[i] if i < len(daily.get('snowfall_sum', [])) else None,
                'wind_speed_max': daily.get('wind_speed_10m_max', [])[i] if i < len(daily.get('wind_speed_10m_max', [])) else None,
                'wind_gusts_max': daily.get('wind_gusts_10m_max', [])[i] if i < len(daily.get('wind_gusts_10m_max', [])) else None,
            }
            forecasts.append(forecast)
        
        return forecasts