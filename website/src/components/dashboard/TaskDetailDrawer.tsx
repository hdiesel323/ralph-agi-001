/**
 * TaskDetailDrawer component - Shows full task details in a side drawer.
 */

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  ExternalLink,
  GitBranch,
  Clock,
  CheckCircle,
  XCircle,
  FolderGit2,
  CalendarClock,
  AlertCircle,
  Play,
  Merge,
  ChevronDown,
  ChevronUp,
  FileOutput,
} from "lucide-react";
import { useState } from "react";
import type { Task, RepoContext } from "@/types/task";
import { PRIORITY_CONFIG, STATUS_CONFIG } from "@/types/task";
import { TaskResults } from "./TaskResults";

interface TaskDetailDrawerProps {
  task: Task | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  repoContext?: RepoContext | null;
  onApprove?: (taskId: string) => void;
  onApproveMerge?: (taskId: string) => void;
  onEdit?: (task: Task) => void;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return "-";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(
  started: string | null,
  completed: string | null
): string | null {
  if (!started) return null;
  const start = new Date(started);
  const end = completed ? new Date(completed) : new Date();
  const seconds = Math.floor((end.getTime() - start.getTime()) / 1000);

  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export function TaskDetailDrawer({
  task,
  open,
  onOpenChange,
  repoContext,
  onApprove,
  onApproveMerge,
  onEdit,
}: TaskDetailDrawerProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  if (!task) return null;

  const priorityConfig = PRIORITY_CONFIG[task.priority];
  const statusConfig = STATUS_CONFIG[task.status];
  const duration = formatDuration(task.started_at, task.completed_at);

  const canApprove =
    task.status === "pending" || task.status === "pending_approval";
  const canMerge = task.status === "pending_merge";
  const isCompleted = ["complete", "failed", "pending_merge"].includes(task.status);
  const hasOutput = task.output !== null;

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader>
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={`${priorityConfig.color} text-white text-xs px-2`}
            >
              {task.priority}
            </Badge>
            <span className={`text-sm ${statusConfig.color}`}>
              {statusConfig.icon} {statusConfig.label}
            </span>
          </div>
          <SheetTitle className="text-lg">{task.description}</SheetTitle>
          <SheetDescription className="text-xs text-muted-foreground">
            ID: {task.id}
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-4 py-4">
          {/* PR Link - Prominent */}
          {task.pr_url && (
            <div className="rounded-lg border bg-muted/50 p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <GitBranch className="h-5 w-5 text-primary" />
                  <span className="font-medium">Pull Request</span>
                </div>
                <Button asChild>
                  <a
                    href={task.pr_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View PR #{task.pr_number || ""}
                  </a>
                </Button>
              </div>
            </div>
          )}

          {/* Task Results - Show for completed tasks */}
          {(isCompleted || hasOutput) && (
            <div className="space-y-3">
              <h4 className="text-sm font-medium flex items-center gap-2">
                <FileOutput className="h-4 w-4" />
                Execution Results
              </h4>
              <TaskResults output={task.output} worktreePath={task.worktree_path} />
            </div>
          )}

          {(isCompleted || hasOutput) && <Separator />}

          {/* Git Context */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <FolderGit2 className="h-4 w-4" />
              Git Context
            </h4>
            <div className="rounded-lg border p-3 space-y-2 text-sm">
              {repoContext && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Repository</span>
                  <span className="font-mono">{repoContext.name}</span>
                </div>
              )}
              {task.branch && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Branch</span>
                  <span className="font-mono text-xs">{task.branch}</span>
                </div>
              )}
              {task.worktree_path && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Worktree</span>
                  <span
                    className="font-mono text-xs truncate max-w-[200px]"
                    title={task.worktree_path}
                  >
                    {task.worktree_path}
                  </span>
                </div>
              )}
              {!task.branch && !task.worktree_path && (
                <span className="text-muted-foreground text-xs">
                  Not yet assigned
                </span>
              )}
            </div>
          </div>

          <Separator />

          {/* Timeline */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <CalendarClock className="h-4 w-4" />
              Timeline
            </h4>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Created
                </span>
                <span>{formatDate(task.created_at)}</span>
              </div>
              {task.started_at && (
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground flex items-center gap-1">
                    <Play className="h-3 w-3" />
                    Started
                  </span>
                  <span>{formatDate(task.started_at)}</span>
                </div>
              )}
              {task.completed_at && (
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground flex items-center gap-1">
                    {task.status === "complete" ? (
                      <CheckCircle className="h-3 w-3 text-green-500" />
                    ) : (
                      <XCircle className="h-3 w-3 text-red-500" />
                    )}
                    Completed
                  </span>
                  <span>{formatDate(task.completed_at)}</span>
                </div>
              )}
              {duration && (
                <div className="flex justify-between items-center">
                  <span className="text-muted-foreground">Duration</span>
                  <Badge variant="secondary">{duration}</Badge>
                </div>
              )}
            </div>
          </div>

          <Separator />

          {/* Confidence Score */}
          {task.confidence !== null && (
            <>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">Confidence Score</span>
                  <span
                    className={
                      task.confidence >= 0.9
                        ? "text-green-500"
                        : task.confidence >= 0.7
                          ? "text-yellow-500"
                          : "text-red-500"
                    }
                  >
                    {(task.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                <Progress value={task.confidence * 100} className="h-2" />
              </div>
              <Separator />
            </>
          )}

          {/* Acceptance Criteria */}
          {task.acceptance_criteria.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Acceptance Criteria</h4>
              <ul className="space-y-1 text-sm">
                {task.acceptance_criteria.map((criteria, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-muted-foreground">-</span>
                    <span>{criteria}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Dependencies */}
          {task.dependencies.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium">Dependencies</h4>
              <div className="flex flex-wrap gap-1">
                {task.dependencies.map(depId => (
                  <Badge key={depId} variant="outline" className="text-xs">
                    {depId}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {task.error && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium flex items-center gap-2 text-destructive">
                <AlertCircle className="h-4 w-4" />
                Error
              </h4>
              <div className="rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
                {task.error}
              </div>
            </div>
          )}
        </div>

        <SheetFooter className="gap-2">
          {canApprove && onApprove && (
            <Button onClick={() => onApprove(task.id)} className="flex-1">
              <Play className="mr-2 h-4 w-4" />
              Approve for Execution
            </Button>
          )}
          {canMerge && onApproveMerge && (
            <Button onClick={() => onApproveMerge(task.id)} className="flex-1">
              <Merge className="mr-2 h-4 w-4" />
              Approve Merge
            </Button>
          )}
          {onEdit && !canApprove && !canMerge && (
            <Button variant="outline" onClick={() => onEdit(task)}>
              Edit Task
            </Button>
          )}
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

export default TaskDetailDrawer;
