export type StationStatus = "HEALTHY" | "WATCH" | "FAULT" | "EXTREME_EVENT";

export interface ScoreBlock {
  accuracy: number;
  balanced_accuracy: number;
  macro_f1: number;
}

export interface ClassScore {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface MetricsSummary {
  generated_at: string;
  task: string;
  model: {
    name: string;
    trees: number;
    min_samples_leaf: number;
    max_depth: number;
    why: string;
  };
  evaluation: string;
  random_seed: number;
  dataset: {
    stations: string[];
    sensors: string[];
    rows: number;
    start: string;
    end: string;
    source: string;
    train_rows_per_fold: number;
    test_rows_per_fold: number;
  };
  label_counts: {
    total_readings: number;
    normal: number;
    fault: number;
    extreme: number;
  };
  class_counts: Record<string, number>;
  features: string[];
  detailed: ScoreBlock;
  grouped: ScoreBlock;
  majority_baseline: number;
  range_check: ScoreBlock;
  per_class: Record<string, ClassScore>;
  group_confusion: { labels: string[]; matrix: number[][] };
  per_station: Record<string, ScoreBlock>;
  feature_importance: Record<string, number>;
  events: {
    count: number;
    fault_events: number;
    extreme_events: number;
    correct_events: number;
  };
  timing: Record<string, number>;
}

export type ModelCard = MetricsSummary;

export interface StationHealth {
  station_id: string;
  station_name: string;
  latitude: number;
  longitude: number;
  status: StationStatus;
  fault_events: number;
  extreme_events: number;
  anomalous_percent: number;
  last_reading_at: string;
  last_fault_type: string | null;
  total_events: number;
  window_hours: number;
}

export interface SensorSummary {
  sensor_name: string;
  readings: number;
  anomalies: number;
  fault_flags: number;
  extreme_flags: number;
  mean_value: number;
  max_score: number;
}

export interface RecentDetection {
  timestamp: string;
  sensor_name: string;
  measured_value: number | null;
  anomaly_score: number;
  event_label: string | null;
  reason_code: string | null;
}

export interface StationDetail {
  station: StationHealth;
  hours: number;
  window_start: string;
  window_end: string;
  sensor_summary: SensorSummary[];
  fault_breakdown: { reason_code: string; count: number }[];
  recent_detections: RecentDetection[];
}

export interface SensorSeries {
  timestamps: string[];
  values: (number | null)[];
  anomaly_scores: number[];
  is_anomaly: number[];
  event_label: (string | null)[];
  baseline_flag: number[];
}

export interface DetectionEvent {
  event_id: string;
  sensor_name: string;
  start: string;
  end: string;
  label: string;
  reason_code: string;
  mean_anomaly_score: number;
}

export interface StationSeries {
  station_id: string;
  days: number;
  start: string;
  end: string;
  series: Record<string, SensorSeries>;
  events: DetectionEvent[];
}

export interface TimelinePoint {
  timestamp: string;
  anomalies: number;
  fault_flags: number;
  extreme_flags: number;
  anomaly_percent: number;
}

export interface TimelineResponse {
  days: number;
  start: string;
  end: string;
  points: TimelinePoint[];
}

export interface EventRecord {
  event_id: string;
  station_id: string;
  sensor_name: string;
  start: string;
  end: string;
  duration_hours: number;
  label: string;
  reason_code: string;
  mean_anomaly_score: number;
  neighbour_agreement: number;
}

export interface EventsResponse {
  count: number;
  events: EventRecord[];
}
