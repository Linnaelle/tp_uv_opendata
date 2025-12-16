"""Fetcher pour l'API Adresse (géocodage de villes)."""
from typing import Generator
from tqdm import tqdm
from .base import BaseFetcher
from ..config import ADRESSE_CONFIG
from ..models import GeocodingResult
from datetime import datetime

class AdresseFetcher(BaseFetcher):
    """Fetcher pour l'API Adresse."""
    
    def __init__(self):
        super().__init__(ADRESSE_CONFIG)
    
    def geocode_city(self, city_name: str) -> GeocodingResult:
        """
        Géocode une ville française.
        
        Args:
            city_name: Nom de la ville
        
        Returns:
            Résultat du géocodage
        """
        if not city_name or city_name.strip() == "":
            return GeocodingResult(original_city=city_name or "", score=0)
        
        try:
            # Recherche de type "municipality" pour les villes
            params = {
                "q": city_name,
                "type": "municipality",
                "limit": 1
            }
            
            data = self._make_request("/search/", params=params)
            
            if not data.get("features"):
                return GeocodingResult(original_city=city_name, score=0)
            
            feature = data["features"][0]
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [None, None])
            
            self.stats["items_fetched"] += 1
            
            return GeocodingResult(
                original_city=city_name,
                label=props.get("label"),
                latitude=coords[1] if len(coords) > 1 else None,
                longitude=coords[0] if len(coords) > 0 else None,
                score=props.get("score", 0),
                postal_code=props.get("postcode"),
                city_code=props.get("citycode"),
                city=props.get("city") or props.get("name"),
                context=props.get("context"),
                population=props.get("population"),
            )
        
        except Exception as e:
            self.stats["requests_failed"] += 1
            print(f"⚠️ Erreur géocodage '{city_name}': {e}")
            return GeocodingResult(original_city=city_name, score=0)
    
    def fetch_batch(self, cities: list[str]) -> list[GeocodingResult]:
        """Géocode un lot de villes."""
        results = []
        for city in cities:
            result = self.geocode_city(city)
            results.append(result)
            self._rate_limit()
        return results
    
    def fetch_all(
        self, 
        cities: list[str], 
        verbose: bool = True
    ) -> Generator[GeocodingResult, None, None]:
        """Géocode toutes les villes."""
        self.stats["start_time"] = datetime.now()
        
        iterator = tqdm(cities, desc="Géocodage villes", disable=not verbose)
        
        for city in iterator:
            result = self.geocode_city(city)
            yield result
            self._rate_limit()
        
        self.stats["end_time"] = datetime.now()
        
        if verbose:
            success = sum(1 for _ in range(self.stats["items_fetched"]))
            print(f"✅ {self.stats['items_fetched']} villes géocodées")