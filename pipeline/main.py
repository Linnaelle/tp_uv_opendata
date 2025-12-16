"""Script principal du pipeline météo."""
import argparse
from datetime import datetime
import pandas as pd

from .enricher import WeatherEnricher
from .transformer import WeatherTransformer
from .quality import WeatherQualityAnalyzer
from .storage import save_raw_json, save_parquet
from .config import FRENCH_CITIES, MAX_CITIES, FORECAST_DAYS


def run_weather_pipeline(
    max_cities: int = MAX_CITIES,
    forecast_days: int = FORECAST_DAYS,
    verbose: bool = True
) -> dict:
    """
    Exécute le pipeline météo complet.
    
    Args:
        max_cities: Nombre maximum de villes
        forecast_days: Jours de prévisions
        verbose: Afficher la progression
    
    Returns:
        Statistiques du pipeline
    """
    stats = {"start_time": datetime.now()}
    
    print("=" * 70)
    print("🌤️  PIPELINE MÉTÉO + GÉO")
    print("=" * 70)
    
    # Sélectionner les villes
    cities = FRENCH_CITIES[:max_cities]
    print(f"\n📍 Villes sélectionnées : {len(cities)}")
    
    # === ÉTAPE 1 : Géocodage des villes ===
    print("\n🌍 ÉTAPE 1 : Géocodage des villes")
    enricher = WeatherEnricher()
    geocoding_cache = enricher.build_city_geocoding_cache(cities)
    
    valid_cities = sum(1 for geo in geocoding_cache.values() if geo.is_valid)
    print(f"   ✅ {valid_cities}/{len(cities)} villes géocodées avec succès")
    
    # === ÉTAPE 2 : Récupération météo ===
    print(f"\n🌤️  ÉTAPE 2 : Récupération prévisions ({forecast_days} jours)")
    forecasts = enricher.fetch_weather_for_cities(geocoding_cache, forecast_days)
    
    if not forecasts:
        print("❌ Aucune prévision récupérée. Arrêt.")
        return {"error": "No forecasts fetched"}
    
    # Sauvegarder brut
    save_raw_json(forecasts, "weather_raw")
    stats["enricher"] = enricher.get_stats()
    
    # === ÉTAPE 3 : Transformation ===
    print(f"\n🔧 ÉTAPE 3 : Transformation et nettoyage")
    df = pd.DataFrame(forecasts)
    
    print(f"   📊 Dataset initial : {df.shape[0]} lignes × {df.shape[1]} colonnes")
    
    transformer = WeatherTransformer(df)
    df_clean = (
        transformer
        .remove_duplicates()
        .handle_missing_values()
        .normalize_text_columns()
        .add_derived_columns()
        .filter_outliers()
        .get_result()
    )
    
    print(f"   📊 Dataset nettoyé : {df_clean.shape[0]} lignes × {df_clean.shape[1]} colonnes")
    print(f"\n   Résumé des transformations:")
    for line in transformer.get_summary().split('\n'):
        print(f"     {line}")
    
    stats["transformer"] = {"transformations": transformer.transformations_applied}
    
    # === ÉTAPE 4 : Analyse qualité ===
    print("\n📊 ÉTAPE 4 : Analyse de qualité")
    analyzer = WeatherQualityAnalyzer(df_clean)
    metrics = analyzer.analyze()
    
    print(f"   🎯 Note: {metrics.quality_grade}")
    print(f"   📝 Complétude: {metrics.completeness_score * 100:.1f}%")
    print(f"   🎯 Doublons: {metrics.duplicates_pct:.1f}%")
    print(f"   📍 Géocodage: {metrics.geocoding_success_rate:.1f}%")
    print(f"   🗺️  Coordonnées valides: {metrics.valid_coordinates_pct:.1f}%")
    
    # Générer le rapport
    report_path = analyzer.generate_report("weather_quality")
    stats["quality"] = metrics.dict()
    
    # === ÉTAPE 5 : Stockage final ===
    print("\n💾 ÉTAPE 5 : Stockage final")
    
    # Option 1 : Fichier unique
    output_path = save_parquet(df_clean, "weather_forecast")
    
    # Option 2 : Avec partitionnement (si assez de données)
    # if 'region' in df_clean.columns and len(df_clean) > 100:
    #     output_path = save_parquet(df_clean, "weather_partitioned", partition_cols=['region'])
    
    stats["output_path"] = str(output_path)
    
    # === RÉSUMÉ ===
    stats["end_time"] = datetime.now()
    stats["duration_seconds"] = (stats["end_time"] - stats["start_time"]).seconds
    
    print("\n" + "=" * 70)
    print("✅ PIPELINE TERMINÉ")
    print("=" * 70)
    print(f"   ⏱️  Durée: {stats['duration_seconds']}s")
    print(f"   🏙️  Villes: {metrics.cities_count}")
    print(f"   📅 Prévisions: {len(df_clean)}")
    print(f"   🎯 Qualité: {metrics.quality_grade}")
    print(f"   📄 Rapport: {report_path}")
    print(f"   💾 Données: {output_path}")
    print("=" * 70)
    
    return stats


def main():
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(description="Pipeline Météo + Géo")
    parser.add_argument(
        "--max-cities", "-m", 
        type=int, 
        default=MAX_CITIES, 
        help=f"Nombre max de villes (défaut: {MAX_CITIES})"
    )
    parser.add_argument(
        "--forecast-days", "-d",
        type=int,
        default=FORECAST_DAYS,
        help=f"Jours de prévisions (défaut: {FORECAST_DAYS})"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Mode verbeux"
    )
    
    args = parser.parse_args()
    
    run_weather_pipeline(
        max_cities=args.max_cities,
        forecast_days=args.forecast_days,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()