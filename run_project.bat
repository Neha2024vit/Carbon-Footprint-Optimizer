@echo off
echo Cloud Carbon Footprint Optimizer
echo.
echo This helper opens two terminal windows: backend and frontend.
echo Run it from the extracted project folder.
if not exist "backend\venv\Scripts\python.exe" (
  echo Backend virtual environment not found.
  echo First run: cd backend ^& py -m venv venv ^& venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Frontend dependencies not found.
  echo First run: cd frontend ^& npm install
  pause
  exit /b 1
)
start "Cloud Carbon Optimizer API" cmd /k "cd /d %~dp0backend && venv\Scripts\python.exe -m uvicorn main:app --reload"
start "Cloud Carbon Optimizer Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo Open http://127.0.0.1:5173
pause
