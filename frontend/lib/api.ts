import {
  EventsResponse,
  MetricsSummary,
  StationDetail,
  StationHealth,
  StationSeries,
  TimelineResponse,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}: ${path}`);
  }
  return (await response.json()) as T;
}

export function getMetrics(): Promise<MetricsSummary> {
  return request<MetricsSummary>("/api/metrics");
}

export function getStations(): Promise<StationHealth[]> {
  return request<StationHealth[]>("/api/stations");
}

export function getStationDetail(stationId: string, hours = 168): Promise<StationDetail> {
  return request<StationDetail>(`/api/stations/${stationId}?hours=${hours}`);
}

export function getStationSeries(stationId: string, days = 30): Promise<StationSeries> {
  return request<StationSeries>(`/api/stations/${stationId}/series?days=${days}`);
}

export function getTimeline(days = 30): Promise<TimelineResponse> {
  return request<TimelineResponse>(`/api/timeline?days=${days}`);
}

export function getEvents(limit = 100, label?: string): Promise<EventsResponse> {
  const suffix = label ? `&label=${label}` : "";
  return request<EventsResponse>(`/api/events?limit=${limit}${suffix}`);
}
