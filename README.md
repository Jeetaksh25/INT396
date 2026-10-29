# INT-396 · Sensor Fault Classification for Weather Station Networks

A supervised Random Forest that labels every hourly weather-station reading as normal, one of six
sensor faults, or one of four genuine weather extremes. Real ERA5 weather for eight Indian cities,
labelled faults and extremes injected on top, one FastAPI service and one Next.js dashboard.

## Results

Scored with 4-fold cross validation grouped by station, so every reading is predicted by a model
that never saw its station.

| Metric | Random Forest | Range check |
|---|---|---|
| Accuracy (normal / fault / extreme) | **97.9%** | 94.3% |
| Balanced accuracy | **83.4%** | 44.2% |
| Macro F1 | **0.877** | 0.485 |
| Accuracy on all 11 classes | **97.3%** | – |

Always predicting "normal" scores 93.0%, which is why balanced accuracy and macro F1 are reported
next to accuracy.

## Run everything

Double-click **`run.bat`**. It installs dependencies, generates the data and trains the model if
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
| `backend/generate_data.py` | Loads real weather, injects labelled faults and extremes |
| `backend/model.py` | Features, Random Forest, evaluation, result files |
| `backend/main.py` | API that serves the results |
| `frontend/` | Dashboard: overview, stations, events, method, model card |
| `documentation/MODEL_EXPLAINED.md` | The model in plain words, plus viva questions |
| `documentation/research_paper.tex` | IEEE paper for Overleaf |
