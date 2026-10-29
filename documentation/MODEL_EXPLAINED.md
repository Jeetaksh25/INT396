# The Model, Explained

A plain guide to the project for the presentation and viva.

## The problem in one line

A weather station sensor can break (stuck, drifting, noisy, missing), and the weather can also do
something extreme (heat wave, storm). Both look "unusual". The model looks at every hourly reading
and says which one it is: **normal**, one of **six faults**, or one of **four extremes**.

## Two files, that's the whole model

| File | What it does |
|---|---|
| `backend/generate_data.py` | Loads one year of real hourly weather for 8 Indian cities, injects labelled faults and extremes, saves `data/processed/dataset.csv` |
| `backend/model.py` | Builds features, trains a Random Forest, scores it, saves the results the dashboard shows |

`backend/main.py` is only the API that serves those results to the dashboard.

Run them in order:

```bash
cd backend
python generate_data.py
python model.py
```

## Step 1: the data (`generate_data.py`)

- **Real weather:** ERA5 reanalysis from the Open-Meteo archive, 2023, hourly, for Delhi, Mumbai,
  Chennai, Hyderabad, Jaipur, Kolkata, Bengaluru and Shimla. Four sensors each: temperature,
  humidity, wind speed and pressure. That is 8 × 8,760 hours × 4 sensors = **280,320 readings**.
- **Why inject?** Nobody publishes logs of broken weather sensors, so there are no real labels. We
  take real weather and add faults ourselves, so we know exactly which readings are wrong.
- **Faults** (one sensor at a time, 5 episodes of each type per station):

| Fault | What happens to the reading |
|---|---|
| bias | shifted by 4 to 7 standard deviations for 1 to 3 days |
| drift | an offset that grows slowly over 3 to 7 days |
| stuck | the same value repeated for 12 to 48 hours |
| spike | about 15% of hours jump 6 to 10 standard deviations |
| precision | coarse rounding plus noise |
| dropout | readings missing for 6 to 24 hours |

- **Extremes** (several sensors of the station move together, only in their normal season, 2 of
  each per station):

| Extreme | Sensors | Season |
|---|---|---|
| heat wave | temperature +11 °C, humidity −22%, pressure −5 hPa | Apr to Jun |
| cold snap | temperature −11 °C, wind +12, humidity +15 | Dec to Feb |
| storm | wind +35 km/h, pressure −14 hPa, humidity +18 | Jun to Oct |
| heavy rain | humidity +28, temperature −6 °C, wind +16 | Jun to Sep |

Extremes rise and fall smoothly (a sine-shaped bump). Only the hours where the bump is above 30% of
its peak are labelled, because the very start and end look exactly like normal weather.

Final mix: **93.0% normal, 3.9% fault, 3.1% extreme**.

## Step 2: features (`model.py`, `build_features`)

For every reading, 16 numbers:

| Feature | Meaning | Catches |
|---|---|---|
| `value_z` | the reading standardised for its station and sensor | bias, spikes |
| `dev_day` | distance from the 24 hour median | spikes |
| `dev_week` | 24 hour median minus the two week median | bias, drift, extremes |
| `jump` | change from the previous hour | spikes |
| `noise_6h`, `noise_day` | spread of hourly changes over 6 and 24 hours | precision loss |
| `flat_6h` | identical readings in a row | stuck |
| `missing_6h` | missing readings in 6 hours | dropout |
| `others_dev`, `others_week` | how much the other 3 sensors of the station moved | fault vs extreme |
| `temp_week`, `humid_week`, `wind_week`, `press_week` | slow movement of each sensor at the station | which extreme |
| `sensor_code`, `hour` | which sensor, what time of day | context |

The key idea: **a broken sensor moves alone, real weather moves several sensors together.** The
`others_*` and `*_week` station features give the model that view.

## Step 3: the model

- **Random Forest** from scikit-learn: 100 decision trees, max depth 20, at least 2 samples per leaf.
- Why a Random Forest: no scaling needed, it handles thresholds like "6 identical readings" well,
  it is hard to overfit with many trees, and it shows which features mattered.
- It is a **supervised** model: it learns from the labels made in step 1.

## Step 4: honest evaluation

- **4-fold GroupKFold by station.** Stations are split into 4 groups of 2. The model trains on 6
  stations and predicts the other 2, four times, so every reading is predicted by a model that has
  never seen that station. Splitting randomly by row would leak neighbouring hours into training.
- **Baselines:** "always say normal" scores 93.0%, and a fixed physical range check (e.g.
  temperature outside −5 to 45 °C) scores 94.3%.

## Results

| Metric | Random Forest | Range check |
|---|---|---|
| Accuracy (normal / fault / extreme) | **97.9%** | 94.3% |
| Balanced accuracy | **83.4%** | 44.2% |
| Macro F1 | **0.877** | 0.485 |
| Accuracy on all 11 classes | **97.3%** | – |

Per class recall: spike 99%, dropout 98%, stuck 87%, storm 87%, precision 71%, cold snap 69%,
drift 66%, heat wave 65%, bias 52%, heavy rain 19%.

Every station scores between 97.5% and 98.4% accuracy.

Most important features: `dev_week` (21%), `temp_week` (13%), `value_z` (12%), `noise_day` (9%).

## Questions you may be asked

**Why is accuracy so high?** Most readings are normal, and the injected faults are clear. That is
why balanced accuracy and macro F1 are shown too: they weigh the rare classes equally.

**Why not split by random rows?** Neighbouring hours are almost identical, so the model would see
the test answers during training. Splitting by station prevents that.

**What does the model get wrong?** Heavy rain is short and looks like a normal humid day, and the
first hours of a drift are tiny. Bias is sometimes confused with a real weather change.

**Is the data real?** The weather is real ERA5 data. The faults and extremes are injected, because
labelled failures are not public. This is stated on the dashboard and in the paper.

**Why a Random Forest and not deep learning?** 16 tabular features and 280k rows is a classic
tabular problem where tree ensembles are strong, fast and explainable.
