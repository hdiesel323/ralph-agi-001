/**
 * React hook for execution control.
 */

import { useState, useEffect, useCallback } from "react";
import type { ExecutionStatus, ExecutionResults } from "@/types/task";
import {
  getExecutionStatus,
  startExecution,
  stopExecution,
  getExecutionResults,
  cleanupWorktrees,
} from "@/api/tasks";

interface UseExecutionOptions {
  pollingInterval?: number;
}

interface UseExecutionReturn {
  status: ExecutionStatus | null;
  results: ExecutionResults | null;
  loading: boolean;
  error: Error | null;
  isRunning: boolean;
  start: (maxConcurrent?: number, maxTasks?: number) => Promise<void>;
  stop: (wait?: boolean) => Promise<void>;
  cleanup: (force?: boolean) => Promise<number>;
  refresh: () => Promise<void>;
}

/**
 * Hook for managing parallel execution
 */
export function useExecution(
  options: UseExecutionOptions = {}
): UseExecutionReturn {
  const { pollingInterval = 2000 } = options;

  const [status, setStatus] = useState<ExecutionStatus | null>(null);
  const [results, setResults] = useState<ExecutionResults | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [statusData, resultsData] = await Promise.all([
        getExecutionStatus(),
        getExecutionResults(),
      ]);
      setStatus(statusData);
      setResults(resultsData);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err
          : new Error("Failed to fetch execution status")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Polling when running
  useEffect(() => {
    if (!status || status.state !== "running" || pollingInterval <= 0) {
      return;
    }

    const interval = setInterval(refresh, pollingInterval);
    return () => clearInterval(interval);
  }, [status?.state, pollingInterval, refresh]);

  const isRunning = status?.state === "running";

  const start = useCallback(
    async (maxConcurrent = 3, maxTasks?: number) => {
      try {
        setError(null);
        await startExecution({
          max_concurrent: maxConcurrent,
          max_tasks: maxTasks,
        });
        await refresh();
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error("Failed to start execution")
        );
        throw err;
      }
    },
    [refresh]
  );

  const stop = useCallback(
    async (wait = true) => {
      try {
        setError(null);
        await stopExecution(wait);
        await refresh();
      } catch (err) {
        setError(
          err instanceof Error ? err : new Error("Failed to stop execution")
        );
        throw err;
      }
    },
    [refresh]
  );

  const cleanup = useCallback(async (force = false): Promise<number> => {
    try {
      setError(null);
      const result = await cleanupWorktrees(force);
      return result.cleaned;
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to cleanup worktrees")
      );
      throw err;
    }
  }, []);

  return {
    status,
    results,
    loading,
    error,
    isRunning,
    start,
    stop,
    cleanup,
    refresh,
  };
}
