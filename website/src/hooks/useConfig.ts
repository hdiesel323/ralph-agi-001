/**
 * React hook for configuration management.
 */

import { useState, useEffect, useCallback } from "react";
import type {
  ConfigResponse,
  ConfigUpdate,
  RepoContext,
  RuntimeSettings,
} from "@/types/task";
import { getConfig, updateConfig } from "@/api/config";

interface UseConfigReturn {
  config: ConfigResponse | null;
  repo: RepoContext | null;
  settings: RuntimeSettings | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  updateSettings: (updates: ConfigUpdate) => Promise<ConfigResponse>;
}

/**
 * Hook for managing application configuration
 */
export function useConfig(): UseConfigReturn {
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getConfig();
      setConfig(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to fetch config")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    refresh();
  }, [refresh]);

  const updateSettings = useCallback(
    async (updates: ConfigUpdate): Promise<ConfigResponse> => {
      const updated = await updateConfig(updates);
      setConfig(updated);
      return updated;
    },
    []
  );

  return {
    config,
    repo: config?.repo ?? null,
    settings: config?.settings ?? null,
    loading,
    error,
    refresh,
    updateSettings,
  };
}
