"""Module d'enrichissement des données météo."""
import pandas as pd
from typing import Dict
from tqdm import tqdm

from .fetchers.adresse import AdresseFetcher
from .fetchers.openmeteo import OpenMeteoFetcher, WeatherDataParser
from .models import GeocodingResult


class WeatherEnricher:
    """Enrichit les données météo avec géolocalisation."""
    
    def __init__(self):
        self.geocoder = AdresseFetcher()
        self.weather_fetcher = OpenMeteoFetcher()
        self.parser = WeatherDataParser()
        self.enrichment_stats = {
            "total_cities_processed": 0,
            "successfully_geocoded": 0,
            "failed_geocoding": 0,
            "weather_fetched": 0,
            "weather_failed": 0,
        }
    
    def build_city_geocoding_cache(self, cities: list[str]) -> Dict[str, GeocodingResult]:
        """
        Construit un cache de géocodage pour les villes.
        
        Args:
            cities: Liste des noms de villes
        
        Returns:
            Dictionnaire ville -> résultat géocodage
        """
        cache = {}
        
        print(f"🌍 Géocodage de {len(cities)} villes...")
        
        for result in self.geocoder.fetch_all(cities):
            cache[result.original_city] = result
            if result.is_valid:
                self.enrichment_stats["successfully_geocoded"] += 1
            else:
                self.enrichment_stats["failed_geocoding"] += 1
        
        success_rate = (self.enrichment_stats["successfully_geocoded"] / 
                       len(cities) * 100 if cities else 0)
        print(f"✅ Taux de succès géocodage: {success_rate:.1f}%")
        
        return cache
    
    def fetch_weather_for_cities(
        self, 
        geocoding_cache: Dict[str, GeocodingResult],
        forecast_days: int = 7
    ) -> list[dict]:
        """
        Récupère les prévisions météo pour toutes les villes géocodées.
        
        Args:
            geocoding_cache: Cache de géocodage
            forecast_days: Nombre de jours de prévisions
        
        Returns:
            Liste des prévisions enrichies
        """
        all_forecasts = []
        
        # Extraire les coordonnées valides
        valid_cities = [
            (city, geo) 
            for city, geo in geocoding_cache.items() 
            if geo.is_valid
        ]
        
        print(f"🌤️ Récupération météo pour {len(valid_cities)} villes...")
        
        for city_name, geo in tqdm(valid_cities, desc="Météo"):
            self.enrichment_stats["total_cities_processed"] += 1
            
            try:
                # Récupérer météo
                raw_weather = self.weather_fetcher.fetch_forecast(
                    geo.latitude, 
                    geo.longitude,
                    days=forecast_days
                )
                
                if raw_weather:
                    # Parser les données
                    daily_forecasts = self.parser.parse_forecast(raw_weather, city_name)
                    
                    # Enrichir avec les données géo
                    for forecast in daily_forecasts:
                        forecast.update({
                            'city_label': geo.label,
                            'latitude': geo.latitude,
                            'longitude': geo.longitude,
                            'postal_code': geo.postal_code,
                            'city_code': geo.city_code,
                            'department': geo.department,
                            'region': geo.region,
                            'population': geo.population,
                            'geocoding_score': geo.score,
                        })
                    
                    all_forecasts.extend(daily_forecasts)
                    self.enrichment_stats["weather_fetched"] += 1
                else:
                    self.enrichment_stats["weather_failed"] += 1
            
            except Exception as e:
                print(f"⚠️ Erreur météo pour {city_name}: {e}")
                self.enrichment_stats["weather_failed"] += 1
        
        print(f"✅ {len(all_forecasts)} prévisions quotidiennes récupérées")
        return all_forecasts
    
    def get_stats(self) -> dict:
        """Retourne les statistiques d'enrichissement."""
        stats = self.enrichment_stats.copy()
        stats["geocoder_stats"] = self.geocoder.get_stats()
        stats["weather_stats"] = self.weather_fetcher.get_stats()
        
        if stats["total_cities_processed"] > 0:
            stats["success_rate"] = (stats["weather_fetched"] / 
                                    stats["total_cities_processed"] * 100)
        else:
            stats["success_rate"] = 0
        
        return stats