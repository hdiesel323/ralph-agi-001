/**
 * QuickActionsBar component.
 * Simplified action bar with essential controls only.
 */

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Play, Square, Plus, RefreshCw } from "lucide-react";
import type { ExecutionStatus, QueueStats } from "@/types/task";

interface QuickActionsBarProps {
  executionStatus: ExecutionStatus | null;
  queueStats: QueueStats | null;
  onStart: (maxConcurrent?: number) => Promise<void>;
  onStop: () => Promise<void>;
  onClear: (includeRunning?: boolean) => Promise<void>;
  onRefresh: () => Promise<void>;
  onCreateTask: () => void;
}

export function QuickActionsBar({
  executionStatus,
  queueStats,
  onStart,
  onStop,
  onRefresh,
  onCreateTask,
}: QuickActionsBarProps) {
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const isRunning = executionStatus?.state === "running";
  const isStopping_ = executionStatus?.state === "stopping";
  const pendingCount = (queueStats?.pending || 0) + (queueStats?.ready || 0);
  const canStart = pendingCount > 0;

  // Calculate overall progress
  const progress = useMemo(() => {
    if (!queueStats) return null;
    const total = queueStats.total;
    if (total === 0) return null;
    const completed = queueStats.complete + queueStats.failed + queueStats.cancelled;
    const percentage = Math.round((completed / total) * 100);
    return { percentage, completed, total };
  }, [queueStats]);

  const handleStart = async () => {
    setIsStarting(true);
    try {
      await onStart(3);
    } finally {
      setIsStarting(false);
    }
  };

  const handleStop = async () => {
    setIsStopping(true);
    try {
      await onStop();
    } finally {
      setIsStopping(false);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await onRefresh();
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="flex flex-col border-b bg-card">
      {/* Progress bar - only show when there are tasks */}
      {progress && progress.total > 0 && (
        <div className="relative h-1.5 bg-muted">
          <Progress
            value={progress.percentage}
            className="h-1.5 rounded-none"
          />
        </div>
      )}

      <div className="flex items-center justify-between px-4 py-3">
        {/* Left side: Status & Stats */}
        <div className="flex items-center gap-4">
        <Badge
          variant={isRunning ? "default" : "secondary"}
          className={`text-xs ${isRunning ? "bg-green-500 hover:bg-green-600 animate-pulse" : ""}`}
        >
          {executionStatus?.state || "idle"}
        </Badge>

        {queueStats && (
          <div className="flex items-center gap-3 text-sm text-muted-foreground">
            <span className="font-medium text-foreground">
              {pendingCount} pending
            </span>
            <span className="text-muted-foreground/40">|</span>
            <span>{queueStats.running} running</span>
            <span className="text-muted-foreground/40">|</span>
            <span className="text-green-600">{queueStats.complete} done</span>
            {queueStats.failed > 0 && (
              <>
                <span className="text-muted-foreground/40">|</span>
                <span className="text-red-500">{queueStats.failed} failed</span>
              </>
            )}
          </div>
        )}
      </div>

      {/* Right side: Actions */}
      <div className="flex items-center gap-2">
        <Button onClick={onCreateTask} size="sm" variant="outline">
          <Plus className="mr-1.5 h-4 w-4" />
          Add Task
        </Button>

        {!isRunning ? (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                disabled={isStarting || !canStart}
                className="bg-green-600 hover:bg-green-700 min-w-[80px]"
                onClick={handleStart}
              >
                {isStarting ? (
                  <Spinner className="mr-1.5 h-4 w-4" />
                ) : (
                  <Play className="mr-1.5 h-4 w-4" />
                )}
                Start
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {canStart
                ? `Start processing ${pendingCount} task${pendingCount > 1 ? "s" : ""}`
                : "No pending tasks to process"}
            </TooltipContent>
          </Tooltip>
        ) : (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleStop}
            disabled={isStopping || isStopping_}
            className="min-w-[80px]"
          >
            {isStopping || isStopping_ ? (
              <Spinner className="mr-1.5 h-4 w-4" />
            ) : (
              <Square className="mr-1.5 h-4 w-4" />
            )}
            Stop
          </Button>
        )}

        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="h-9 w-9"
            >
              {isRefreshing ? (
                <Spinner className="h-4 w-4" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
          </TooltipTrigger>
          <TooltipContent>Refresh</TooltipContent>
        </Tooltip>

        {/* Progress indicator */}
        {progress && (
          <span className="text-xs text-muted-foreground ml-2">
            {progress.percentage}% ({progress.completed}/{progress.total})
          </span>
        )}
        </div>
      </div>
    </div>
  );
}

export default QuickActionsBar;
