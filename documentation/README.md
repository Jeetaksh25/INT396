# Documentation

| File | Contents |
|---|---|
| `MODEL_EXPLAINED.md` | The whole model in plain words, results, and likely viva questions |
| `data_sources.md` | Dataset, licence, citations and stations |
| `research_paper.tex` | Overleaf-ready IEEE conference paper |

## Regenerating everything

```bash
cd backend
python generate_data.py
python model.py
```

The paper's numbers come from `backend/results/metrics.json`.
