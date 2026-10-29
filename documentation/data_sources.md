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
cool hill station (SLM), so the model is tested on climates it did not train on.

## Volume

| Quantity | Count |
|---|---|
| Raw station-hours | 70,080 |
| Tidy readings (station-hour-sensor) | 280,320 |
| Stations | 8 |
| Sensors | 4 |

## Preprocessing

1. Each station has 8,760 hourly rows from `2023-01-01 00:00` to `2023-12-31 23:00`.
2. Gaps of at most 2 hours are linearly interpolated on the clean series before injection, so the
   only missing values left are the injected dropouts.
3. Faults and extremes are injected and every changed reading gets its label.

## Why synthetic faults

ERA5 is a quality-controlled reanalysis: it does not contain failing instruments, and public weather
networks do not publish labelled failure logs. The standard workaround, used here, is to inject
realistic faults and extremes into real weather. The weather stays real; only the episodes are
authored. The labels are used to score the unsupervised detectors and to train the small supervised booster.

## Reproducing

```bash
cd backend
python generate_data.py
python model.py
```

`generate_data.py` downloads any missing station CSV from Open-Meteo. All randomness uses seed 42.
