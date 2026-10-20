import json
from pathlib import Path
import pandas as pd

RAW_DIR = Path("data/raw")
CLEAN_DIR = Path ("data/filtered")


# Julian Date of the Unix epoch é um formato de data utilizado pelos astronomos.
# Cria um ponto fixo no tempo que não é identificado por meses, anos bissextos etc.

JD_UNIX_EPOCH = 2440587.5


# 2 Tabelas, associaçao, de 1 - *, porque podemos ter só um asteroide, mas pode ter varias aproximações com diferent variedade de orbitas.

# Colunas de asteroides.
ASTEROID_COLS = {
    # identity
    "id" : "id",
    "name" : "name",
    "name_limited" : "short_name",
    "designation" : "designation",
    "nasa_jpl_url" : "jpl_url",

    # Flags and size
    "absolute_magnitude_h" : "h_mag",
    "estimated_diameter.kilometers.estimated_diameter_min" : "d_min_km",
    "estimated_diameter.kilometers.estimated_diameter_max" : "d_max_km",
    "is_potentially_hazardous_asteroid" : "is_pha",
    "is_sentry_object" : "is_sentry",

    # The six keplerian elements and variables for timescaling
    "orbital_data.semi_major_axis" : "a_au", # Distancia media da orbita em relação ao sol medido em Unidades Astronomicas.
    "orbital_data.eccentricity" : "e", # Excentricidade da orbita, quanto mais perto de 0 mais redondo é, inverso tende para eliptica.
    "orbital_data.inclination" : "i_deg", # Inclinação relativa a orbita da Terra
    "orbital_data.ascending_node_longitude" : "node_deg", # Onde o asteroid cruza com a orbita da Terra num movinmento de baixo para cima.
    "orbital_data.perihelion_argument" : "peri_deg", # Ponto mais perto do sol.
    "orbital_data.mean_anomaly" : "M_deg", # Onde os asteroide esta na sua orbita.
    "orbital_data.mean_motion" : "n_deg_day", # Quantos graus avança por dia.
    "orbital_data.epoch_osculation" : "epoch_jd", # data.

    # Derived orbit information. (Usada nos filtros)
    "orbital_data.orbital_period" : "period_days", # Duração das orbita em dias.
    "orbital_data.perihelion_distance": "perihelion_au",
    "orbital_data.aphelion_distance": "aphelion_au",
    "orbital_data.minimum_orbit_intersection": "moid_au",
    "orbital_data.jupiter_tisserand_invariant": "t_jup",
    "orbital_data.orbit_class.orbit_class_type": "orbit_class",

    # orbit quality
    "orbital_data.orbit_uncertainty": "uncertainty",
    "orbital_data.observations_used": "n_obs",
    "orbital_data.data_arc_in_days": "arc_days",
    "orbital_data.first_observation_date": "first_obs",
    "orbital_data.last_observation_date": "last_obs",

}

# Colunas das aproximações.
APPROACH_COLS = {
    "id": "id",
    "epoch_date_close_approach": "epoch_ms",
    "orbiting_body": "body",
    "relative_velocity.kilometers_per_second": "velocity_kms",
    "miss_distance.astronomical": "miss_au",
    "miss_distance.lunar": "miss_lunar",
    "miss_distance.kilometers": "miss_km",
}


def load_raw():
    """Carrega cada página de cada asteroide e retorna uma lista em formato dicionario."""
    neos = []
    for path in sorted(RAW_DIR.glob("page_*.json")):
        data = json.loads(path.read_text())
        neos.extend(data["near_earth_objects"])
    print(f"loaded {len(neos)} asteroid records from {RAW_DIR}")
    return neos


def build_asteroids(neos):
    df = pd.json_normalize(neos)
 
    # reindex keeps only our columns; any column missing in the data becomes NaN
    df = df.reindex(columns=list(ASTEROID_COLS)).rename(columns=ASTEROID_COLS)
 
    # strings -> numbers ("errors='coerce'" turns anything unparseable into NaN)
    num_cols = [
        "h_mag", "d_min_km", "d_max_km",
        "a_au", "e", "i_deg", "node_deg", "peri_deg", "M_deg", "n_deg_day", "epoch_jd",
        "period_days", "perihelion_au", "aphelion_au", "moid_au", "t_jup",
        "n_obs", "arc_days",
    ]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
    df["uncertainty"] = pd.to_numeric(df["uncertainty"], errors="coerce").astype("Int64")
 
    # dates
    df["epoch"] = pd.to_datetime(df["epoch_jd"] - JD_UNIX_EPOCH, unit="D")
    df["first_obs"] = pd.to_datetime(df["first_obs"], errors="coerce")
    df["last_obs"] = pd.to_datetime(df["last_obs"], errors="coerce")
 
    # flags
    df["is_pha"] = df["is_pha"].astype(bool)
    df["is_sentry"] = df["is_sentry"].fillna(False).astype(bool)
 
    # derived columns
    df["diameter_km"] = (df["d_min_km"] + df["d_max_km"]) / 2
    df["is_numbered"] = df["id"].str.startswith("2")
 
    # pages can shift while fetching -> same asteroid may appear twice
    before = len(df)
    df = df.drop_duplicates(subset="id").reset_index(drop=True)
    print(f"asteroids: removed {before - len(df)} duplicates")
 
    return df
 
 
def build_approaches(neos):
    # an asteroid without the key would crash json_normalize, so make sure it exists
    for neo in neos:
        neo.setdefault("close_approach_data", [])
 
    df = pd.json_normalize(neos, record_path="close_approach_data", meta=["id"])
    df = df.reindex(columns=list(APPROACH_COLS)).rename(columns=APPROACH_COLS)
 
    num_cols = ["velocity_kms", "miss_au", "miss_lunar", "miss_km"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")
 
    # Unix milliseconds -> datetime (negative values = before 1970, that's fine)
    df["date"] = pd.to_datetime(df["epoch_ms"], unit="ms")
    df = df.drop(columns="epoch_ms")
 
    before = len(df)
    df = df.drop_duplicates(subset=["id", "date", "body"]).reset_index(drop=True)
    print(f"approaches: removed {before - len(df)} duplicates")
 
    return df
 
 
def report(asteroids, approaches):
    """Quick sanity checks printed after cleaning."""
    print()
    print(f"asteroids:  {asteroids.shape[0]:>9,} rows x {asteroids.shape[1]} columns")
    print(f"approaches: {approaches.shape[0]:>9,} rows x {approaches.shape[1]} columns")
 
    orbit_cols = ["a_au", "e", "i_deg", "node_deg", "peri_deg", "M_deg", "n_deg_day", "epoch_jd"]
    missing = asteroids[orbit_cols].isna().any(axis=1).sum()
    print(f"asteroids missing orbital elements: {missing}")
 
    print(f"hazardous (PHA): {asteroids['is_pha'].sum():,}")
    print("orbit classes:")
    print(asteroids["orbit_class"].value_counts().to_string())
 
 
def main():
    neos = load_raw()
    asteroids = build_asteroids(neos)
    approaches = build_approaches(neos)
 
    report(asteroids, approaches)
 
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    asteroids.to_parquet(CLEAN_DIR / "asteroids.parquet", index=False)
    approaches.to_parquet(CLEAN_DIR / "approaches.parquet", index=False)
    print(f"\nsaved to {CLEAN_DIR}/")
 
 
if __name__ == "__main__":
    main()