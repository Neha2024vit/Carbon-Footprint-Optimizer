"""Dataset loader for the user-provided Cloud Carbon Footprint Optimizer workbook."""
from pathlib import Path
from functools import lru_cache
import math
import pandas as pd

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
WORKBOOK = DATA_DIR / "carbon_datasets.xlsx"


def _clean(value):
    if pd.isna(value):
        return None
    if isinstance(value, (int, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    return str(value).strip()


def _sheet(name):
    if not WORKBOOK.exists():
        return []
    try:
        df = pd.read_excel(WORKBOOK, sheet_name=name)
    except (ValueError, OSError):
        return []
    df.columns = [str(c).strip() for c in df.columns]
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def _num(value, default=None):
    try:
        x = float(value)
        return x if math.isfinite(x) else default
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=1)
def load_carbon_regions():
    """Join Cloud_Regions to country factors and provider efficiency in the uploaded workbook."""
    regions = _sheet("Cloud_Regions")
    carbon = {str(r.get("Country") or "").strip().casefold(): r for r in _sheet("Carbon_Intensity")}
    renewable = {str(r.get("Country") or "").strip().casefold(): r for r in _sheet("Renewable_Energy")}
    efficiency = {str(r.get("Provider") or "").strip().casefold(): r for r in _sheet("Cloud_Sustainability")}
    out = []
    for r in regions:
        provider = str(r.get("Provider") or "").strip()
        region = str(r.get("Region") or "").strip()
        country = str(r.get("Country") or "").strip()
        if not provider or not region or not country:
            continue
        c = carbon.get(country.casefold(), {})
        ren = renewable.get(country.casefold(), {})
        eff_key = "google cloud" if provider.casefold() in {"gcp", "google cloud", "google cloud platform"} else provider.casefold()
        eff = efficiency.get(eff_key, {})
        intensity_kg = _num(c.get("kgCO2_per_kWh"))
        renewable_pct = _num(ren.get("Renewable_%"))
        eff_score = _num(eff.get("EfficiencyScore"))
        out.append({
            "Provider": "GCP" if provider.casefold() in {"gcp", "google cloud", "google cloud platform"} else provider,
            "Region_Code": region,
            "Region": region,
            "Region_Name": region,
            "Country": country,
            "Carbon_Intensity_kgCO2e_per_kWh": intensity_kg,
            "Carbon_Intensity_gCO2e_per_kWh": intensity_kg * 1000 if intensity_kg is not None else None,
            "Renewable_%": renewable_pct,
            "Provider_Efficiency_Score": eff_score,
            "Source": "User-provided workbook: Carbon_Intensity, Renewable_Energy, Cloud_Sustainability, Cloud_Regions sheets",
            "Data_Method": "Country-level grid factor applied to listed cloud region; not provider-reported emissions",
            "Comparability_Note": "Country-level factor from the supplied dataset is used as a proxy for each listed region. Results are illustrative and limited by the workbook's geographic granularity.",
            "CFE_%": None,
            "Data_Status": "User-provided dataset",
            "Data_Type": "Country-level proxy",
        })
    return out


@lru_cache(maxsize=1)
def load_cloud_regions():
    return _sheet("Cloud_Regions")


@lru_cache(maxsize=1)
def load_energy_coefficients():
    rows = _sheet("Energy_Coefficients")
    vals = {str(r.get("Parameter") or "").strip(): _num(r.get("Value")) for r in rows}
    return {
        "cpu_kwh_per_hr_at_100_percent": vals.get("CPU_kWh_per_hr_at100%", 0.1),
        "ram_kwh_per_gb_hr": vals.get("RAM_kWh_per_GB_hr", 0.005),
        "storage_kwh_per_100gb_hr": vals.get("Storage_kWh_per_100GB_hr", 0.002),
    }


def refresh_dataset_cache():
    load_carbon_regions.cache_clear()
    load_cloud_regions.cache_clear()
    load_energy_coefficients.cache_clear()


def get_region_carbon_data(provider, region_code):
    p = str(provider or "").strip().casefold()
    code = str(region_code or "").strip().casefold()
    for row in load_carbon_regions():
        if str(row.get("Provider") or "").strip().casefold() == p and str(row.get("Region_Code") or "").strip().casefold() == code:
            return row
    return None


def get_sustainability_score(region):
    """Transparent 0–100 composite score from factors available in the supplied workbook.

    Score = 50% normalized lower-carbon grid score + 30% renewable share +
    20% provider efficiency score. It is a project-defined score, not an official rating.
    """
    intensity = _num(region.get("Carbon_Intensity_kgCO2e_per_kWh"))
    renewable = _num(region.get("Renewable_%"))
    efficiency = _num(region.get("Provider_Efficiency_Score"))
    if intensity is None or renewable is None or efficiency is None:
        return None, None
    all_factors = [_num(r.get("Carbon_Intensity_kgCO2e_per_kWh")) for r in load_carbon_regions()]
    all_factors = [x for x in all_factors if x is not None]
    if not all_factors:
        return None, None
    low, high = min(all_factors), max(all_factors)
    carbon_score = 100.0 if high == low else 100.0 * (high - intensity) / (high - low)
    renewable_score = max(0.0, min(100.0, renewable))
    efficiency_score = max(0.0, min(1.0, efficiency)) * 100.0
    score = 0.50 * carbon_score + 0.30 * renewable_score + 0.20 * efficiency_score
    details = {
        "carbon_component": round(carbon_score, 2),
        "renewable_component": round(renewable_score, 2),
        "provider_efficiency_component": round(efficiency_score, 2),
        "weights_percent": {"carbon_intensity": 50, "renewable_energy": 30, "provider_efficiency": 20},
        "formula": "0.50 × carbon score + 0.30 × renewable percentage + 0.20 × provider efficiency score × 100",
        "notice": "Project-defined comparative score from the uploaded dataset; not an official cloud-provider sustainability rating.",
    }
    return round(max(0.0, min(100.0, score)), 2), details
