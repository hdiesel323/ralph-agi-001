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
