from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
import csv, io
from calculator.data_loader import load_carbon_regions, load_cloud_regions, get_region_carbon_data, get_sustainability_score
from calculator.energy import estimate_energy
from calculator.carbon import calculate_carbon
from calculator.location import optimize_regions

app = FastAPI(
    title="Cloud Carbon Footprint Optimizer API",
    description="Estimates workload energy and emissions using configured assumptions and regional dataset values.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class WorkloadRequest(BaseModel):
    cpu_utilization: float = Field(ge=0, le=100)
    ram_gb: float = Field(gt=0)
    storage_gb: float = Field(ge=0)
    runtime_hours: float = Field(gt=0)
    vm_count: int = Field(ge=1)
    provider: str
    region_code: str
    location: str = ""

    @field_validator("provider", "region_code")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("This field cannot be empty.")
        return value.strip()

@app.get("/")
def root():
    return {"message": "Cloud Carbon Footprint Optimizer API", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/regions")
def regions():
    # Show only regions that can actually be calculated with the current carbon dataset.
    # Cloud_Regions may contain metadata for regions without an emissions factor.
    carbon_rows = load_carbon_regions()
    rows = []
    seen = set()
    for row in carbon_rows:
        provider = str(row.get("Provider") or "").strip()
        code = str(row.get("Region_Code") or "").strip()
        try:
            intensity = float(row.get("Carbon_Intensity_gCO2e_per_kWh"))
        except (TypeError, ValueError):
            continue
        if not provider or not code or intensity < 0:
            continue
        key = (provider.lower(), code.lower())
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            **row,
            "Region_Name": row.get("Region_Name") or row.get("Region") or code,
        })
    providers = sorted({str(r.get("Provider", "")).strip() for r in rows if r.get("Provider")})
    return {"providers": providers, "regions": rows, "count": len(rows)}

@app.get("/carbon-regions")
def carbon_regions():
    rows = load_carbon_regions()
    return {"regions": rows, "count": len(rows)}

def calculate_for_region(request: WorkloadRequest, provider: str, region_code: str):
    region = get_region_carbon_data(provider, region_code)
    if not region:
        raise HTTPException(
            status_code=404,
            detail=f"No carbon-intensity data found for provider '{provider}', region '{region_code}'. Check the workbook and region code."
        )
    intensity = region.get("Carbon_Intensity_gCO2e_per_kWh")
    if intensity is None:
        raise HTTPException(status_code=422, detail="This region has no valid Carbon_Intensity_gCO2e_per_kWh value in the dataset.")
    energy = estimate_energy(
        cpu_utilization=request.cpu_utilization,
        ram_gb=request.ram_gb,
        storage_gb=request.storage_gb,
        runtime_hours=request.runtime_hours,
        vm_count=request.vm_count,
    )
    emissions = calculate_carbon(energy["total_energy_kwh"], float(intensity))
    sustainability_score, sustainability_breakdown = get_sustainability_score(region)
    return {
        "provider": provider,
        "region_code": region_code,
        "region_name": region.get("Region_Name") or region.get("Region") or region_code,
        "energy": energy,
        "carbon_intensity_gco2e_per_kwh": float(intensity),
        "carbon": emissions,
        "cfe_percent": region.get("CFE_%"),
        "sustainability_score": sustainability_score,
        "sustainability_score_breakdown": sustainability_breakdown,
        "renewable_percent": region.get("Renewable_%"),
        "provider_efficiency_score": region.get("Provider_Efficiency_Score"),
        "data_method": region.get("Data_Method") or "Unspecified source method",
        "data_source": region.get("Source"),
        "comparability_note": region.get("Comparability_Note"),
        "model_notice": energy["model_notice"],
    }

@app.post("/calculate")
def calculate(request: WorkloadRequest):
    return calculate_for_region(request, request.provider, request.region_code)

@app.post("/optimize")
def optimize(request: WorkloadRequest):
    # IMPORTANT: scope candidates to the user's requested country/location BEFORE ranking.
    location = str(request.location or "").strip()
    if not location:
        raise HTTPException(status_code=422, detail="Enter a target country/location before comparing providers.")

    def norm(value):
        return " ".join(str(value or "").strip().casefold().replace(",", " ").split())

    all_regions = load_carbon_regions()
    matching_regions = [row for row in all_regions if norm(row.get("Country")) == norm(location)]
    if not matching_regions:
        available = sorted({str(row.get("Country")).strip() for row in all_regions if row.get("Country")})
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"No dataset locations match '{location}'. Enter a country exactly as listed in the location field.",
                "available_locations": available,
            },
        )

    candidates = []
    seen = set()
    for row in matching_regions:
        provider = str(row.get("Provider", "")).strip()
        code = str(row.get("Region_Code", "")).strip()
        if not provider or not code or (provider.lower(), code.lower()) in seen:
            continue
        seen.add((provider.lower(), code.lower()))
        try:
            result = calculate_for_region(request, provider, code)
            # Keep the matched geography attached to the result for transparency.
            result["country"] = row.get("Country")
            candidates.append(result)
        except HTTPException:
            continue
    if not candidates:
        providers_in_location = sorted({str(row.get("Provider", "")).strip() for row in matching_regions if row.get("Provider")})
        raise HTTPException(
            status_code=422,
            detail=f"Location '{location}' exists in the dataset, but none of its listed regions has a valid carbon-intensity factor. No winner can be recommended. Providers listed for this location: {', '.join(providers_in_location) or 'none'}.",
        )
    # Recommendation Index = Sustainability Score / Estimated Emissions (kg CO2e).
    # Higher is better. Undefined for missing scores or zero emissions; those rows rank last.
    for item in candidates:
        score = item.get("sustainability_score")
        emissions_kg = (item.get("carbon") or {}).get("carbon_kg")
        if score is not None and emissions_kg is not None and float(emissions_kg) > 0:
            item["recommendation_index"] = round(float(score) / float(emissions_kg), 6)
        else:
            item["recommendation_index"] = None

    ranked = sorted(
        candidates,
        key=lambda item: (
            item.get("recommendation_index") is None,
            -(item.get("recommendation_index") or 0),
            item.get("carbon", {}).get("carbon_kg", float("inf")),
        ),
    )
    for rank, item in enumerate(ranked, start=1):
        item["recommendation_rank"] = rank

    return {
        "requested_location": location,
        "matched_location": ranked[0].get("country") or location,
        "recommended_region": ranked[0],
        "comparisons": ranked,
        "regions_compared": len(ranked),
        "providers_compared": sorted({item["provider"] for item in ranked}),
        "recommendation_basis": f"Ranked by Recommendation Index = Sustainability Score / Estimated Emissions (kg CO2e), highest first, among eligible regions in {location} using the same workload assumptions. AWS/Azure entries marked as proxies are not provider-reported emissions factors.",
        "limitations": [
            "Only rows whose dataset Country matches the requested location are included in this ranking.",
            "Recommendation Index = project-defined Sustainability Score divided by estimated emissions in kg CO2e; higher values rank first. It is not a standardized sustainability metric.",
            "Recommendation Index is undefined when emissions are zero or the sustainability score is missing; those rows are placed last and are not treated as a valid index result.",
            "This is an estimate, not measured cloud energy use.",
            "Energy coefficients are illustrative configurable assumptions and must be validated for your methodology.",
            "Latency, service availability, data residency, and cost are not evaluated.",
            "The uploaded workbook provides country-level carbon intensity and renewable shares, applied as proxies to each listed cloud region. These are not provider-reported emissions.",
            "Providers without a valid carbon factor for the requested location are excluded rather than assigned invented values."
        ]
    }


@app.post("/provider-reports/preview")
async def preview_provider_report(file: UploadFile = File(...)):
    """Validate a provider-reported emissions CSV. Preview only; nothing is persisted."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV export from your cloud provider.")
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.")
    reader = csv.DictReader(io.StringIO(text))
    required = {"provider", "report_period_start", "report_period_end", "region_code", "emissions_kgco2e", "measurement_basis", "source_report"}
    headers = {str(h or "").strip().lower() for h in (reader.fieldnames or [])}
    missing = sorted(required - headers)
    if missing:
        raise HTTPException(status_code=422, detail={"message": "Map provider columns into provider_emissions_import_template.csv first.", "missing_columns": missing})
    records, errors = [], []
    for line_no, row in enumerate(reader, start=2):
        norm = {str(k or "").strip().lower(): (str(v).strip() if v is not None else "") for k,v in row.items()}
        provider = norm.get("provider","").upper()
        if provider not in {"AWS","AZURE","GCP"}:
            errors.append({"line": line_no, "error": "provider must be AWS, AZURE, or GCP"}); continue
        try:
            emissions = float(norm.get("emissions_kgco2e",""))
            if emissions < 0: raise ValueError()
        except ValueError:
            errors.append({"line": line_no, "error": "emissions_kgco2e must be a non-negative number"}); continue
        required_values = ["report_period_start","report_period_end","region_code","measurement_basis","source_report"]
        if any(not norm.get(k) for k in required_values):
            errors.append({"line": line_no, "error": "period, region, measurement basis and source report are required"}); continue
        records.append({
            "provider":provider, "report_period_start":norm["report_period_start"], "report_period_end":norm["report_period_end"],
            "region_code":norm["region_code"], "region_name":norm.get("region_name",""), "service":norm.get("service",""),
            "emissions_scope":norm.get("emissions_scope",""), "emissions_kgco2e":emissions,
            "measurement_basis":norm["measurement_basis"], "source_report":norm["source_report"], "notes":norm.get("notes",""),
            "data_type":"provider-reported emissions"
        })
    return {"rows_validated":len(records),"errors":errors,"records":records,
            "notice":"Preview only; no data is persisted. Compare only aligned periods, scopes, units and measurement bases."}
