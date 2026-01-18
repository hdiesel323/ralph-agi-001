/**
 * KanbanBoard component.
 * Main container for the task Kanban board.
 */

import { ScrollArea, ScrollBar } from '@/components/ui/scroll-area';
import { KanbanColumn } from './KanbanColumn';
import type { Task } from '@/types/task';
import { KANBAN_COLUMNS } from '@/types/task';

interface KanbanBoardProps {
  tasks: Task[];
  onEditTask?: (task: Task) => void;
  onDeleteTask?: (taskId: string) => void;
  onStatusChange?: (taskId: string, status: string) => void;
}

export function KanbanBoard({
  tasks,
  onEditTask,
  onDeleteTask,
  onStatusChange,
}: KanbanBoardProps) {
  return (
    <ScrollArea className="w-full">
      <div className="flex gap-4 p-4 min-h-[calc(100vh-200px)]">
        {KANBAN_COLUMNS.map((column) => (
          <KanbanColumn
            key={column.id}
            column={column}
            tasks={tasks}
            onEditTask={onEditTask}
            onDeleteTask={onDeleteTask}
            onStatusChange={onStatusChange}
          />
        ))}
      </div>
      <ScrollBar orientation="horizontal" />
    </ScrollArea>
  );
}

export default KanbanBoard;
