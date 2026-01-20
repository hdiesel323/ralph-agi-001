/**
 * UnifiedStatusPanel component.
 * Consolidated sidebar showing metrics, progress, current task, and activity feed.
 */

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  DollarSign,
  Clock,
  Hash,
  Activity,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { getMetrics, getCumulativeMetrics, type CumulativeMetrics } from "@/api/metrics";
import {
  useActivityFeed,
  formatRelativeTime,
  type ActivityItem,
} from "@/hooks/useActivityFeed";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { Metrics, ExecutionStatus, WebSocketEvent } from "@/types/task";

interface UnifiedStatusPanelProps {
  executionStatus: ExecutionStatus | null;
  pollingInterval?: number;
}

export function UnifiedStatusPanel({
  executionStatus,
  pollingInterval = 2000,
}: UnifiedStatusPanelProps) {
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [cumulativeMetrics, setCumulativeMetrics] = useState<CumulativeMetrics | null>(null);
  const [isActivityOpen, setIsActivityOpen] = useState(true);
  const { items: activityItems, addEvent } = useActivityFeed({ maxItems: 30 });

  // Subscribe to WebSocket events for activity feed
  useWebSocket({
    autoConnect: true,
    onEvent: (event: WebSocketEvent) => {
      addEvent(event);
    },
  });

  const fetchMetrics = useCallback(async () => {
    try {
      const [currentMetrics, cumulative] = await Promise.all([
        getMetrics(),
        getCumulativeMetrics(),
      ]);
      setMetrics(currentMetrics);
      setCumulativeMetrics(cumulative);
    } catch {
      // Silently fail - metrics are optional
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, pollingInterval);
    return () => clearInterval(interval);
  }, [fetchMetrics, pollingInterval]);

  const isRunning = executionStatus?.state === "running";
  const progress = executionStatus?.progress;
  const totalProcessed = progress ? progress.completed + progress.failed : 0;
  const progressPercent =
    progress && progress.total_tasks > 0
      ? (totalProcessed / progress.total_tasks) * 100
      : 0;

  return (
    <div className="space-y-4">
      {/* Cost & Time - Cumulative Metrics */}
      <Card>
        <CardContent className="pt-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="text-center p-3 bg-emerald-50 dark:bg-emerald-950/30 rounded-lg">
              <div className="flex items-center justify-center gap-1 text-emerald-600 dark:text-emerald-400 mb-1">
                <DollarSign className="h-4 w-4" />
                <span className="text-xs font-medium">Total Cost</span>
              </div>
              <p className="text-2xl font-bold text-emerald-700 dark:text-emerald-300">
                {cumulativeMetrics?.total_cost_formatted || "$0.0000"}
              </p>
            </div>
            <div className="text-center p-3 bg-blue-50 dark:bg-blue-950/30 rounded-lg">
              <div className="flex items-center justify-center gap-1 text-blue-600 dark:text-blue-400 mb-1">
                <Clock className="h-4 w-4" />
                <span className="text-xs font-medium">Total Time</span>
              </div>
              <p className="text-2xl font-bold text-blue-700 dark:text-blue-300">
                {cumulativeMetrics?.total_time_formatted || "00:00:00"}
              </p>
            </div>
          </div>

          {/* Token count - cumulative */}
          <div className="flex items-center justify-center gap-2 mt-3 text-sm text-muted-foreground">
            <Hash className="h-3.5 w-3.5" />
            <span>{cumulativeMetrics?.total_tokens_formatted || "0"} tokens</span>
            <span className="text-muted-foreground/50">|</span>
            <span className="text-xs">
              {formatNumber(cumulativeMetrics?.total_input_tokens || 0)} in /{" "}
              {formatNumber(cumulativeMetrics?.total_output_tokens || 0)} out
            </span>
          </div>

          {/* Empty state message */}
          {cumulativeMetrics && cumulativeMetrics.total_tokens === 0 && (
            <p className="text-xs text-muted-foreground text-center mt-3">
              Metrics will appear when tasks are executed
            </p>
          )}

          {/* Success rate */}
          {cumulativeMetrics && (cumulativeMetrics.tasks_completed > 0 || cumulativeMetrics.tasks_failed > 0) && (
            <div className="flex items-center justify-center gap-2 mt-2 text-xs text-muted-foreground">
              <span className="text-green-600">{cumulativeMetrics.tasks_completed} completed</span>
              <span className="text-muted-foreground/50">|</span>
              <span className="text-red-500">{cumulativeMetrics.tasks_failed} failed</span>
              <span className="text-muted-foreground/50">|</span>
              <span>{cumulativeMetrics.success_rate}% success</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Progress Section */}
      {progress && progress.total_tasks > 0 && (
        <Card>
          <CardContent className="pt-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Progress</span>
                <span className="text-sm text-muted-foreground">
                  {totalProcessed}/{progress.total_tasks} tasks
                </span>
              </div>
              <Progress value={progressPercent} className="h-2" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  {isRunning && <Loader2 className="h-3 w-3 animate-spin" />}
                  {progress.running} running
                </span>
                <span>{progress.pending} pending</span>
                <span className="text-green-600">
                  {progress.completed} done
                </span>
                {progress.failed > 0 && (
                  <span className="text-red-500">{progress.failed} failed</span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current Task */}
      {metrics?.current_task && (
        <Card className="border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/20">
          <CardContent className="pt-4">
            <div className="flex items-start gap-2">
              <Loader2 className="h-4 w-4 mt-0.5 animate-spin text-amber-600" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-amber-600 dark:text-amber-400 font-medium mb-1">
                  Working on
                </p>
                <p className="text-sm font-medium truncate">
                  {metrics.current_task}
                </p>
                {metrics.iteration > 0 && (
                  <p className="text-xs text-muted-foreground mt-1">
                    Iteration {metrics.iteration}/{metrics.max_iterations}
                  </p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Errors Warning */}
      {metrics && metrics.errors > 0 && (
        <Card className="border-red-200 dark:border-red-800 bg-red-50/50 dark:bg-red-950/20">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
              <AlertTriangle className="h-4 w-4" />
              <span className="text-sm font-medium">
                {metrics.errors} error{metrics.errors > 1 ? "s" : ""} occurred
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Activity Feed */}
      <Collapsible open={isActivityOpen} onOpenChange={setIsActivityOpen}>
        <Card>
          <CollapsibleTrigger asChild>
            <CardHeader className="pb-2 cursor-pointer hover:bg-muted/50 transition-colors">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Activity className="h-4 w-4" />
                  Activity
                  {activityItems.length > 0 && (
                    <Badge variant="secondary" className="text-xs">
                      {activityItems.length}
                    </Badge>
                  )}
                </CardTitle>
                {isActivityOpen ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent className="pt-0">
              {activityItems.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No activity yet
                </p>
              ) : (
                <ScrollArea className="h-[200px]">
                  <div className="space-y-1">
                    {activityItems.map(item => (
                      <ActivityRow key={item.id} item={item} />
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>
    </div>
  );
}

function ActivityRow({ item }: { item: ActivityItem }) {
  const typeColors = {
    tool: "text-blue-600 dark:text-blue-400",
    agent: "text-purple-600 dark:text-purple-400",
    log: "text-muted-foreground",
    error: "text-red-600 dark:text-red-400",
    task: "text-green-600 dark:text-green-400",
  };

  return (
    <div
      className={`flex items-start gap-2 py-1.5 px-1 rounded text-xs ${
        item.type === "error" ? "bg-red-50 dark:bg-red-950/20" : ""
      }`}
    >
      <span className="flex-shrink-0 w-5 text-center">{item.icon}</span>
      <div className="flex-1 min-w-0">
        <span className={typeColors[item.type]}>{item.message}</span>
        {item.detail && (
          <span className="text-muted-foreground ml-1 truncate block">
            {item.detail}
          </span>
        )}
      </div>
      <span className="flex-shrink-0 text-muted-foreground/60">
        {formatRelativeTime(item.timestamp)}
      </span>
    </div>
  );
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + "M";
  if (num >= 1_000) return (num / 1_000).toFixed(1) + "K";
  return num.toLocaleString();
}

export default UnifiedStatusPanel;
