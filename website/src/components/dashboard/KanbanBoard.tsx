/**
 * KanbanBoard component.
 * Main container for the task Kanban board with drag-and-drop support.
 */

import { useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCenter,
} from "@dnd-kit/core";
import { useState } from "react";
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area";
import { KanbanColumn } from "./KanbanColumn";
import { TaskCard } from "./TaskCard";
import type { Task, TaskStatus } from "@/types/task";
import { KANBAN_COLUMNS } from "@/types/task";

interface KanbanBoardProps {
  tasks: Task[];
  onEditTask?: (task: Task) => void;
  onDeleteTask?: (taskId: string) => void;
  onStatusChange?: (taskId: string, status: string) => void;
  onTaskClick?: (task: Task) => void;
  onApproveTask?: (taskId: string) => void;
  onApproveMerge?: (taskId: string) => void;
  selectedIds?: Set<string>;
  onSelectTask?: (taskId: string) => void;
  selectionMode?: boolean;
}

// Map column IDs to their primary status for dropping
const COLUMN_TO_STATUS: Record<string, TaskStatus> = {
  backlog: "pending",
  ready: "ready",
  "in-progress": "running",
  done: "complete",
};

export function KanbanBoard({
  tasks,
  onEditTask,
  onDeleteTask,
  onStatusChange,
  onTaskClick,
  onApproveTask,
  onApproveMerge,
  selectedIds = new Set(),
  onSelectTask,
  selectionMode = false,
}: KanbanBoardProps) {
  const [activeTask, setActiveTask] = useState<Task | null>(null);

  // Configure sensors - require 8px movement before drag starts
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  const handleDragStart = useCallback(
    (event: DragStartEvent) => {
      const { active } = event;
      const task = tasks.find(t => t.id === active.id);
      if (task) {
        setActiveTask(task);
      }
    },
    [tasks]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveTask(null);

      if (!over || !onStatusChange) return;

      const taskId = active.id as string;
      const columnId = over.id as string;

      // Get the target status for this column
      const targetStatus = COLUMN_TO_STATUS[columnId];
      if (!targetStatus) return;

      // Find the task to check its current status
      const task = tasks.find(t => t.id === taskId);
      if (!task || task.status === targetStatus) return;

      // Update the task status
      onStatusChange(taskId, targetStatus);
    },
    [tasks, onStatusChange]
  );

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
    >
      <ScrollArea className="w-full">
        <div className="flex gap-4 p-4 min-h-[calc(100vh-200px)]">
          {KANBAN_COLUMNS.map(column => (
            <KanbanColumn
              key={column.id}
              column={column}
              tasks={tasks}
              onEditTask={onEditTask}
              onDeleteTask={onDeleteTask}
              onStatusChange={onStatusChange}
              onTaskClick={onTaskClick}
              onApproveTask={onApproveTask}
              onApproveMerge={onApproveMerge}
              selectedIds={selectedIds}
              onSelectTask={onSelectTask}
              selectionMode={selectionMode}
            />
          ))}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>

      {/* Drag overlay - shows the card being dragged */}
      <DragOverlay>
        {activeTask ? (
          <div className="opacity-90 rotate-3 scale-105">
            <TaskCard task={activeTask} isDragging />
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  );
}

export default KanbanBoard;
