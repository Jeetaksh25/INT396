export type SimDecision = "HEALTHY" | "FAULT" | "EXTREME";

export type SimTruth = "clean" | "fault" | "extreme";

export interface SimRecord {
  station_id: string;
  station_name: string;
  sensor_name: string;
  unit: string;
  timestamp: string;
  measured_value: number | null;
  votes: number[];
  vote_count: number;
  anomaly_score: number;
  decision: SimDecision;
  reason_code: string | null;
  truth: SimTruth;
  fault_type: string | null;
  extreme_type: string | null;
  correct: boolean;
}

export interface SimLaneBlock {
  total: number;
  flagged: number;
  rate: number;
}

export interface SimStreamBlock {
  total: number;
  correct: number;
  accuracy: number;
  by_truth: Record<SimTruth, { total: number; correct: number }>;
  by_decision: Record<SimDecision, { total: number; correct: number }>;
}

export interface SimMetricBlock {
  fault_detection_rate: number;
  fault_classification_rate: number;
  extreme_false_flag_rate: number;
  precision_at_k: Record<string, number>;
  precision: number;
  recall: number;
  f1: number;
  false_positive_rate_clean: number;
}

export interface SimEpisode {
  fault_type?: string;
  extreme_type?: string;
  station_id: string;
  sensor_name?: string;
  start: string;
  end: string;
  affected_rows?: number;
  duration_hours?: number;
}

export interface SimResult {
  seed: number;
  window_days: number;
  window: { start: string; end: string };
  counts: {
    readings: number;
    stations: number;
    sensors: number;
    hours: number;
    fault_episodes: number;
    extreme_episodes: number;
    fault_readings: number;
    extreme_readings: number;
    clean_readings: number;
  };
  bins: { healthy: number; fault: number; extreme: number };
  stream: SimStreamBlock;
  detector: SimMetricBlock;
  baseline: SimMetricBlock;
  delta: {
    fault_detection_rate: number;
    extreme_false_flag_rate: number;
    precision: number;
    f1: number;
  };
  per_fault_type_recall: Record<string, number>;
  baseline_per_fault_type_recall: Record<string, number>;
  confusion: { fault: SimLaneBlock; extreme: SimLaneBlock; clean: SimLaneBlock };
  event_metrics: {
    event_count: number;
    fault_events: number;
    extreme_events: number;
    clean_events: number;
    fault_event_precision: number;
    extreme_event_precision: number;
    reason_code_counts: Record<string, number>;
  };
  per_station: Record<
    string,
    {
      fault_detection_rate: number;
      false_positive_rate_clean: number;
      fault_readings: number;
      extreme_readings: number;
    }
  >;
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
  fault_types: string[];
  extreme_types: string[];
  detectors: string[];
  episodes: { fault: SimEpisode[]; extreme: SimEpisode[] };
  records: SimRecord[];
}
