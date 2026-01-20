/**
 * Dashboard page.
 * Main visual control interface for RALPH-AGI.
 */

import { useState, useCallback, useMemo, useRef } from "react";
import { KanbanBoard } from "@/components/dashboard/KanbanBoard";
import { MobileKanbanTabs } from "@/components/dashboard/MobileKanbanTabs";
import { TaskEditor } from "@/components/dashboard/TaskEditor";
import { TaskDetailDrawer } from "@/components/dashboard/TaskDetailDrawer";
import { SettingsPanel } from "@/components/dashboard/SettingsPanel";
import { QuickActionsBar } from "@/components/dashboard/QuickActionsBar";
import { UnifiedStatusPanel } from "@/components/dashboard/UnifiedStatusPanel";
import { MobileFAB } from "@/components/dashboard/MobileFAB";
import { OnboardingGuide } from "@/components/dashboard/OnboardingGuide";
import { DashboardToolbar } from "@/components/dashboard/DashboardToolbar";
import { KeyboardShortcutsDialog } from "@/components/dashboard/KeyboardShortcutsDialog";
import { BulkActionsBar } from "@/components/dashboard/BulkActionsBar";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { useTasks } from "@/hooks/useTasks";
import { useExecution } from "@/hooks/useExecution";
import { useConfig } from "@/hooks/useConfig";
import { useWebSocket } from "@/hooks/useWebSocket";
import { useKeyboardShortcuts } from "@/hooks/useKeyboardShortcuts";
import { useFilterState } from "@/hooks/useFilterState";
import { useTaskSelection } from "@/hooks/useTaskSelection";
import { approveTask, approveMerge, cancelTask } from "@/api/tasks";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Wifi, WifiOff, Settings, PanelRight } from "lucide-react";
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  ConfigUpdate,
  TaskPriority,
} from "@/types/task";

export function Dashboard() {
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);

  // Filter State (persisted to URL and localStorage)
  const {
    searchTerm,
    setSearchTerm,
    priorityFilter,
    setPriorityFilter,
    showCompleted,
    setShowCompleted,
    sortBy,
    setSortBy,
  } = useFilterState();
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Selection state for bulk operations
  const {
    selectedIds,
    isSelected,
    toggle: toggleTaskSelection,
    clearSelection,
    selectCount,
    hasSelection,
  } = useTaskSelection();

  // Data hooks
  const {
    tasks,
    stats,
    loading: tasksLoading,
    error: tasksError,
    refresh: refreshTasks,
    addTask,
    editTask,
    removeTask,
    clearCompleted,
  } = useTasks({ pollingInterval: 3000 });

  const {
    status: executionStatus,
    results: executionResults,
    loading: executionLoading,
    error: executionError,
    start: startExecution,
    stop: stopExecution,
    refresh: refreshExecution,
  } = useExecution({ pollingInterval: 2000 });

  const {
    config,
    repo: repoContext,
    loading: configLoading,
    updateSettings,
  } = useConfig();

  // WebSocket for real-time updates
  const { status: wsStatus, lastEvent } = useWebSocket({
    autoConnect: true,
    onEvent: event => {
      // Refresh data when relevant events occur
      if (
        event.type.startsWith("task_") ||
        event.type.startsWith("iteration_") ||
        event.type.startsWith("loop_")
      ) {
        refreshTasks();
        refreshExecution();
      }
    },
  });

  // Handlers
  const handleCreateTask = useCallback(() => {
    setEditingTask(null);
    setIsEditorOpen(true);
  }, []);

  // Derived state: Filtered and sorted Tasks
  const filteredTasks = useMemo(() => {
    const priorityOrder: Record<string, number> = { P0: 0, P1: 1, P2: 2, P3: 3, P4: 4 };

    const filtered = tasks.filter(task => {
      // Search
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchesId = task.id.toLowerCase().includes(term);
        const matchesDesc = task.description.toLowerCase().includes(term);
        if (!matchesId && !matchesDesc) return false;
      }

      // Priority
      if (priorityFilter !== "ALL" && task.priority !== priorityFilter) {
        return false;
      }

      // Show Completed/Active
      if (!showCompleted) {
        if (["complete", "failed", "cancelled"].includes(task.status)) {
          return false;
        }
      }

      return true;
    });

    // Sort based on sortBy option
    return [...filtered].sort((a, b) => {
      switch (sortBy) {
        case "priority":
          return priorityOrder[a.priority] - priorityOrder[b.priority];
        case "created":
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case "updated":
          return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime();
        case "name":
          return a.description.localeCompare(b.description);
        default:
          return 0;
      }
    });
  }, [tasks, searchTerm, priorityFilter, showCompleted, sortBy]);

  const handleEditTask = useCallback((task: Task) => {
    setEditingTask(task);
    setIsEditorOpen(true);
  }, []);

  const handleDeleteTask = useCallback(
    async (taskId: string) => {
      await removeTask(taskId);
    },
    [removeTask]
  );

  const handleStatusChange = useCallback(
    async (taskId: string, status: string) => {
      await editTask(taskId, { status: status as TaskUpdate["status"] });
    },
    [editTask]
  );

  const handleSubmitTask = useCallback(
    async (data: TaskCreate) => {
      if (editingTask) {
        await editTask(editingTask.id, data);
      } else {
        await addTask(data);
      }
    },
    [editingTask, addTask, editTask]
  );

  const handleStart = useCallback(
    async (maxConcurrent?: number) => {
      await startExecution(maxConcurrent);
    },
    [startExecution]
  );

  const handleStop = useCallback(async () => {
    await stopExecution();
  }, [stopExecution]);

  const handleClear = useCallback(
    async (includeRunning?: boolean) => {
      await clearCompleted(includeRunning);
    },
    [clearCompleted]
  );

  const handleRefresh = useCallback(async () => {
    await Promise.all([refreshTasks(), refreshExecution()]);
  }, [refreshTasks, refreshExecution]);

  const handleTaskClick = useCallback((task: Task) => {
    setSelectedTask(task);
    setIsDetailDrawerOpen(true);
  }, []);

  const handleApproveTask = useCallback(
    async (taskId: string) => {
      await approveTask(taskId);
      await refreshTasks();
      setIsDetailDrawerOpen(false);
    },
    [refreshTasks]
  );

  const handleApproveMerge = useCallback(
    async (taskId: string) => {
      await approveMerge(taskId);
      await refreshTasks();
      setIsDetailDrawerOpen(false);
    },
    [refreshTasks]
  );

  const handleCancelTask = useCallback(
    async (taskId: string) => {
      await cancelTask(taskId);
      await refreshTasks();
    },
    [refreshTasks]
  );

  const handleUpdateSettings = useCallback(
    async (updates: ConfigUpdate) => {
      await updateSettings(updates);
    },
    [updateSettings]
  );

  // Bulk action handlers
  const handleBulkDelete = useCallback(async () => {
    const ids = Array.from(selectedIds);
    await Promise.all(ids.map(id => removeTask(id)));
    clearSelection();
  }, [selectedIds, removeTask, clearSelection]);

  const handleBulkStatusChange = useCallback(
    async (status: TaskUpdate["status"]) => {
      const ids = Array.from(selectedIds);
      await Promise.all(ids.map(id => editTask(id, { status })));
      clearSelection();
    },
    [selectedIds, editTask, clearSelection]
  );

  const handleBulkPriorityChange = useCallback(
    async (priority: TaskPriority) => {
      const ids = Array.from(selectedIds);
      await Promise.all(ids.map(id => editTask(id, { priority })));
      clearSelection();
    },
    [selectedIds, editTask, clearSelection]
  );

  // Keyboard Shortcuts (must be after all handlers are defined)
  useKeyboardShortcuts([
    {
      key: "k",
      meta: true,
      action: () => {
        searchInputRef.current?.focus();
      },
      preventDefault: true,
    },
    {
      key: "n",
      action: handleCreateTask,
    },
    {
      key: "?",
      action: () => setIsShortcutsOpen(true),
    },
    {
      key: "r",
      action: handleRefresh,
    },
    {
      key: "Enter",
      shift: true,
      action: () => {
        if (!executionStatus || executionStatus.state !== "running") {
          handleStart(3);
        }
      },
      preventDefault: true,
    },
    {
      key: "Escape",
      shift: true,
      action: handleStop,
    },
  ]);

  // Check if API is connected (error means not connected)
  const isApiConnected = !tasksError && !executionError;
  const hasAnyTasks = tasks.length > 0;
  const showOnboarding = !isApiConnected || (!hasAnyTasks && !tasksLoading);

  // Loading state (only show if we expect data)
  if (tasksLoading && executionLoading && !tasksError) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Spinner className="h-8 w-8" />
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  // Show onboarding guide when API not connected or no tasks
  if (showOnboarding) {
    return (
      <div className="min-h-screen bg-background">
        {/* Header */}
        <header className="border-b px-4 py-3 flex items-center justify-between bg-background">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold">RALPH-AGI Control</h1>
            <div className="flex items-center gap-1 text-sm text-muted-foreground">
              {wsStatus === "connected" ? (
                <>
                  <Wifi className="h-4 w-4 text-green-500" />
                  <span>Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-red-500" />
                  <span>Disconnected</span>
                </>
              )}
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings className="h-5 w-5" />
          </Button>
        </header>

        <OnboardingGuide
          isApiConnected={isApiConnected}
          isWebSocketConnected={wsStatus === "connected"}
          hasAnyTasks={hasAnyTasks}
          onRetryConnection={handleRefresh}
          onCreateTask={handleCreateTask}
          repoContext={repoContext}
        />

        {/* Task Editor Dialog (needed for onboarding) */}
        <TaskEditor
          open={isEditorOpen}
          onOpenChange={setIsEditorOpen}
          task={editingTask}
          onSubmit={handleSubmitTask}
          availableTasks={tasks}
        />

        {/* Settings Panel */}
        <SettingsPanel
          config={config}
          open={isSettingsOpen}
          onOpenChange={setIsSettingsOpen}
          onUpdateSettings={handleUpdateSettings}
          onClearTasks={handleClear}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <header className="border-b px-4 py-3 flex items-center justify-between bg-background">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">RALPH-AGI Control</h1>
          {repoContext && (
            <span className="text-sm text-muted-foreground font-mono">
              {repoContext.name}
            </span>
          )}
          <div className="flex items-center gap-1 text-sm text-muted-foreground">
            {wsStatus === "connected" ? (
              <>
                <Wifi className="h-4 w-4 text-green-500" />
                <span>Connected</span>
              </>
            ) : wsStatus === "connecting" ? (
              <>
                <Spinner className="h-4 w-4" />
                <span>Connecting...</span>
              </>
            ) : (
              <>
                <WifiOff className="h-4 w-4 text-red-500" />
                <span>Disconnected</span>
              </>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1">
          {/* Mobile sidebar toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSidebarOpen(true)}
            className="md:hidden"
          >
            <PanelRight className="h-5 w-5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSettingsOpen(true)}
          >
            <Settings className="h-5 w-5" />
          </Button>
        </div>
      </header>

      {/* Quick Actions Bar */}
      <QuickActionsBar
        executionStatus={executionStatus}
        queueStats={stats}
        onStart={handleStart}
        onStop={handleStop}
        onClear={handleClear}
        onRefresh={handleRefresh}
        onCreateTask={handleCreateTask}
      />

      <DashboardToolbar
        searchTerm={searchTerm}
        onSearchChange={setSearchTerm}
        priorityFilter={priorityFilter}
        onPriorityFilterChange={setPriorityFilter}
        showCompleted={showCompleted}
        onShowCompletedChange={setShowCompleted}
        sortBy={sortBy}
        onSortChange={setSortBy}
        totalTasks={tasks.length}
        filteredCount={filteredTasks.length}
        inputRef={searchInputRef}
      />

      {/* Bulk Actions Bar */}
      <BulkActionsBar
        selectedCount={selectCount}
        onClearSelection={clearSelection}
        onBulkDelete={handleBulkDelete}
        onBulkStatusChange={handleBulkStatusChange}
        onBulkPriorityChange={handleBulkPriorityChange}
      />

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Kanban Board - Desktop */}
        <div className="hidden md:flex flex-1 overflow-auto">
          <KanbanBoard
            tasks={filteredTasks}
            onEditTask={handleEditTask}
            onDeleteTask={handleDeleteTask}
            onStatusChange={handleStatusChange}
            onTaskClick={handleTaskClick}
            onApproveTask={handleApproveTask}
            onApproveMerge={handleApproveMerge}
            onCancelTask={handleCancelTask}
            selectedIds={selectedIds}
            onSelectTask={toggleTaskSelection}
            selectionMode={hasSelection}
          />
        </div>

        {/* Mobile Kanban Tabs - with swipe gestures */}
        <div className="flex md:hidden flex-1 overflow-hidden">
          <MobileKanbanTabs
            tasks={filteredTasks}
            onEditTask={handleEditTask}
            onDeleteTask={handleDeleteTask}
            onStatusChange={handleStatusChange}
            onTaskClick={handleTaskClick}
            onApproveTask={handleApproveTask}
            onApproveMerge={handleApproveMerge}
            onCancelTask={handleCancelTask}
            selectedIds={selectedIds}
            onSelectTask={toggleTaskSelection}
            selectionMode={hasSelection}
          />
        </div>

        {/* Sidebar - Desktop: always visible, Mobile: hidden */}
        <div className="hidden md:block w-80 border-l p-4 overflow-auto bg-muted/10">
          <UnifiedStatusPanel
            executionStatus={executionStatus}
            pollingInterval={2000}
          />
        </div>

        {/* Sidebar - Mobile: Sheet overlay */}
        <Sheet open={isSidebarOpen} onOpenChange={setIsSidebarOpen}>
          <SheetContent side="right" className="w-80 p-4 md:hidden">
            <UnifiedStatusPanel
              executionStatus={executionStatus}
              pollingInterval={2000}
            />
          </SheetContent>
        </Sheet>
      </div>

      {/* Mobile FAB */}
      <MobileFAB
        executionStatus={executionStatus}
        onStart={() => handleStart(3)}
        onStop={handleStop}
        onRefresh={handleRefresh}
        onCreateTask={handleCreateTask}
        disabled={stats?.pending === 0 && stats?.ready === 0}
      />

      {/* Task Editor Dialog */}
      <TaskEditor
        open={isEditorOpen}
        onOpenChange={setIsEditorOpen}
        task={editingTask}
        onSubmit={handleSubmitTask}
        availableTasks={tasks}
      />

      {/* Task Detail Drawer */}
      <TaskDetailDrawer
        task={selectedTask}
        open={isDetailDrawerOpen}
        onOpenChange={setIsDetailDrawerOpen}
        repoContext={repoContext}
        onApprove={handleApproveTask}
        onApproveMerge={handleApproveMerge}
        onEdit={task => {
          setIsDetailDrawerOpen(false);
          handleEditTask(task);
        }}
      />

      {/* Settings Panel */}
      <SettingsPanel
        config={config}
        open={isSettingsOpen}
        onOpenChange={setIsSettingsOpen}
        onUpdateSettings={handleUpdateSettings}
        onClearTasks={handleClear}
      />

      {/* Keyboard Shortcuts Dialog */}
      <KeyboardShortcutsDialog
        open={isShortcutsOpen}
        onOpenChange={setIsShortcutsOpen}
      />
    </div>
  );
}

export default Dashboard;
