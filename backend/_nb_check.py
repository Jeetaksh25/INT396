import sys
from pathlib import Path

backend = Path.cwd().parent if Path.cwd().name == 'notebooks' else Path.cwd()
sys.path.insert(0, str(backend))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config

assets = backend.parent / 'documentation' / 'assets'
assets.mkdir(parents=True, exist_ok=True)
dataset = pd.read_parquet(config.DATASET_PARQUET)
dataset['timestamp'] = pd.to_datetime(dataset['timestamp'])
dataset.shape
figure, axes = plt.subplots(2, 2, figsize=(9, 6))
for axis, sensor_name in zip(axes.ravel(), config.SENSORS):
    values = dataset.loc[dataset.sensor_name == sensor_name, 'clean_value'].dropna()
    axis.hist(values, bins=60, color='#3f5b8b')
    axis.set_title(f'{sensor_name} ({config.SENSOR_UNITS[sensor_name]})')
figure.suptitle('Clean reading distributions, 2023')
figure.tight_layout()
figure.savefig(assets / 'nb_distributions.png', bbox_inches='tight')

temperature = dataset[dataset.sensor_name == 'temperature'].copy()
temperature['hour'] = temperature.timestamp.dt.hour
temperature['month'] = temperature.timestamp.dt.month

figure, axes = plt.subplots(1, 2, figsize=(10, 3.6))
axes[0].plot(temperature.groupby('hour').clean_value.mean(), color='#b4552d')
axes[0].set_title('Mean temperature by hour')
axes[0].set_xlabel('hour (UTC)')
axes[0].set_ylabel('C')
axes[1].bar(
    temperature.groupby('month').clean_value.mean().index,
    temperature.groupby('month').clean_value.mean().values,
    color='#3f5b8b',
)
axes[1].set_title('Mean temperature by month')
axes[1].set_xlabel('month')
figure.tight_layout()
figure.savefig(assets / 'nb_seasonal.png', bbox_inches='tight')

stuck_row = dataset[dataset.fault_type == 'stuck'].iloc[0]
station = stuck_row.station_id
sensor = stuck_row.sensor_name
series = dataset[(dataset.station_id == station) & (dataset.sensor_name == sensor)]
centre = pd.Timestamp(stuck_row.timestamp)
window = series[(series.timestamp >= centre - pd.Timedelta(hours=72)) & (series.timestamp <= centre + pd.Timedelta(hours=72))]

figure, axis = plt.subplots(figsize=(9, 3.4))
axis.plot(window.timestamp, window.clean_value, color='#3f5b8b', label='clean')
axis.plot(window.timestamp, window.measured_value, color='#b4552d', label='injected')
axis.set_title(f'Stuck sensor: {station} {sensor}')
axis.legend(frameon=False)
figure.tight_layout()
figure.savefig(assets / 'nb_stuck.png', bbox_inches='tight')

heat = dataset[(dataset.extreme_type == 'heat_wave') & (dataset.sensor_name == 'temperature')]
sample = heat.iloc[len(heat) // 2]
centre = pd.Timestamp(sample.timestamp)
station = sample.station_id
temperature_window = dataset[(dataset.station_id == station) & (dataset.sensor_name == 'temperature')]
humidity_window = dataset[(dataset.station_id == station) & (dataset.sensor_name == 'humidity')]
mask = lambda frame: frame[(frame.timestamp >= centre - pd.Timedelta(hours=96)) & (frame.timestamp <= centre + pd.Timedelta(hours=96))]
temperature_window = mask(temperature_window)
humidity_window = mask(humidity_window)

figure, axis = plt.subplots(figsize=(9, 3.4))
axis.plot(temperature_window.timestamp, temperature_window.measured_value, color='#b4552d', label='temperature')
axis.set_ylabel('C')
secondary = axis.twinx()
secondary.plot(humidity_window.timestamp, humidity_window.measured_value, color='#3f7f6b', label='humidity')
secondary.set_ylabel('%')
axis.set_title(f'Heat wave: {station}, two sensors moving together')
figure.tight_layout()
figure.savefig(assets / 'nb_heat_wave.png', bbox_inches='tight')

faults = dataset[dataset.is_fault_injected == 1].copy()
faults['month'] = faults.timestamp.dt.month
counts = faults.groupby(['month', 'fault_type']).size().unstack(fill_value=0)
counts