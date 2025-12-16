"""Module de transformation et nettoyage météo."""
import pandas as pd
import numpy as np
from typing import Callable


class WeatherTransformer:
    """Transforme et nettoie les données météo."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.transformations_applied = []
    
    def remove_duplicates(self) -> 'WeatherTransformer':
        """Supprime les doublons (même ville + même date)."""
        initial = len(self.df)
        
        self.df = self.df.drop_duplicates(
            subset=['city', 'forecast_date'], 
            keep='first'
        )
        removed = initial - len(self.df)
        
        self.transformations_applied.append(f"Doublons supprimés: {removed}")
        return self
    
    def handle_missing_values(self) -> 'WeatherTransformer':
        """Gère les valeurs manquantes."""
        
        # Colonnes météo numériques - remplacer par 0 (pas de précipitation = 0)
        precip_cols = ['precipitation_sum', 'rain_sum', 'snowfall_sum']
        for col in precip_cols:
            if col in self.df.columns:
                null_count = self.df[col].isnull().sum()
                if null_count > 0:
                    self.df[col] = self.df[col].fillna(0)
                    self.transformations_applied.append(f"{col}: {null_count} nulls → 0")
        
        # Températures - interpolation ou suppression
        temp_cols = ['temperature_max', 'temperature_min']
        for col in temp_cols:
            if col in self.df.columns:
                null_count = self.df[col].isnull().sum()
                if null_count > 0:
                    # Interpolation linéaire par ville
                    self.df[col] = self.df.groupby('city')[col].transform(
                        lambda x: x.interpolate(method='linear', limit_direction='both')
                    )
                    self.transformations_applied.append(f"{col}: {null_count} nulls interpolés")
        
        # Vent - remplacer par médiane
        wind_cols = ['wind_speed_max', 'wind_gusts_max']
        for col in wind_cols:
            if col in self.df.columns:
                null_count = self.df[col].isnull().sum()
                if null_count > 0:
                    median_val = self.df[col].median()
                    self.df[col] = self.df[col].fillna(median_val)
                    self.transformations_applied.append(f"{col}: {null_count} nulls → {median_val:.1f}")
        
        return self
    
    def add_derived_columns(self) -> 'WeatherTransformer':
        """Ajoute des colonnes dérivées."""
        
        # Température moyenne
        if 'temperature_max' in self.df.columns and 'temperature_min' in self.df.columns:
            self.df['temperature_avg'] = (
                self.df['temperature_max'] + self.df['temperature_min']
            ) / 2
            self.transformations_applied.append("Ajout: temperature_avg")
        
        # Amplitude thermique
        if 'temperature_max' in self.df.columns and 'temperature_min' in self.df.columns:
            self.df['temperature_range'] = (
                self.df['temperature_max'] - self.df['temperature_min']
            )
            self.transformations_applied.append("Ajout: temperature_range")
        
        # Catégorie de température
        if 'temperature_avg' in self.df.columns:
            self.df['temp_category'] = pd.cut(
                self.df['temperature_avg'],
                bins=[-float('inf'), 0, 10, 20, 30, float('inf')],
                labels=['très_froid', 'froid', 'doux', 'chaud', 'très_chaud']
            )
            self.transformations_applied.append("Ajout: temp_category")
        
        # Intensité des précipitations
        if 'precipitation_sum' in self.df.columns:
            self.df['precip_intensity'] = pd.cut(
                self.df['precipitation_sum'],
                bins=[0, 1, 5, 10, 50, float('inf')],
                labels=['nulle', 'faible', 'modérée', 'forte', 'très_forte']
            )
            self.transformations_applied.append("Ajout: precip_intensity")
        
        # Conditions hivernales
        if 'snowfall_sum' in self.df.columns:
            self.df['has_snow'] = self.df['snowfall_sum'] > 0
            self.transformations_applied.append("Ajout: has_snow")
        
        # Conditions venteuses
        if 'wind_speed_max' in self.df.columns:
            self.df['is_windy'] = self.df['wind_speed_max'] > 40  # > 40 km/h
            self.transformations_applied.append("Ajout: is_windy")
        
        # Extraction date features
        if 'forecast_date' in self.df.columns:
            self.df['forecast_date'] = pd.to_datetime(self.df['forecast_date'])
            self.df['day_of_week'] = self.df['forecast_date'].dt.day_name()
            self.df['month'] = self.df['forecast_date'].dt.month
            self.df['is_weekend'] = self.df['forecast_date'].dt.dayofweek >= 5
            self.transformations_applied.append("Ajout: features temporelles")
        
        return self
    
    def normalize_text_columns(self) -> 'WeatherTransformer':
        """Normalise les colonnes texte."""
        text_cols = ['city', 'city_label', 'department', 'region']
        
        for col in text_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].astype(str).str.strip()
        
        self.transformations_applied.append("Normalisation texte")
        return self
    
    def filter_outliers(self) -> 'WeatherTransformer':
        """Filtre les valeurs météo aberrantes."""
        initial = len(self.df)
        
        # Températures réalistes pour la France
        if 'temperature_max' in self.df.columns:
            self.df = self.df[
                (self.df['temperature_max'] >= -30) & 
                (self.df['temperature_max'] <= 50)
            ]
        
        if 'temperature_min' in self.df.columns:
            self.df = self.df[
                (self.df['temperature_min'] >= -40) & 
                (self.df['temperature_min'] <= 45)
            ]
        
        # Précipitations réalistes
        if 'precipitation_sum' in self.df.columns:
            self.df = self.df[self.df['precipitation_sum'] <= 300]  # max 300mm/jour
        
        # Vent réaliste
        if 'wind_speed_max' in self.df.columns:
            self.df = self.df[self.df['wind_speed_max'] <= 200]  # max 200 km/h
        
        removed = initial - len(self.df)
        if removed > 0:
            self.transformations_applied.append(f"Outliers filtrés: {removed}")
        
        return self
    
    def apply_custom(self, func: Callable[[pd.DataFrame], pd.DataFrame], name: str) -> 'WeatherTransformer':
        """Applique une transformation personnalisée."""
        self.df = func(self.df)
        self.transformations_applied.append(f"Custom: {name}")
        return self
    
    def get_result(self) -> pd.DataFrame:
        """Retourne le DataFrame transformé."""
        return self.df
    
    def get_summary(self) -> str:
        """Retourne un résumé des transformations."""
        return "\n".join([f"• {t}" for t in self.transformations_applied])