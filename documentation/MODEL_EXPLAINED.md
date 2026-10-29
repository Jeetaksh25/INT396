# The Model, Explained

A plain guide to the project for the presentation and viva.

## The problem in one line

A weather station sensor can break (stuck, drifting, noisy, missing), and the weather can also do
something extreme (heat wave, storm). Both look "unusual". The system finds unusual readings without
labels and decides whether each is a **fault** or a real **extreme**.

## The files

| File | What it does |
|---|---|
| `backend/generate_data.py` | Loads one year of real hourly weather for 8 Indian cities, injects faults and extremes, saves `data/processed/dataset.csv` |
| `backend/model.py` | **The main unsupervised model**: builds features, runs four unsupervised detectors, votes, separates fault from extreme, saves results |
| `backend/booster.py` | A small supervised Random Forest that refines the unsupervised verdicts |
| `backend/main.py` | API that serves the results to the dashboard |
| `backend/simulation.py` | Powers the Simulation tab: a fresh random window scored live by the saved detectors and booster |

Run:

```bash
cd backend
python generate_data.py
python model.py
```

`model.py` calls the booster itself at the end.

## Step 1: the data (`generate_data.py`)

- **Real weather:** ERA5 reanalysis from the Open-Meteo archive, 2023, hourly, for Delhi, Mumbai,
  Chennai, Hyderabad, Jaipur, Kolkata, Bengaluru and Shimla. Four sensors each: temperature,
  humidity, wind speed and pressure, giving 8 × 8,760 hours × 4 sensors = **280,320 readings**.
- **Why inject?** Nobody publishes logs of broken weather sensors. We take real weather and add
  faults ourselves, so we can check the results afterwards.
- **Faults** (one sensor at a time, 5 episodes of each type per station):

| Fault | What happens to the reading |
|---|---|
| bias | shifted by 4 to 7 standard deviations for 1 to 3 days |
| drift | an offset that grows slowly over 3 to 7 days |
| stuck | the same value repeated for 12 to 48 hours |
| spike | about 15% of hours jump 6 to 10 standard deviations |
| precision | coarse rounding plus noise |
| dropout | readings missing for 6 to 24 hours |

- **Extremes** (several sensors move together, only in their season, 2 of each per station):

| Extreme | Sensors | Season |
|---|---|---|
| heat wave | temperature +11 °C, humidity −22%, pressure −5 hPa | Apr to Jun |
| cold snap | temperature −11 °C, wind +12, humidity +15 | Dec to Feb |
| storm | wind +35 km/h, pressure −14 hPa, humidity +18 | Jun to Oct |
| heavy rain | humidity +28, temperature −6 °C, wind +16 | Jun to Sep |

Final mix: **93.0% normal, 3.9% fault, 3.1% extreme**.

## Step 2: features (`model.py`, `build_features`)

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
| `sensor_code`, `hour` | which sensor, what time of day | context (booster only) |

Key idea: **a broken sensor moves alone, real weather moves several sensors together.**

## Step 3: the unsupervised model (`model.py`)

No labels are used to fit any of these. The 14 numeric features are standardised, and each detector
is fitted on a random sample of 20,000 readings:

| Detector | Unusual means | Setting |
|---|---|---|
| Isolation Forest | the reading is isolated in few random splits | 200 trees |
| Local Outlier Factor | the reading sits in a much emptier area than its neighbours | 20 neighbours |
| k-Means | the reading is far from every cluster centre | 8 clusters |
| PCA | the reading cannot be rebuilt from the main components | 11 components (90% variance) |

- **Vote:** each detector votes when its score is in its top 5%. **2 of 4 votes** flag the reading.
- **Fault or extreme:** if the other sensors of the station are also moving (`others_week` > 0.5),
  it is an **extreme**, otherwise a **fault**.

## Step 4: the supervised booster (`booster.py`)

The unsupervised stage finds unusual readings but flags too many healthy ones, and one simple rule
can't tell ten event types apart. The booster is a small **Random Forest** (100 trees, depth 20). Its
inputs are the 16 features plus the four detector scores and the vote count, and it learns from the
injected labels which flags are real. It is tested with **4-fold GroupKFold by station**: it trains
on 6 stations and predicts the other 2, so it never sees the station it is scored on.

## Results

| Metric | Range check | Unsupervised | + booster |
|---|---|---|---|
| Accuracy (normal / fault / extreme) | 94.3% | 91.8% | **97.9%** |
| Balanced accuracy | 44.2% | 49.8% | **82.4%** |
| Macro F1 | 0.485 | 0.528 | **0.876** |

- Always guessing "normal" scores 93.0%. That is why balanced accuracy and macro F1 matter.
- The unsupervised stage flags 3.4% of healthy readings; with the booster it is 0.3%.
- 11-class accuracy with the booster: 97.3%. Every station: 97.4% to 98.5%.
- The booster's top inputs: `dev_week` 16.5%, `temp_week` 10.9%, `value_z` 10.5%, `noise_day` 7.4%,
  k-Means score 6.3%, Isolation Forest score 5.5%. The detector inputs make up 17.9% in total.

## Questions you may be asked

**Is it unsupervised?** The detection stage is: four detectors and a vote, no labels. The booster
on top is supervised and uses the injected labels; the paper reports both stages separately.

**Why is the unsupervised accuracy below "always normal"?** It flags 5% of readings, and most of
those are unusual but healthy weather. Its balanced accuracy and F1 are still better than the
range check.

**Why add a booster?** The detectors tell you a reading is unusual but not why. With a few labelled
examples, a small model can learn which score patterns mean fault, extreme or nothing.

**Why split by station?** Neighbouring hours are almost identical, so a random split would leak test
answers into training.

**What is still hard?** Heavy rain (short, looks like a humid day), the first hours of a drift, and
bias that looks like a genuine weather change.

**Is the data real?** The weather is real ERA5 data. Faults and extremes are injected because
labelled failures are not public.
