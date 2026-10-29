# INT-396 · Sensor Fault Discovery in Automatic Weather Station Networks

Unsupervised detection of failing weather-station sensors, with genuine extreme events separated from
instrument faults, plus a small supervised booster that refines the verdicts. Real ERA5 weather for
eight Indian cities, injected faults and extremes, one FastAPI service and one Next.js dashboard.

## Results

| Metric | Range check | Unsupervised detectors | + supervised booster |
|---|---|---|---|
| Accuracy (normal / fault / extreme) | 94.3% | 91.8% | **97.9%** |
| Balanced accuracy | 44.2% | 49.8% | **82.4%** |
| Macro F1 | 0.485 | 0.528 | **0.876** |

The booster is scored with 4-fold cross validation grouped by station. Always predicting "normal"
scores 93.0%, which is why balanced accuracy and macro F1 are reported next to accuracy.

## Run everything

Double-click **`run.bat`**. It installs dependencies, generates the data and runs the model if
results are missing, starts the API and the dashboard, and opens `http://localhost:3000`.

Manual equivalent:

```bash
cd backend
pip install -r requirements.txt
python generate_data.py
python model.py
python -m uvicorn main:app --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

## Project layout

| Path | What it is |
|---|---|
| `backend/generate_data.py` | Loads real weather, injects faults and extremes |
| `backend/model.py` | Main unsupervised model: features, four detectors, vote, fault vs extreme |
| `backend/booster.py` | Small supervised Random Forest that refines the unsupervised verdicts |
| `backend/main.py` | API that serves the results |
| `backend/simulation.py` | Live simulation: random 21-day window, fresh faults, both stages scored |
| `frontend/` | Dashboard: overview, stations, events, simulation, method, model card |
| `documentation/MODEL_EXPLAINED.md` | The model in plain words, plus viva questions |
| `documentation/research_paper.tex` | IEEE paper for Overleaf |
