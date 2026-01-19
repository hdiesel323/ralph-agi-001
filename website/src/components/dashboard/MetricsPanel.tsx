/**
 * MetricsPanel component.
 * Displays real-time execution metrics including cost, tokens, and time.
 */

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DollarSign,
  Hash,
  Clock,
  Activity,
  AlertTriangle,
  Cpu,
} from "lucide-react";
import { getMetrics } from "@/api/metrics";
import type { Metrics } from "@/types/task";

interface MetricsPanelProps {
  /** Polling interval in milliseconds (default: 2000) */
  pollingInterval?: number;
  /** Whether to auto-refresh metrics */
  autoRefresh?: boolean;
}

export function MetricsPanel({
  pollingInterval = 2000,
  autoRefresh = true,
}: MetricsPanelProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const fetchMetrics = useCallback(async () => {
    try {
      const data = await getMetrics();
      setMetrics(data);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to fetch metrics")
      );
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchMetrics();

    // Set up polling if auto-refresh is enabled
    if (autoRefresh) {
      const interval = setInterval(fetchMetrics, pollingInterval);
      return () => clearInterval(interval);
    }
  }, [fetchMetrics, pollingInterval, autoRefresh]);

  if (!metrics) {
    return null;
  }

  return (
    <Card className="mb-4">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Live Metrics
          </CardTitle>
          {metrics.tasks_running > 0 && (
            <span className="text-xs text-green-500 animate-pulse">
              Recording
            </span>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Current Task */}
        {metrics.current_task && (
          <div className="p-2 bg-blue-500/10 rounded-lg">
            <p className="text-xs text-muted-foreground mb-1">Working on</p>
            <p className="text-sm font-medium truncate">
              {metrics.current_task}
            </p>
          </div>
        )}

        {/* Primary Metrics Grid */}
        <div className="grid grid-cols-2 gap-3">
          <MetricCard
            icon={<DollarSign className="h-4 w-4" />}
            label="Cost"
            value={`$${metrics.cost.toFixed(4)}`}
            color="text-green-500"
          />
          <MetricCard
            icon={<Clock className="h-4 w-4" />}
            label="Time"
            value={metrics.elapsed_formatted}
            color="text-blue-500"
          />
          <MetricCard
            icon={<Hash className="h-4 w-4" />}
            label="Tokens"
            value={formatNumber(metrics.total_tokens)}
            color="text-purple-500"
          />
          <MetricCard
            icon={<Cpu className="h-4 w-4" />}
            label="Iteration"
            value={`${metrics.iteration}/${metrics.max_iterations}`}
            color="text-orange-500"
          />
        </div>

        {/* Token Breakdown */}
        <div className="text-xs text-muted-foreground flex justify-between px-1">
          <span>Input: {formatNumber(metrics.input_tokens)}</span>
          <span>Output: {formatNumber(metrics.output_tokens)}</span>
        </div>

        {/* Task Stats */}
        <div className="flex items-center justify-between text-sm pt-2 border-t">
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground">
              Completed:{" "}
              <span className="text-foreground font-medium">
                {metrics.tasks_completed}
              </span>
            </span>
            <span className="text-muted-foreground">
              Running:{" "}
              <span className="text-foreground font-medium">
                {metrics.tasks_running}
              </span>
            </span>
          </div>
          {metrics.errors > 0 && (
            <div className="flex items-center gap-1 text-red-500">
              <AlertTriangle className="h-3 w-3" />
              <span>{metrics.errors} errors</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

interface MetricCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}

function MetricCard({ icon, label, value, color }: MetricCardProps) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/50">
      <div className={color}>{icon}</div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-semibold text-sm">{value}</p>
      </div>
    </div>
  );
}

/**
 * Format large numbers with K/M suffixes
 */
function formatNumber(num: number): string {
  if (num >= 1_000_000) {
    return (num / 1_000_000).toFixed(1) + "M";
  }
  if (num >= 1_000) {
    return (num / 1_000).toFixed(1) + "K";
  }
  return num.toLocaleString();
}

export default MetricsPanel;
