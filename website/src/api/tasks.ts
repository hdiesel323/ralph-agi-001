/**
 * Task API functions for RALPH-AGI.
 */

import { apiClient } from './client';
import type {
  Task,
  TaskCreate,
  TaskUpdate,
  TaskListResponse,
  QueueStats,
  ExecutionStatus,
  ExecutionResults,
  TaskStatus,
  TaskPriority,
} from '@/types/task';

/**
 * Fetch all tasks with optional filtering
 */
export async function getTasks(params?: {
  status?: TaskStatus;
  priority?: TaskPriority;
  include_terminal?: boolean;
}): Promise<TaskListResponse> {
  const response = await apiClient.get<TaskListResponse>('/api/tasks', { params });
  return response.data;
}

/**
 * Fetch a single task by ID
 */
export async function getTask(taskId: string): Promise<Task> {
  const response = await apiClient.get<Task>(`/api/tasks/${taskId}`);
  return response.data;
}

/**
 * Create a new task
 */
export async function createTask(task: TaskCreate): Promise<Task> {
  const response = await apiClient.post<Task>('/api/tasks', task);
  return response.data;
}

/**
 * Update an existing task
 */
export async function updateTask(taskId: string, updates: TaskUpdate): Promise<Task> {
  const response = await apiClient.patch<Task>(`/api/tasks/${taskId}`, updates);
  return response.data;
}

/**
 * Delete a task
 */
export async function deleteTask(taskId: string): Promise<void> {
  await apiClient.delete(`/api/tasks/${taskId}`);
}

/**
 * Get queue statistics
 */
export async function getQueueStats(): Promise<QueueStats> {
  const response = await apiClient.get<QueueStats>('/api/queue/stats');
  return response.data;
}

/**
 * Get the next task to process
 */
export async function getNextTask(): Promise<Task | null> {
  const response = await apiClient.get<Task | null>('/api/queue/next');
  return response.data;
}

/**
 * Clear completed/failed tasks from the queue
 */
export async function clearQueue(includeRunning = false): Promise<{ removed: number }> {
  const response = await apiClient.post<{ removed: number }>('/api/queue/clear', null, {
    params: { include_running: includeRunning },
  });
  return response.data;
}

/**
 * Get execution status
 */
export async function getExecutionStatus(): Promise<ExecutionStatus> {
  const response = await apiClient.get<ExecutionStatus>('/api/execution/status');
  return response.data;
}

/**
 * Start parallel task execution
 */
export async function startExecution(params?: {
  max_concurrent?: number;
  max_tasks?: number;
}): Promise<{ status: string; max_concurrent: number; max_tasks: number | null }> {
  const response = await apiClient.post('/api/execution/start', params || { max_concurrent: 3 });
  return response.data;
}

/**
 * Stop task execution
 */
export async function stopExecution(wait = true): Promise<{ status: string }> {
  const response = await apiClient.post<{ status: string }>('/api/execution/stop', null, {
    params: { wait },
  });
  return response.data;
}

/**
 * Get execution results
 */
export async function getExecutionResults(): Promise<ExecutionResults> {
  const response = await apiClient.get<ExecutionResults>('/api/execution/results');
  return response.data;
}

/**
 * Cleanup worktrees
 */
export async function cleanupWorktrees(force = false): Promise<{ cleaned: number }> {
  const response = await apiClient.post<{ cleaned: number }>('/api/execution/cleanup', null, {
    params: { force },
  });
  return response.data;
}
