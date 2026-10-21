export type StationStatus = "HEALTHY" | "WATCH" | "FAULT" | "EXTREME_EVENT";

export interface MetricBlock {
  fault_detection_rate: number;
  fault_classification_rate: number;
  extreme_false_flag_rate: number;
  precision_at_k: Record<string, number>;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate_clean: number;
}

export interface MetricsSummary {
  generated_at: string;
  random_seed: number;
  dataset: {
    stations: string[];
    sensors: string[];
    rows: number;
    start: string;
    end: string;
    source: string;
  };
  detector: MetricBlock;
  baseline_range_check: MetricBlock;
  delta: {
    fault_detection_rate: number;
    extreme_false_flag_rate: number;
    precision: number;
    f1: number;
  };
  per_fault_type_recall: Record<string, number>;
  baseline_per_fault_type_recall: Record<string, number>;
  per_station: Record<
    string,
    {
      fault_detection_rate: number;
      false_positive_rate_clean: number;
      fault_readings: number;
      extreme_readings: number;
    }
  >;
  label_counts: {
    total_readings: number;
    fault_readings: number;
    extreme_readings: number;
  };
  confusion: {
    fault_flagged: number;
    fault_total: number;
    extreme_flagged: number;
    extreme_total: number;
    clean_flagged: number;
    clean_total: number;
  };
  event_metrics: {
    event_count: number;
    fault_events: number;
    extreme_events: number;
    clean_events: number;
    fault_event_precision: number;
    extreme_event_precision: number;
    reason_code_counts: Record<string, number>;
  };
  diagnostics: {
    vote_thresholds: Record<string, number>;
    vote_rates_reference: Record<string, number>;
    pca_components: number;
    dbscan_noise_percent: number;
    lof_outlier_percent: number;
    reference_rows: number;
    total_rows: number;
  };
  timing: Record<string, number>;
  rule_count: number;
  feature_columns: string[];
}

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
