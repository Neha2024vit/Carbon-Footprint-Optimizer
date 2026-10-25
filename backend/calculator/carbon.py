def calculate_carbon(energy_kwh: float, carbon_intensity_g_per_kwh: float):
    if energy_kwh < 0 or carbon_intensity_g_per_kwh < 0:
        raise ValueError("Energy and carbon intensity must be non-negative.")
    grams = energy_kwh * carbon_intensity_g_per_kwh
    return {
        "carbon_grams": round(grams, 6),
        "carbon_kg": round(grams / 1000.0, 6),
    }
