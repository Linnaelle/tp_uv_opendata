"""Tests pour les fetchers météo."""
import pytest
from pipeline.fetchers.openmeteo import OpenMeteoFetcher, WeatherDataParser
from pipeline.fetchers.adresse import AdresseFetcher


class TestAdresseFetcher:
    """Tests pour le géocodage de villes."""
    
    def test_geocode_paris(self):
        """Test géocodage de Paris."""
        fetcher = AdresseFetcher()
        result = fetcher.geocode_city("Paris")
        
        assert result.original_city == "Paris"
        assert result.is_valid
        assert result.latitude is not None
        assert result.longitude is not None
        assert result.score > 0.9
        assert "Paris" in result.label
    
    def test_geocode_marseille(self):
        """Test géocodage de Marseille."""
        fetcher = AdresseFetcher()
        result = fetcher.geocode_city("Marseille")
        
        assert result.is_valid
        assert 43.0 < result.latitude < 44.0  # Latitude approximative
        assert 5.0 < result.longitude < 6.0   # Longitude approximative
    
    def test_geocode_invalid_city(self):
        """Test géocodage d'une ville invalide."""
        fetcher = AdresseFetcher()
        result = fetcher.geocode_city("VilleInexistante123")
        
        assert not result.is_valid
        assert result.score < 0.7
    
    def test_geocode_empty(self):
        """Test géocodage d'une chaîne vide."""
        fetcher = AdresseFetcher()
        result = fetcher.geocode_city("")
        
        assert result.score == 0
        assert result.latitude is None


class TestOpenMeteoFetcher:
    """Tests pour l'API météo."""
    
    def test_fetch_forecast_paris(self):
        """Test récupération météo pour Paris."""
        fetcher = OpenMeteoFetcher()
        # Coordonnées de Paris
        result = fetcher.fetch_forecast(48.8566, 2.3522, days=3)
        
        assert result is not None
        assert 'daily' in result
        assert 'time' in result['daily']
        assert len(result['daily']['time']) == 3
    
    def test_fetch_forecast_has_temperature(self):
        """Test présence des températures."""
        fetcher = OpenMeteoFetcher()
        result = fetcher.fetch_forecast(48.8566, 2.3522, days=1)
        
        assert 'temperature_2m_max' in result['daily']
        assert 'temperature_2m_min' in result['daily']
        assert len(result['daily']['temperature_2m_max']) > 0


class TestWeatherDataParser:
    """Tests pour le parser météo."""
    
    def test_parse_valid_data(self):
        """Test parsing de données valides."""
        raw_data = {
            'daily': {
                'time': ['2024-01-01', '2024-01-02'],
                'temperature_2m_max': [15.5, 16.2],
                'temperature_2m_min': [8.3, 9.1],
                'precipitation_sum': [0, 2.5]
            }
        }
        
        parser = WeatherDataParser()
        result = parser.parse_forecast(raw_data, "TestCity")
        
        assert len(result) == 2
        assert result[0]['city'] == "TestCity"
        assert result[0]['forecast_date'] == '2024-01-01'
        assert result[0]['temperature_max'] == 15.5
    
    def test_parse_empty_data(self):
        """Test parsing de données vides."""
        parser = WeatherDataParser()
        result = parser.parse_forecast({}, "TestCity")
        
        assert result == []