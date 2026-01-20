/**
 * KanbanColumn component.
 * Displays a column of tasks in the Kanban board with drop zone support.
 */

import { useDroppable } from "@dnd-kit/core";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { TaskCard } from "./TaskCard";
import { Inbox, Sparkles, Loader2, CheckCircle2 } from "lucide-react";
import type { Task, KanbanColumn as KanbanColumnType } from "@/types/task";

interface EmptyColumnStateProps {
  columnId: string;
}

const EMPTY_STATES: Record<
  string,
  { icon: React.ReactNode; title: string; description: string }
> = {
  backlog: {
    icon: <Inbox className="h-8 w-8 text-muted-foreground/50" />,
    title: "No pending tasks",
    description: "Create a task with + Add Task or import from PRD",
  },
  ready: {
    icon: <Sparkles className="h-8 w-8 text-blue-400/50" />,
    title: "Ready queue empty",
    description: "Approve tasks from Backlog to move them here",
  },
  "in-progress": {
    icon: <Loader2 className="h-8 w-8 text-amber-400/50" />,
    title: "Nothing running",
    description: "Click Start to begin processing ready tasks",
  },
  done: {
    icon: <CheckCircle2 className="h-8 w-8 text-emerald-400/50" />,
    title: "No completed tasks yet",
    description: "Completed tasks will appear here",
  },
};

function EmptyColumnState({ columnId }: EmptyColumnStateProps) {
  const state = EMPTY_STATES[columnId] || EMPTY_STATES.backlog;

  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
      {state.icon}
      <p className="mt-3 text-sm font-medium text-muted-foreground">
        {state.title}
      </p>
      <p className="mt-1 text-xs text-muted-foreground/70">
        {state.description}
      </p>
    </div>
  );
}

interface KanbanColumnProps {
  column: KanbanColumnType;
  tasks: Task[];
  onEditTask?: (task: Task) => void;
  onDeleteTask?: (taskId: string) => void;
  onStatusChange?: (taskId: string, status: string) => void;
  onTaskClick?: (task: Task) => void;
  onApproveTask?: (taskId: string) => void;
  onApproveMerge?: (taskId: string) => void;
  onCancelTask?: (taskId: string) => void;
  selectedIds?: Set<string>;
  onSelectTask?: (taskId: string) => void;
  selectionMode?: boolean;
}

export function KanbanColumn({
  column,
  tasks,
  onEditTask,
  onDeleteTask,
  onStatusChange,
  onTaskClick,
  onApproveTask,
  onApproveMerge,
  onCancelTask,
  selectedIds = new Set(),
  onSelectTask,
  selectionMode = false,
}: KanbanColumnProps) {
  // Set up droppable zone
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  // Filter tasks for this column
  const columnTasks = tasks.filter(task => {
    if (!column.statuses.includes(task.status)) {
      return false;
    }
    if (column.filter) {
      return column.filter(task);
    }
    return true;
  });

  // Sort tasks by priority (P0 first) then by status for done column
  const sortedTasks = [...columnTasks].sort((a, b) => {
    const priorityOrder = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };
    const statusOrder = {
      pending_merge: 0,
      failed: 1,
      complete: 2,
      cancelled: 3,
    };

    // For done column, sort by status first (needs review at top)
    if (column.id === "done") {
      const statusDiff =
        (statusOrder[a.status as keyof typeof statusOrder] ?? 99) -
        (statusOrder[b.status as keyof typeof statusOrder] ?? 99);
      if (statusDiff !== 0) return statusDiff;
    }

    return priorityOrder[a.priority] - priorityOrder[b.priority];
  });

  // Get column header style based on column type
  const getHeaderStyle = () => {
    switch (column.id) {
      case "backlog":
        return "bg-slate-100 dark:bg-slate-800/50";
      case "ready":
        return "bg-blue-50 dark:bg-blue-950/50";
      case "in-progress":
        return "bg-amber-50 dark:bg-amber-950/50";
      case "done":
        return "bg-emerald-50 dark:bg-emerald-950/50";
      default:
        return "bg-muted";
    }
  };

  // Count sub-statuses for done column
  const getSubStatusCounts = () => {
    if (column.id !== "done") return null;
    const counts = {
      complete: columnTasks.filter(t => t.status === "complete").length,
      pending_merge: columnTasks.filter(t => t.status === "pending_merge")
        .length,
      failed: columnTasks.filter(t => t.status === "failed").length,
    };
    return counts;
  };

  const subStatusCounts = getSubStatusCounts();

  return (
    <div
      ref={setNodeRef}
      className={`flex flex-col h-full min-w-[300px] w-[300px] flex-shrink-0 bg-muted/20 rounded-lg border transition-colors ${
        isOver
          ? "border-primary border-2 bg-primary/5"
          : "border-border/50"
      }`}
    >
      {/* Column Header */}
      <div className={`p-3 rounded-t-lg ${getHeaderStyle()}`}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm">{column.title}</h3>
          <Badge variant="secondary" className="text-xs">
            {columnTasks.length}
          </Badge>
        </div>
        {/* Sub-status badges for Done column */}
        {subStatusCounts &&
          (subStatusCounts.pending_merge > 0 || subStatusCounts.failed > 0) && (
            <div className="flex gap-1.5 mt-2">
              {subStatusCounts.pending_merge > 0 && (
                <Badge
                  variant="outline"
                  className="text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border-purple-300"
                >
                  {subStatusCounts.pending_merge} review
                </Badge>
              )}
              {subStatusCounts.failed > 0 && (
                <Badge
                  variant="outline"
                  className="text-xs bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 border-red-300"
                >
                  {subStatusCounts.failed} failed
                </Badge>
              )}
            </div>
          )}
      </div>

      {/* Column Content */}
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-2">
          {sortedTasks.length === 0 ? (
            <EmptyColumnState columnId={column.id} />
          ) : (
            sortedTasks.map(task => (
              <TaskCard
                key={task.id}
                task={task}
                onEdit={onEditTask}
                onDelete={onDeleteTask}
                onStatusChange={onStatusChange}
                onClick={onTaskClick}
                onApprove={onApproveTask}
                onApproveMerge={onApproveMerge}
                onCancel={onCancelTask}
                isCompact={column.id === "done" && task.status === "complete"}
                allTasks={tasks}
                isSelected={selectedIds.has(task.id)}
                onSelect={onSelectTask}
                selectionMode={selectionMode}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

export default KanbanColumn;
