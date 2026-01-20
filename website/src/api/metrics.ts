/**
 * API client functions for metrics endpoints.
 */

import { apiClient } from "./client";
import type { Metrics } from "@/types/task";

/**
 * Get current execution metrics
 */
export async function getMetrics(): Promise<Metrics> {
  const response = await apiClient.get<Metrics>("/api/metrics");
  return response.data;
}

/**
 * Reset metrics to zero
 */
export async function resetMetrics(): Promise<{
  status: string;
  message: string;
}> {
  const response = await apiClient.post<{ status: string; message: string }>(
    "/api/metrics/reset"
  );
  return response.data;
}

/**
 * Add token usage to metrics
 */
export async function addTokens(
  inputTokens: number,
  outputTokens: number
): Promise<Metrics> {
  const response = await apiClient.post<Metrics>(
    `/api/metrics/tokens?input_tokens=${inputTokens}&output_tokens=${outputTokens}`
  );
  return response.data;
}

/**
 * Cumulative metrics aggregated from all tasks
 */
export interface CumulativeMetrics {
  total_cost: number;
  total_cost_formatted: string;
  total_tokens: number;
  total_tokens_formatted: string;
  total_input_tokens: number;
  total_output_tokens: number;
  total_time_seconds: number;
  total_time_formatted: string;
  total_api_calls: number;
  tasks_total: number;
  tasks_completed: number;
  tasks_failed: number;
  tasks_cancelled: number;
  tasks_running: number;
  tasks_pending: number;
  success_rate: number;
}

/**
 * Get cumulative metrics across all tasks
 */
export async function getCumulativeMetrics(): Promise<CumulativeMetrics> {
  const response = await apiClient.get<CumulativeMetrics>(
    "/api/metrics/cumulative"
  );
  return response.data;
}
