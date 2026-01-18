/**
 * KanbanColumn component.
 * Displays a column of tasks in the Kanban board.
 */

import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { TaskCard } from './TaskCard';
import type { Task, KanbanColumn as KanbanColumnType } from '@/types/task';

interface KanbanColumnProps {
  column: KanbanColumnType;
  tasks: Task[];
  onEditTask?: (task: Task) => void;
  onDeleteTask?: (taskId: string) => void;
  onStatusChange?: (taskId: string, status: string) => void;
  onTaskClick?: (task: Task) => void;
  onApproveTask?: (taskId: string) => void;
  onApproveMerge?: (taskId: string) => void;
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
}: KanbanColumnProps) {
  // Filter tasks for this column
  const columnTasks = tasks.filter((task) => {
    // First check if task status matches column
    if (!column.statuses.includes(task.status)) {
      return false;
    }
    // Then apply any additional filter
    if (column.filter) {
      return column.filter(task);
    }
    return true;
  });

  // Get column header style based on column type
  const getHeaderStyle = () => {
    switch (column.id) {
      case 'backlog':
        return 'bg-gray-100 dark:bg-gray-800';
      case 'needs-approval':
        return 'bg-orange-50 dark:bg-orange-950';
      case 'ready':
        return 'bg-blue-50 dark:bg-blue-950';
      case 'running':
        return 'bg-yellow-50 dark:bg-yellow-950';
      case 'needs-review':
        return 'bg-purple-50 dark:bg-purple-950';
      case 'done':
        return 'bg-green-50 dark:bg-green-950';
      default:
        return 'bg-muted';
    }
  };

  return (
    <div className="flex flex-col h-full min-w-[280px] max-w-[320px] bg-muted/30 rounded-lg">
      {/* Column Header */}
      <div className={`p-3 rounded-t-lg ${getHeaderStyle()}`}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-sm">{column.title}</h3>
          <Badge variant="secondary" className="text-xs">
            {columnTasks.length}
          </Badge>
        </div>
      </div>

      {/* Column Content */}
      <ScrollArea className="flex-1 p-2">
        <div className="space-y-2">
          {columnTasks.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              No tasks
            </div>
          ) : (
            columnTasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onEdit={onEditTask}
                onDelete={onDeleteTask}
                onStatusChange={onStatusChange}
                onClick={onTaskClick}
                onApprove={onApproveTask}
                onApproveMerge={onApproveMerge}
              />
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

export default KanbanColumn;
