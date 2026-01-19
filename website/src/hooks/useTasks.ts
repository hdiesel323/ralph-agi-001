/**
 * React hooks for task data management.
 */

import { useState, useEffect, useCallback } from "react";
import type {
  Task,
  TaskListResponse,
  TaskCreate,
  TaskUpdate,
  QueueStats,
} from "@/types/task";
import {
  getTasks,
  getTask,
  createTask,
  updateTask,
  deleteTask,
  getQueueStats,
  clearQueue,
} from "@/api/tasks";

interface UseTasksOptions {
  includeTerminal?: boolean;
  pollingInterval?: number;
}

interface UseTasksReturn {
  tasks: Task[];
  stats: QueueStats | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  addTask: (task: TaskCreate) => Promise<Task>;
  editTask: (id: string, updates: TaskUpdate) => Promise<Task>;
  removeTask: (id: string) => Promise<void>;
  clearCompleted: (includeRunning?: boolean) => Promise<number>;
}

/**
 * Hook for managing tasks list with auto-refresh
 */
export function useTasks(options: UseTasksOptions = {}): UseTasksReturn {
  const { includeTerminal = true, pollingInterval = 5000 } = options;

  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<QueueStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [tasksResponse, statsResponse] = await Promise.all([
        getTasks({ include_terminal: includeTerminal }),
        getQueueStats(),
      ]);
      setTasks(tasksResponse.tasks);
      setStats(statsResponse);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch tasks"));
    } finally {
      setLoading(false);
    }
  }, [includeTerminal]);

  // Initial fetch
  useEffect(() => {
    refresh();
  }, [refresh]);

  // Polling for updates
  useEffect(() => {
    if (pollingInterval <= 0) return;

    const interval = setInterval(refresh, pollingInterval);
    return () => clearInterval(interval);
  }, [pollingInterval, refresh]);

  const addTask = useCallback(async (task: TaskCreate): Promise<Task> => {
    const newTask = await createTask(task);
    setTasks(prev => [...prev, newTask]);
    return newTask;
  }, []);

  const editTask = useCallback(
    async (id: string, updates: TaskUpdate): Promise<Task> => {
      const updatedTask = await updateTask(id, updates);
      setTasks(prev => prev.map(t => (t.id === id ? updatedTask : t)));
      return updatedTask;
    },
    []
  );

  const removeTask = useCallback(async (id: string): Promise<void> => {
    await deleteTask(id);
    setTasks(prev => prev.filter(t => t.id !== id));
  }, []);

  const clearCompleted = useCallback(
    async (includeRunning = false): Promise<number> => {
      const result = await clearQueue(includeRunning);
      await refresh();
      return result.removed;
    },
    [refresh]
  );

  return {
    tasks,
    stats,
    loading,
    error,
    refresh,
    addTask,
    editTask,
    removeTask,
    clearCompleted,
  };
}

interface UseTaskReturn {
  task: Task | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  update: (updates: TaskUpdate) => Promise<Task>;
}

/**
 * Hook for managing a single task
 */
export function useTask(taskId: string): UseTaskReturn {
  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getTask(taskId);
      setTask(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch task"));
    } finally {
      setLoading(false);
    }
  }, [taskId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const update = useCallback(
    async (updates: TaskUpdate): Promise<Task> => {
      const updated = await updateTask(taskId, updates);
      setTask(updated);
      return updated;
    },
    [taskId]
  );

  return { task, loading, error, refresh, update };
}
