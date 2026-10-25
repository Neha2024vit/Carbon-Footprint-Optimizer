# Cloud Carbon Footprint Optimizer

A local React + FastAPI academic prototype that estimates workload energy and electricity-related emissions from the user-provided workbook and compares AWS, Azure, and GCP regions for the selected country. It also calculates and displays a project-defined sustainability score using the workbook's carbon intensity, renewable-energy percentage, and provider efficiency score.

## Dataset used

The supplied workbook is included at `backend/data/carbon_datasets.xlsx`. The backend reads these sheets:

- `Cloud_Regions`: provider, region, country
- `Carbon_Intensity`: country-level `kgCO2_per_kWh`
- `Renewable_Energy`: country-level renewable share
- `Cloud_Sustainability`: provider efficiency score
- `Energy_Coefficients`: CPU, RAM, and storage energy coefficients

The sample dataset lists nine region entries across AWS, Azure, and GCP. Country carbon intensity and renewable percentage are applied to listed regions as country-level proxies. Therefore, regional rows in the same country can have the same carbon intensity and emissions for an identical workload. 
## Sustainability score

A score from 0 to 100 is calculated by the application for every eligible provider/region:

`Sustainability Score = 0.50 × Carbon Score + 0.30 × Renewable Share + 0.20 × Provider Efficiency Score (scaled to 0–100)`

Where:

- **Carbon Score** = normalized lower-is-better score from country-level carbon intensity, where the highest intensity in the dataset receives 0 and the lowest receives 100.
- **Renewable Share** = the dataset's renewable-energy percentage (0–100).
- **Provider Efficiency Score** = `EfficiencyScore × 100` from `Cloud_Sustainability`.

The weights and normalization are a transparent, project-defined scoring model, not an official AWS/Azure/GCP sustainability rating. The score is displayed in the snapshot and for every row in the region comparison table. The region comparison table also displays the Recommendation Index (score points per kg CO2e). It should be described as an academic comparative indicator.

## Recommendation index\n\n`Recommendation Index = Sustainability Score / Estimated Emissions (kg CO2e)`\n\nHigher values rank first. The index is only calculated when the sustainability score is available and estimated emissions are greater than zero. Zero-emission or missing-score rows receive no index and are placed after valid index results. 

Energy coefficients are loaded from the workbook:

- CPU power estimate = CPU utilization × `CPU_kWh_per_hr_at100%`
- RAM contribution = RAM GB × `RAM_kWh_per_GB_hr`
- Storage contribution = (storage GB / 100) × `Storage_kWh_per_100GB_hr`
- Estimated energy (kWh) = modeled power contributions × runtime hours × VM count
- Estimated emissions (gCO2e) = estimated energy (kWh) × carbon intensity (gCO2e/kWh)
- Estimated emissions (kgCO2e) = grams / 1,000

The workbook labels these as coefficients; they are assumptions and are not validated provider telemetry. The app reports estimates, not measured cloud emissions.

## Run on Windows / VS Code

Requirements: Python 3.12 recommended for this project; Node.js 20 LTS recommended.

### 1. Backend terminal

From the project root:

```powershell
cd backend
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload
```

If `venv` already exists from a previous run, skip the `py -3.12 -m venv venv` command and only activate it.

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/health

### 2. Frontend terminal

Open a second terminal at the project root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually http://localhost:5173.

## Optimization behavior

The frontend sends the target country to `POST /optimize`. The backend filters the workbook rows by exact case-insensitive country match before calculation and ranking. It compares eligible regions only for that country. Ranking uses the project-defined Recommendation Index: `Sustainability Score / Estimated Emissions (kg CO2e)`. A higher index ranks first. If the index is undefined because emissions are zero or the score is missing, that row is placed last. The index is a custom comparative ratio, not a standardized sustainability metric. This does not imply a complete overall recommendation based on price, latency, availability, or data residency.



## Main API endpoints

- `GET /health`
- `GET /regions`
- `GET /carbon-regions`
- `POST /calculate`
- `POST /optimize`
- `POST /provider-reports/preview`
