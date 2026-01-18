/**
 * Dashboard page.
 * Main visual control interface for RALPH-AGI.
 */

import { useState, useCallback } from 'react';
import { KanbanBoard } from '@/components/dashboard/KanbanBoard';
import { TaskEditor } from '@/components/dashboard/TaskEditor';
import { TaskDetailDrawer } from '@/components/dashboard/TaskDetailDrawer';
import { SettingsPanel } from '@/components/dashboard/SettingsPanel';
import { QuickActionsBar } from '@/components/dashboard/QuickActionsBar';
import { ExecutionStatus } from '@/components/dashboard/ExecutionStatus';
import { useTasks } from '@/hooks/useTasks';
import { useExecution } from '@/hooks/useExecution';
import { useConfig } from '@/hooks/useConfig';
import { useWebSocket } from '@/hooks/useWebSocket';
import { approveTask, approveMerge } from '@/api/tasks';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/spinner';
import { AlertCircle, Wifi, WifiOff, Settings } from 'lucide-react';
import type { Task, TaskCreate, TaskUpdate, ConfigUpdate } from '@/types/task';

export function Dashboard() {
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [isDetailDrawerOpen, setIsDetailDrawerOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

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
    onEvent: (event) => {
      // Refresh data when relevant events occur
      if (
        event.type.startsWith('task_') ||
        event.type.startsWith('iteration_') ||
        event.type.startsWith('loop_')
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
      await editTask(taskId, { status: status as TaskUpdate['status'] });
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

  const handleUpdateSettings = useCallback(
    async (updates: ConfigUpdate) => {
      await updateSettings(updates);
    },
    [updateSettings]
  );

  // Loading state
  if (tasksLoading && executionLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="flex flex-col items-center gap-4">
          <Spinner className="h-8 w-8" />
          <p className="text-muted-foreground">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  // Error state
  const error = tasksError || executionError;
  if (error) {
    return (
      <div className="p-8">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            Failed to load dashboard: {error.message}
            <br />
            <br />
            Make sure the API server is running:{' '}
            <code className="bg-muted px-1 rounded">ralph-agi serve</code>
          </AlertDescription>
        </Alert>
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
            {wsStatus === 'connected' ? (
              <>
                <Wifi className="h-4 w-4 text-green-500" />
                <span>Connected</span>
              </>
            ) : wsStatus === 'connecting' ? (
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
        <Button variant="ghost" size="icon" onClick={() => setIsSettingsOpen(true)}>
          <Settings className="h-5 w-5" />
        </Button>
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

      {/* Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Kanban Board */}
        <div className="flex-1 overflow-auto">
          <KanbanBoard
            tasks={tasks}
            onEditTask={handleEditTask}
            onDeleteTask={handleDeleteTask}
            onStatusChange={handleStatusChange}
            onTaskClick={handleTaskClick}
            onApproveTask={handleApproveTask}
            onApproveMerge={handleApproveMerge}
          />
        </div>

        {/* Sidebar - Execution Status */}
        <div className="w-80 border-l p-4 overflow-auto bg-muted/10">
          <ExecutionStatus status={executionStatus} results={executionResults} />
        </div>
      </div>

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
        onEdit={(task) => {
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
      />
    </div>
  );
}

export default Dashboard;
