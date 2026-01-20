/**
 * TaskCard component for Kanban board.
 * Displays a single task as a draggable card.
 */

import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Progress } from "@/components/ui/progress";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  MoreVertical,
  ExternalLink,
  GitBranch,
  Clock,
  Trash2,
  Edit,
  Play,
  Merge,
  Lock,
  Unlock,
  Square,
  RefreshCw,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { Task, TaskPriority } from "@/types/task";
import { PRIORITY_CONFIG, STATUS_CONFIG } from "@/types/task";

interface TaskCardProps {
  task: Task;
  onEdit?: (task: Task) => void;
  onDelete?: (taskId: string) => void;
  onStatusChange?: (taskId: string, status: string) => void;
  onClick?: (task: Task) => void;
  onApprove?: (taskId: string) => void;
  onApproveMerge?: (taskId: string) => void;
  onCancel?: (taskId: string) => void;
  isDragging?: boolean;
  isCompact?: boolean;
  allTasks?: Task[];
  isSelected?: boolean;
  onSelect?: (taskId: string) => void;
  selectionMode?: boolean;
}

function formatDate(dateString: string | null): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
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
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

export function TaskCard({
  task,
  onEdit,
  onDelete,
  onStatusChange,
  onClick,
  onApprove,
  onApproveMerge,
  onCancel,
  isDragging,
  isCompact,
  allTasks = [],
  isSelected = false,
  onSelect,
  selectionMode = false,
}: TaskCardProps) {
  // Set up draggable - skip for compact mode
  const { attributes, listeners, setNodeRef, transform } = useDraggable({
    id: task.id,
    disabled: isCompact,
  });

  const style = transform
    ? {
        transform: CSS.Translate.toString(transform),
      }
    : undefined;

  const priorityConfig = PRIORITY_CONFIG[task.priority];
  const statusConfig = STATUS_CONFIG[task.status];
  const duration = formatDuration(task.started_at, task.completed_at);

  // Check if task is blocked by incomplete dependencies
  const blockedBy = task.dependencies.filter(depId => {
    const depTask = allTasks.find(t => t.id === depId);
    return depTask && depTask.status !== "complete";
  });
  const isBlocked = blockedBy.length > 0;

  const canApprove =
    (task.status === "pending" || task.status === "pending_approval") &&
    onApprove;
  const canMerge = task.status === "pending_merge" && onApproveMerge;

  const handleCardClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button, [role="menuitem"], a, [role="checkbox"]')) {
      return;
    }
    // If in selection mode, toggle selection instead of opening detail
    if (selectionMode && onSelect) {
      onSelect(task.id);
      return;
    }
    onClick?.(task);
  };

  const handleCheckboxChange = () => {
    onSelect?.(task.id);
  };

  // Priority-based left border styles
  const getPriorityBorderStyle = () => {
    switch (task.priority) {
      case "P0":
        return "border-l-4 border-l-red-500";
      case "P1":
        return "border-l-4 border-l-orange-500";
      case "P2":
        return "border-l-[3px] border-l-yellow-500";
      case "P3":
        return "border-l-2 border-l-blue-500";
      case "P4":
        return "border-l-2 border-l-gray-400";
      default:
        return "border-l-2 border-l-gray-400";
    }
  };

  // Status-based styles
  const getStatusStyle = () => {
    if (task.status === "running")
      return "ring-2 ring-amber-400 ring-offset-1 animate-pulse";
    if (task.status === "pending_approval")
      return "ring-2 ring-orange-400 ring-offset-1";
    if (task.status === "pending_merge")
      return "ring-2 ring-purple-400 ring-offset-1";
    if (task.status === "failed")
      return "opacity-75 bg-red-50 dark:bg-red-950/20";
    if (task.status === "complete") return "opacity-60";
    return "";
  };

  // Compact mode for completed tasks
  if (isCompact) {
    return (
      <Card
        className={`mb-2 cursor-pointer transition-all hover:opacity-100 ${getPriorityBorderStyle()} ${getStatusStyle()}`}
        onClick={handleCardClick}
      >
        <div className="px-3 py-2 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <span className="text-green-500 flex-shrink-0">✓</span>
            <span className="text-sm truncate text-muted-foreground">
              {task.description}
            </span>
          </div>
          {duration && (
            <span className="text-xs text-muted-foreground flex-shrink-0">
              {duration}
            </span>
          )}
        </div>
      </Card>
    );
  }

  return (
    <Card
      ref={setNodeRef}
      style={style}
      className={`mb-2 cursor-grab transition-all hover:shadow-md ${getPriorityBorderStyle()} ${getStatusStyle()} ${
        isDragging ? "opacity-50 shadow-lg cursor-grabbing" : ""
      } ${isSelected ? "ring-2 ring-primary ring-offset-1" : ""}`}
      onClick={handleCardClick}
      {...listeners}
      {...attributes}
    >
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          {/* Selection checkbox */}
          {(selectionMode || isSelected) && (
            <Checkbox
              checked={isSelected}
              onCheckedChange={handleCheckboxChange}
              className="mt-0.5 flex-shrink-0"
            />
          )}
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-medium truncate">
              {task.description}
            </CardTitle>
            <CardDescription className="text-xs mt-1">
              <span className={statusConfig.color}>
                {statusConfig.icon} {statusConfig.label}
              </span>
              {duration && (
                <span className="ml-2 text-muted-foreground">
                  <Clock className="inline-block w-3 h-3 mr-1" />
                  {duration}
                </span>
              )}
            </CardDescription>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon-sm" className="h-6 w-6">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {onEdit && (
                <DropdownMenuItem onClick={() => onEdit(task)}>
                  <Edit className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
              )}
              {task.status === "ready" && onStatusChange && (
                <DropdownMenuItem
                  onClick={() => onStatusChange(task.id, "running")}
                >
                  Start Task
                </DropdownMenuItem>
              )}
              {task.status === "running" && onStatusChange && (
                <>
                  <DropdownMenuItem
                    onClick={() => onStatusChange(task.id, "pending_merge")}
                  >
                    Mark Complete
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onStatusChange(task.id, "failed")}
                  >
                    Mark Failed
                  </DropdownMenuItem>
                </>
              )}
              {task.pr_url && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <a
                      href={task.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <ExternalLink className="mr-2 h-4 w-4" />
                      View PR
                    </a>
                  </DropdownMenuItem>
                </>
              )}
              {onDelete && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    onClick={() => onDelete(task.id)}
                    className="text-destructive"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge
            variant="outline"
            className={`${priorityConfig.color} text-white text-xs px-1.5 py-0`}
          >
            {task.priority}
          </Badge>

          {task.branch && (
            <Badge variant="secondary" className="text-xs px-1.5 py-0">
              <GitBranch className="w-3 h-3 mr-1" />
              {task.branch.length > 20
                ? task.branch.slice(0, 20) + "..."
                : task.branch}
            </Badge>
          )}

          {task.dependencies.length > 0 && (
            isBlocked ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="outline"
                    className="text-xs px-1.5 py-0 bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 border-amber-300"
                  >
                    <Lock className="w-3 h-3 mr-1" />
                    Blocked ({blockedBy.length})
                  </Badge>
                </TooltipTrigger>
                <TooltipContent>
                  <p className="text-xs">Waiting on: {blockedBy.join(", ")}</p>
                </TooltipContent>
              </Tooltip>
            ) : (
              <Badge variant="outline" className="text-xs px-1.5 py-0 text-green-600 border-green-300">
                <Unlock className="w-3 h-3 mr-1" />
                {task.dependencies.length} deps
              </Badge>
            )
          )}
        </div>

        {/* PR Link - Prominent display when available */}
        {task.pr_url && (
          <div className="mt-2">
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs w-full"
              asChild
            >
              <a href={task.pr_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="mr-1 h-3 w-3" />
                View PR #{task.pr_number || ""}
              </a>
            </Button>
          </div>
        )}

        {/* Iteration progress for running tasks */}
        {task.status === "running" && task.max_iterations > 0 && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-muted-foreground flex items-center gap-1">
                <RefreshCw className="w-3 h-3 animate-spin" />
                Iterations
              </span>
              <span
                className={
                  task.current_iteration / task.max_iterations >= 0.9
                    ? "text-red-500 font-medium"
                    : task.current_iteration / task.max_iterations >= 0.75
                      ? "text-orange-500"
                      : "text-muted-foreground"
                }
              >
                {task.current_iteration}/{task.max_iterations}
              </span>
            </div>
            <Progress
              value={(task.current_iteration / task.max_iterations) * 100}
              className={`h-1.5 ${
                task.current_iteration / task.max_iterations >= 0.9
                  ? "[&>div]:bg-red-500"
                  : task.current_iteration / task.max_iterations >= 0.75
                    ? "[&>div]:bg-orange-500"
                    : ""
              }`}
            />
          </div>
        )}

        {task.confidence !== null && (
          <div className="mt-3">
            <div className="flex items-center justify-between text-xs mb-1">
              <span className="text-muted-foreground">Confidence</span>
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
            <Progress value={task.confidence * 100} className="h-1.5" />
          </div>
        )}

        {task.error && (
          <div className="mt-2 p-2 bg-destructive/10 rounded text-xs text-destructive">
            {task.error.length > 100
              ? task.error.slice(0, 100) + "..."
              : task.error}
          </div>
        )}

        {task.acceptance_criteria.length > 0 && (
          <div className="mt-2 text-xs text-muted-foreground">
            {task.acceptance_criteria.length} acceptance criteria
          </div>
        )}

        {/* Approval Buttons */}
        {canApprove && (
          <div className="mt-3">
            <Button
              size="sm"
              className="h-7 text-xs w-full"
              onClick={e => {
                e.stopPropagation();
                onApprove!(task.id);
              }}
            >
              <Play className="mr-1 h-3 w-3" />
              Approve
            </Button>
          </div>
        )}

        {canMerge && (
          <div className="mt-3">
            <Button
              size="sm"
              className="h-7 text-xs w-full"
              onClick={e => {
                e.stopPropagation();
                onApproveMerge!(task.id);
              }}
            >
              <Merge className="mr-1 h-3 w-3" />
              Approve Merge
            </Button>
          </div>
        )}

        {/* Cancel button for running tasks */}
        {task.status === "running" && onCancel && (
          <div className="mt-3">
            <Button
              size="sm"
              variant="destructive"
              className="h-7 text-xs w-full"
              onClick={e => {
                e.stopPropagation();
                onCancel(task.id);
              }}
            >
              <Square className="mr-1 h-3 w-3" />
              Cancel Task
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default TaskCard;
