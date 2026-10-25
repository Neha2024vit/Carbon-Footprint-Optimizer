"""Workload energy estimate using coefficients in the uploaded workbook."""
from calculator.data_loader import load_energy_coefficients

MODEL_NOTICE = (
    "Illustrative estimate using coefficients from the supplied workbook; these are assumptions, "
    "not measured provider telemetry or validated provider-specific power values."
)

def estimate_energy(cpu_utilization, ram_gb, storage_gb, runtime_hours, vm_count):
    c = load_energy_coefficients()
    cpu_kw = (cpu_utilization / 100.0) * c["cpu_kwh_per_hr_at_100_percent"]
    ram_kw = ram_gb * c["ram_kwh_per_gb_hr"]
    storage_kw = storage_gb / 100.0 * c["storage_kwh_per_100gb_hr"]
    total_kwh = (cpu_kw + ram_kw + storage_kw) * runtime_hours * vm_count
    return {
        "cpu_energy_kwh": round(cpu_kw * runtime_hours * vm_count, 6),
        "ram_energy_kwh": round(ram_kw * runtime_hours * vm_count, 6),
        "storage_energy_kwh": round(storage_kw * runtime_hours * vm_count, 6),
        "total_energy_kwh": round(total_kwh, 6),
        "estimated_power_kw_per_vm": round(cpu_kw + ram_kw + storage_kw, 6),
        "model_notice": MODEL_NOTICE,
        "coefficients": c,
    }
