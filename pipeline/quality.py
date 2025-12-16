"""Module de scoring et rapport de qualité météo."""
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import QUALITY_THRESHOLDS, REPORTS_DIR
from .models import QualityMetrics

# Import conditionnel pour l'IA
try:
    from litellm import completion
    from dotenv import load_dotenv
    load_dotenv()
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False


class WeatherQualityAnalyzer:
    """Analyse et score la qualité des données météo."""
    
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.metrics = None
    
    def calculate_completeness(self) -> float:
        """Calcule le score de complétude."""
        total_cells = self.df.size
        non_null_cells = self.df.notna().sum().sum()
        return non_null_cells / total_cells if total_cells > 0 else 0
    
    def count_duplicates(self) -> tuple[int, float]:
        """Compte les doublons (ville + date)."""
        duplicates = self.df.duplicated(subset=['city', 'forecast_date']).sum()
        pct = duplicates / len(self.df) * 100 if len(self.df) > 0 else 0
        return duplicates, pct
    
    def calculate_geocoding_stats(self) -> tuple[float, float]:
        """Calcule les stats de géocodage."""
        if 'geocoding_score' not in self.df.columns:
            return 0, 0
        
        valid_geo = self.df['geocoding_score'].notna() & (self.df['geocoding_score'] >= 0.7)
        success_rate = valid_geo.sum() / len(self.df) * 100 if len(self.df) > 0 else 0
        avg_score = self.df.loc[valid_geo, 'geocoding_score'].mean() if valid_geo.any() else 0
        
        return success_rate, avg_score
    
    def calculate_valid_coordinates(self) -> float:
        """Calcule le % de coordonnées valides."""
        if 'latitude' not in self.df.columns or 'longitude' not in self.df.columns:
            return 0
        
        valid = (
            self.df['latitude'].notna() & 
            self.df['longitude'].notna() &
            (self.df['latitude'].between(-90, 90)) &
            (self.df['longitude'].between(-180, 180))
        )
        
        return valid.sum() / len(self.df) * 100 if len(self.df) > 0 else 0
    
    def calculate_weather_stats(self) -> dict:
        """Statistiques spécifiques météo."""
        stats = {}
        
        if 'city' in self.df.columns:
            stats['cities_count'] = self.df['city'].nunique()
        
        if 'forecast_date' in self.df.columns:
            # Nombre moyen de jours de prévision par ville
            days_per_city = self.df.groupby('city')['forecast_date'].nunique().mean()
            stats['forecast_days_avg'] = days_per_city
        
        return stats
    
    def calculate_null_counts(self) -> dict:
        """Compte les valeurs nulles par colonne."""
        return self.df.isnull().sum().to_dict()
    
    def determine_grade(
        self, 
        completeness: float, 
        duplicates_pct: float, 
        geo_rate: float,
        coord_pct: float
    ) -> str:
        """Détermine la note de qualité globale."""
        score = 0
        
        # Complétude (30 points)
        score += min(completeness * 30, 30)
        
        # Doublons (20 points)
        if duplicates_pct <= 1:
            score += 20
        elif duplicates_pct <= 2:
            score += 15
        elif duplicates_pct <= 5:
            score += 10
        
        # Géocodage (25 points)
        score += min(geo_rate / 100 * 25, 25)
        
        # Coordonnées valides (25 points)
        score += min(coord_pct / 100 * 25, 25)
        
        # Note finale
        if score >= 90:
            return 'A'
        elif score >= 75:
            return 'B'
        elif score >= 60:
            return 'C'
        elif score >= 40:
            return 'D'
        else:
            return 'F'
    
    def analyze(self) -> QualityMetrics:
        """Effectue l'analyse complète de qualité."""
        completeness = self.calculate_completeness()
        duplicates, duplicates_pct = self.count_duplicates()
        geo_rate, geo_avg = self.calculate_geocoding_stats()
        coord_pct = self.calculate_valid_coordinates()
        weather_stats = self.calculate_weather_stats()
        null_counts = self.calculate_null_counts()
        
        valid_records = len(self.df) - duplicates
        
        grade = self.determine_grade(completeness, duplicates_pct, geo_rate, coord_pct)
        
        self.metrics = QualityMetrics(
            total_records=len(self.df),
            valid_records=valid_records,
            completeness_score=round(completeness, 3),
            duplicates_count=duplicates,
            duplicates_pct=round(duplicates_pct, 2),
            geocoding_success_rate=round(geo_rate, 2),
            avg_geocoding_score=round(geo_avg, 3),
            valid_coordinates_pct=round(coord_pct, 2),
            cities_count=weather_stats.get('cities_count', 0),
            forecast_days_avg=round(weather_stats.get('forecast_days_avg', 0), 1),
            null_counts=null_counts,
            quality_grade=grade,
        )
        
        return self.metrics
    
    def generate_ai_recommendations(self) -> str:
        """Génère des recommandations via l'IA (optionnel)."""
        if not AI_AVAILABLE:
            return "⚠️ IA non disponible. Installez litellm et configurez .env"
        
        if not self.metrics:
            self.analyze()
        
        context = f"""
        Analyse de qualité d'un dataset météo :
        - Total: {self.metrics.total_records} prévisions
        - Villes: {self.metrics.cities_count}
        - Jours moyens: {self.metrics.forecast_days_avg}
        - Complétude: {self.metrics.completeness_score * 100:.1f}%
        - Doublons: {self.metrics.duplicates_pct:.1f}%
        - Géocodage: {self.metrics.geocoding_success_rate:.1f}%
        - Coordonnées valides: {self.metrics.valid_coordinates_pct:.1f}%
        - Note: {self.metrics.quality_grade}
        
        Principales colonnes avec valeurs nulles:
        {dict(sorted(self.metrics.null_counts.items(), key=lambda x: x[1], reverse=True)[:5])}
        """
        
        try:
            response = completion(
                model="ollama/mistral",
                messages=[
                    {
                        "role": "system",
                        "content": "Tu es un expert en qualité de données météo. Donne 5 recommandations concrètes et actionnables."
                    },
                    {
                        "role": "user", 
                        "content": f"{context}\n\nQuelles sont tes recommandations pour améliorer ce dataset météo ?"
                    }
                ],
                api_base="http://localhost:11434"
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"❌ Erreur IA: {e}\n\nRecommandations manuelles:\n• Vérifier les valeurs nulles\n• Valider les coordonnées GPS\n• Nettoyer les doublons"
    
    def generate_report(self, output_name: str = "weather_quality_report") -> Path:
        """Génère un rapport de qualité complet en Markdown."""
        if not self.metrics:
            self.analyze()
        
        recommendations = self.generate_ai_recommendations()
        
        report = f"""# Rapport de Qualité - Données Météo

**Généré le** : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🌤️ Vue d'ensemble

Ce rapport analyse la qualité d'un dataset de prévisions météorologiques enrichi avec des données de géolocalisation pour les villes françaises.

## 📊 Métriques Globales

| Métrique | Valeur | Seuil | Statut |
|----------|--------|-------|--------|
| **Note globale** | **{self.metrics.quality_grade}** | A-B-C = Acceptable | {"✅" if self.metrics.is_acceptable else "⚠️"} |
| Total prévisions | {self.metrics.total_records:,} | - | - |
| Prévisions valides | {self.metrics.valid_records:,} | - | - |
| Nombre de villes | {self.metrics.cities_count} | - | - |
| Jours moyens/ville | {self.metrics.forecast_days_avg:.1f} | 7 | {"✅" if self.metrics.forecast_days_avg >= 6 else "⚠️"} |

## 📈 Scores de Qualité

| Dimension | Score | Seuil | Statut |
|-----------|-------|-------|--------|
| **Complétude** | {self.metrics.completeness_score * 100:.1f}% | ≥ 80% | {"✅" if self.metrics.completeness_score >= 0.8 else "⚠️"} |
| **Doublons** | {self.metrics.duplicates_pct:.2f}% | ≤ 2% | {"✅" if self.metrics.duplicates_pct <= 2 else "⚠️"} |
| **Géocodage** | {self.metrics.geocoding_success_rate:.1f}% | ≥ 70% | {"✅" if self.metrics.geocoding_success_rate >= 70 else "⚠️"} |
| **Score géo moyen** | {self.metrics.avg_geocoding_score:.3f} | ≥ 0.7 | {"✅" if self.metrics.avg_geocoding_score >= 0.7 else "⚠️"} |
| **Coordonnées valides** | {self.metrics.valid_coordinates_pct:.1f}% | ≥ 95% | {"✅" if self.metrics.valid_coordinates_pct >= 95 else "⚠️"} |

## 🔍 Analyse Détaillée

### Valeurs Manquantes

| Colonne | Valeurs nulles | % du total |
|---------|----------------|------------|
"""
        
        # Top 10 colonnes avec le plus de nulls
        sorted_nulls = sorted(self.metrics.null_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for col, count in sorted_nulls:
            pct = count / self.metrics.total_records * 100 if self.metrics.total_records > 0 else 0
            report += f"| {col} | {count:,} | {pct:.1f}% |\n"
        
        report += f"""

### Problèmes Identifiés

"""
        
        issues = []
        if self.metrics.duplicates_pct > 2:
            issues.append(f"⚠️ **Doublons élevés** : {self.metrics.duplicates_count} doublons ({self.metrics.duplicates_pct:.1f}%)")
        
        if self.metrics.completeness_score < 0.8:
            issues.append(f"⚠️ **Complétude faible** : {self.metrics.completeness_score * 100:.1f}% des données remplies")
        
        if self.metrics.geocoding_success_rate < 70:
            issues.append(f"⚠️ **Géocodage insuffisant** : Seulement {self.metrics.geocoding_success_rate:.1f}% de réussite")
        
        if self.metrics.valid_coordinates_pct < 95:
            issues.append(f"⚠️ **Coordonnées invalides** : {100 - self.metrics.valid_coordinates_pct:.1f}% de coordonnées manquantes/incorrectes")
        
        if not issues:
            report += "✅ Aucun problème majeur détecté\n"
        else:
            for issue in issues:
                report += f"{issue}\n"
        
        report += f"""

## 🤖 Recommandations IA

{recommendations}

## ✅ Conclusion

"""
        
        if self.metrics.is_acceptable:
            report += f"""✅ **Dataset acceptable** pour l'analyse météorologique.

Le dataset présente une qualité {self.metrics.quality_grade} avec :
- Une bonne couverture géographique ({self.metrics.cities_count} villes)
- Des prévisions sur {self.metrics.forecast_days_avg:.0f} jours en moyenne
- Un taux de géocodage satisfaisant ({self.metrics.geocoding_success_rate:.1f}%)

Les données peuvent être utilisées pour des analyses, visualisations et dashboards météo.
"""
        else:
            report += f"""⚠️ **Dataset nécessite des corrections** avant utilisation.

Le dataset présente une qualité {self.metrics.quality_grade} avec plusieurs problèmes :
{chr(10).join(f"• {issue}" for issue in issues)}

Des actions de nettoyage et d'enrichissement sont recommandées avant toute exploitation.
"""
        
        report += """

---

## 📚 Méthodologie

### Sources de données
- **API Météo** : Open-Meteo (https://open-meteo.com)
- **API Géo** : API Adresse - Base Adresse Nationale (https://adresse.data.gouv.fr)

### Critères de qualité
- **Complétude** : Pourcentage de valeurs non-nulles
- **Doublons** : Ville + date identiques
- **Géocodage** : Score de confiance ≥ 0.7
- **Coordonnées** : Latitude/Longitude dans les plages valides

### Système de notation
- **A (90-100)** : Excellent
- **B (75-89)** : Très bon
- **C (60-74)** : Acceptable
- **D (40-59)** : Passable
- **F (0-39)** : Insuffisant

---

*Rapport généré automatiquement par le pipeline Open Data Météo*
"""
        
        # Sauvegarder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = REPORTS_DIR / f"{output_name}_{timestamp}.md"
        filepath.write_text(report, encoding='utf-8')
        
        print(f"📄 Rapport sauvegardé : {filepath}")
        return filepath