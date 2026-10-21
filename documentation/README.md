# Documentation

Source material for the IEEE report and the viva.

| File | Contents |
|---|---|
| `data_sources.md` | Dataset, licences, citations, stations, preprocessing |
| `methodology.md` | Fault and extreme models, features, detector, discriminator, baseline |
| `metrics_definitions.md` | Every metric with its formula and what it proves |
| `results.md` | Final measured numbers, per-fault breakdown, honest limitations |
| `experiments.md` | Experiment log across four runs with the diagnoses |
| `final_report.tex` | Overleaf-ready IEEE conference paper |
| `assets/` | Figures exported from the pipeline and the notebook |

## Regenerating everything

```bash
cd backend
python -m src.acquisition.fetch_open_meteo
python -m src.acquisition.build_dataset
python -m src.simulation.build_simulation
python -m src.evaluation.run_experiment
python -m src.evaluation.export_rules
python -m src.evaluation.generate_figures
```

Then copy `backend/results/figures/*.png` into `documentation/assets/`.
