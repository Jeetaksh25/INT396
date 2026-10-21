# Data Sources

## Primary dataset

| Item | Value |
|---|---|
| Provider | Open-Meteo Historical Weather API |
| Endpoint | `https://archive-api.open-meteo.com/v1/archive` |
| Underlying model | ERA5 reanalysis (ECMWF) |
| Access | No API key, no account |
| Licence | CC BY 4.0 |
| Date range | 2023-01-01 → 2023-12-31, hourly, UTC |
| Stations | 8 Indian cities |
| Variables | temperature_2m, relative_humidity_2m, wind_speed_10m, pressure_msl, precipitation |

### Citations

- Zippenfenig, P. (2023). *Open-Meteo.com Weather API*. Zenodo. doi:10.5281/zenodo.7970649
- Hersbach, H. et al. (2023). *ERA5 hourly data on single levels from 1940 to present*. ECMWF. doi:10.24381/cds.adbb2d47

## Stations

| ID | City | Latitude | Longitude |
|---|---|---|---|
| DEL | Delhi | 28.61 | 77.21 |
| BOM | Mumbai | 19.08 | 72.88 |
| MAA | Chennai | 13.08 | 80.27 |
| HYD | Hyderabad | 17.38 | 78.48 |
| JAI | Jaipur | 26.92 | 75.79 |
| CCU | Kolkata | 22.57 | 88.36 |
| BLR | Bengaluru | 12.97 | 77.59 |
| SLM | Shimla | 31.10 | 77.17 |

The set spans hot arid (JAI), coastal humid (BOM, MAA), tropical (CCU, BLR), inland (HYD, DEL) and a
cool hill station (SLM). That matters because the discriminator depends on stations disagreeing about
weather but agreeing about genuine regional events.

## Volume

| Quantity | Count |
|---|---|
| Raw station-hours | 70,080 |
| Tidy readings (station-hour-sensor) | 280,320 |
| Stations | 8 |
| Sensors | 4 (plus precipitation as auxiliary) |
| Reference period (first 30%) | 84,096 readings |

## Preprocessing

1. Each station is reindexed onto a strict hourly grid from `2023-01-01 00:00` to `2023-12-31 23:00`
   (8,760 hours per station).
2. Gaps of at most 2 hours are linearly interpolated on the **clean** series before fault injection.
   This guarantees the only remaining missing values are the injected dropouts, so a NaN in the final
   dataset is a label, not an accident.
3. A row is dropped only if all four sensors are missing simultaneously.
4. Values are stored as `float64`; humidity is integer-valued in the source and upcast on load.

Interpolation counts per stage are recorded by `src/acquisition/build_dataset.py`, and the sample
committed at `backend/data/samples/dataset_sample.csv` retains the exact output schema.

## Why synthetic faults

ERA5 is a quality-controlled reanalysis: it does not contain failing instruments. Public weather
networks do not publish labelled failure logs. The standard workaround, and the one used here, is to
inject physically realistic faults into real weather so that a detector can be scored without ever
training on labels. The weather remains real; only the fault episodes are authored.

## Reproducing the pull

```bash
cd backend
python -m src.acquisition.fetch_open_meteo
python -m src.acquisition.build_dataset
python -m src.simulation.build_simulation
```

All randomness flows from `config.RANDOM_SEED = 42` and `RANDOM_SEED + 1` for fault injection.
