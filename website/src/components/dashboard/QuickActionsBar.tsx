/**
 * QuickActionsBar component.
 * Provides quick action buttons for execution control.
 */

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Spinner } from '@/components/ui/spinner';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Play, Square, Pause, Trash2, Plus, RefreshCw, Settings, ChevronDown } from 'lucide-react';
import type { ExecutionStatus, QueueStats } from '@/types/task';

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
  onClear,
  onRefresh,
  onCreateTask,
}: QuickActionsBarProps) {
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);
  const [isClearing, setIsClearing] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const isRunning = executionStatus?.state === 'running';
  const isStopping_ = executionStatus?.state === 'stopping';

  const handleStart = async (maxConcurrent = 3) => {
    setIsStarting(true);
    try {
      await onStart(maxConcurrent);
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

  const handleClear = async (includeRunning = false) => {
    setIsClearing(true);
    try {
      await onClear(includeRunning);
    } finally {
      setIsClearing(false);
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
    <div className="flex items-center justify-between p-4 border-b bg-card">
      <div className="flex items-center gap-4">
        {/* Execution Status */}
        <div className="flex items-center gap-2">
          <Badge
            variant={isRunning ? 'default' : 'secondary'}
            className={isRunning ? 'bg-green-500 hover:bg-green-600' : ''}
          >
            {executionStatus?.state || 'idle'}
          </Badge>
          {isRunning && executionStatus && (
            <span className="text-sm text-muted-foreground">
              {executionStatus.progress.running} running / {executionStatus.progress.completed} done
            </span>
          )}
        </div>

        {/* Queue Stats */}
        {queueStats && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>{queueStats.pending} pending</span>
            <span className="text-muted-foreground/50">|</span>
            <span>{queueStats.running} running</span>
            <span className="text-muted-foreground/50">|</span>
            <span>{queueStats.complete} complete</span>
            {queueStats.failed > 0 && (
              <>
                <span className="text-muted-foreground/50">|</span>
                <span className="text-red-500">{queueStats.failed} failed</span>
              </>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        {/* Create Task */}
        <Button onClick={onCreateTask} size="sm">
          <Plus className="mr-1 h-4 w-4" />
          Add Task
        </Button>

        {/* Start/Stop Execution */}
        {!isRunning ? (
          <div className="flex">
            {/* Main Start button - starts with 3 workers */}
            <Button
              variant="default"
              size="sm"
              disabled={isStarting || (queueStats?.pending === 0 && queueStats?.ready === 0)}
              className="bg-green-600 hover:bg-green-700 rounded-r-none"
              onClick={() => handleStart(3)}
            >
              {isStarting ? (
                <Spinner className="mr-1 h-4 w-4" />
              ) : (
                <Play className="mr-1 h-4 w-4" />
              )}
              Start
            </Button>
            {/* Dropdown for worker count options */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="default"
                  size="sm"
                  disabled={isStarting || (queueStats?.pending === 0 && queueStats?.ready === 0)}
                  className="bg-green-600 hover:bg-green-700 rounded-l-none border-l border-green-700 px-2"
                >
                  <ChevronDown className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleStart(1)}>
                  Start with 1 worker
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleStart(2)}>
                  Start with 2 workers
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleStart(3)}>
                  Start with 3 workers
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => handleStart(5)}>
                  Start with 5 workers
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ) : (
          <Button
            variant="destructive"
            size="sm"
            onClick={handleStop}
            disabled={isStopping || isStopping_}
          >
            {isStopping || isStopping_ ? (
              <Spinner className="mr-1 h-4 w-4" />
            ) : (
              <Square className="mr-1 h-4 w-4" />
            )}
            Stop
          </Button>
        )}

        {/* Refresh */}
        <Button
          variant="outline"
          size="icon"
          onClick={handleRefresh}
          disabled={isRefreshing}
        >
          {isRefreshing ? (
            <Spinner className="h-4 w-4" />
          ) : (
            <RefreshCw className="h-4 w-4" />
          )}
        </Button>

        {/* More Actions */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon">
              <Settings className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear Completed
                </DropdownMenuItem>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Clear completed tasks?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will remove all completed and failed tasks from the queue.
                    This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={() => handleClear(false)}>
                    Clear Completed
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <DropdownMenuSeparator />
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <DropdownMenuItem
                  onSelect={(e) => e.preventDefault()}
                  className="text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Clear All Tasks
                </DropdownMenuItem>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Clear ALL tasks?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will remove ALL tasks including running ones.
                    This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => handleClear(true)}
                    className="bg-destructive hover:bg-destructive/90"
                  >
                    Clear All
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

export default QuickActionsBar;
