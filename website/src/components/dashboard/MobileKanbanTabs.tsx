/**
 * MobileKanbanTabs component.
 * Tab-based Kanban view optimized for mobile with swipe gestures.
 */

import { useState, useCallback, useRef, TouchEvent } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TaskCard } from "./TaskCard";
import type { Task, KanbanColumn as KanbanColumnType } from "@/types/task";
import { KANBAN_COLUMNS, PRIORITY_CONFIG } from "@/types/task";

interface MobileKanbanTabsProps {
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

function getTasksForColumn(tasks: Task[], column: KanbanColumnType): Task[] {
  return tasks
    .filter(task => {
      if (!column.statuses.includes(task.status)) return false;
      if (column.filter) return column.filter(task);
      return true;
    })
    .sort((a, b) => {
      const priorityOrder: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
}

export function MobileKanbanTabs({
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
}: MobileKanbanTabsProps) {
  const [activeTab, setActiveTab] = useState("backlog");
  const touchStartX = useRef<number>(0);
  const touchEndX = useRef<number>(0);

  const columnOrder = KANBAN_COLUMNS.map(c => c.id);

  const handleTouchStart = useCallback((e: TouchEvent) => {
    touchStartX.current = e.targetTouches[0].clientX;
  }, []);

  const handleTouchMove = useCallback((e: TouchEvent) => {
    touchEndX.current = e.targetTouches[0].clientX;
  }, []);

  const handleTouchEnd = useCallback(() => {
    const diff = touchStartX.current - touchEndX.current;
    const threshold = 50;

    if (Math.abs(diff) < threshold) return;

    const currentIndex = columnOrder.indexOf(activeTab);

    if (diff > 0 && currentIndex < columnOrder.length - 1) {
      // Swipe left - go to next tab
      setActiveTab(columnOrder[currentIndex + 1]);
    } else if (diff < 0 && currentIndex > 0) {
      // Swipe right - go to previous tab
      setActiveTab(columnOrder[currentIndex - 1]);
    }
  }, [activeTab, columnOrder]);

  return (
    <Tabs
      value={activeTab}
      onValueChange={setActiveTab}
      className="flex flex-col h-full"
    >
      <TabsList className="grid grid-cols-4 mx-4 mt-2">
        {KANBAN_COLUMNS.map(column => {
          const count = getTasksForColumn(tasks, column).length;
          return (
            <TabsTrigger
              key={column.id}
              value={column.id}
              className="text-xs px-1 py-1.5 relative"
            >
              <span className="truncate">{column.title.split(" ")[0]}</span>
              {count > 0 && (
                <Badge
                  variant="secondary"
                  className="ml-1 h-5 w-5 p-0 text-[10px] flex items-center justify-center"
                >
                  {count}
                </Badge>
              )}
            </TabsTrigger>
          );
        })}
      </TabsList>

      <div
        className="flex-1 overflow-hidden"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {KANBAN_COLUMNS.map(column => {
          const columnTasks = getTasksForColumn(tasks, column);

          return (
            <TabsContent
              key={column.id}
              value={column.id}
              className="h-full m-0 p-0"
            >
              <ScrollArea className="h-full p-4">
                {columnTasks.length === 0 ? (
                  <div className="flex flex-col items-center justify-center py-12 text-center">
                    <p className="text-sm text-muted-foreground">
                      No tasks in {column.title.toLowerCase()}
                    </p>
                    <p className="text-xs text-muted-foreground/70 mt-1">
                      Swipe left/right to switch columns
                    </p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {columnTasks.map(task => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        onEdit={onEditTask}
                        onDelete={onDeleteTask}
                        onStatusChange={onStatusChange}
                        onClick={onTaskClick}
                        onApprove={onApproveTask}
                        onApproveMerge={onApproveMerge}
                        isCompact={column.id === "done" && task.status === "complete"}
                        allTasks={tasks}
                        isSelected={selectedIds.has(task.id)}
                        onSelect={onSelectTask}
                        selectionMode={selectionMode}
                      />
                    ))}
                  </div>
                )}
              </ScrollArea>
            </TabsContent>
          );
        })}
      </div>

      {/* Swipe indicator */}
      <div className="flex justify-center gap-1.5 py-2">
        {columnOrder.map((id, index) => (
          <div
            key={id}
            className={`h-1.5 rounded-full transition-all ${
              activeTab === id
                ? "w-4 bg-primary"
                : "w-1.5 bg-muted-foreground/30"
            }`}
          />
        ))}
      </div>
    </Tabs>
  );
}

export default MobileKanbanTabs;
