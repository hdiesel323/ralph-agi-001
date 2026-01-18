/**
 * Config API functions for RALPH-AGI.
 */

import { apiClient } from './client';
import type { ConfigResponse, ConfigUpdate } from '@/types/task';

/**
 * Fetch current configuration
 */
export async function getConfig(): Promise<ConfigResponse> {
  const response = await apiClient.get<ConfigResponse>('/api/config');
  return response.data;
}

/**
 * Update runtime settings
 */
export async function updateConfig(updates: ConfigUpdate): Promise<ConfigResponse> {
  const response = await apiClient.patch<ConfigResponse>('/api/config', updates);
  return response.data;
}
