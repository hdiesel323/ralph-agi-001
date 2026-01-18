/**
 * TypeScript types for the RALPH-AGI Task API.
 * These mirror the Pydantic schemas in ralph_agi/api/schemas.py
 */

export type TaskStatus = 'pending' | 'ready' | 'running' | 'complete' | 'failed' | 'cancelled';
export type TaskPriority = 'P0' | 'P1' | 'P2' | 'P3' | 'P4';
export type ExecutionState = 'idle' | 'running' | 'stopping' | 'stopped';

/**
 * Task entity from the API
 */
export interface Task {
  id: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  acceptance_criteria: string[];
  dependencies: string[];
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
  worktree_path: string | null;
  branch: string | null;
  pr_url: string | null;
  pr_number: number | null;
  confidence: number | null;
  error: string | null;
  metadata: Record<string, unknown>;
}

/**
 * Request body for creating a task
 */
export interface TaskCreate {
  description: string;
  priority?: TaskPriority;
  acceptance_criteria?: string[];
  dependencies?: string[];
  metadata?: Record<string, unknown>;
}

/**
 * Request body for updating a task
 */
export interface TaskUpdate {
  description?: string;
  priority?: TaskPriority;
  status?: TaskStatus;
  acceptance_criteria?: string[];
  dependencies?: string[];
  worktree_path?: string;
  branch?: string;
  pr_url?: string;
  pr_number?: number;
  confidence?: number;
  error?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Response for task list endpoint
 */
export interface TaskListResponse {
  tasks: Task[];
  total: number;
}

/**
 * Queue statistics
 */
export interface QueueStats {
  total: number;
  pending: number;
  ready: number;
  running: number;
  complete: number;
  failed: number;
  cancelled: number;
}

/**
 * Execution progress
 */
export interface ExecutionProgress {
  total_tasks: number;
  completed: number;
  failed: number;
  running: number;
  pending: number;
  success_rate: string;
}

/**
 * Execution status response
 */
export interface ExecutionStatus {
  state: ExecutionState;
  max_concurrent: number;
  progress: ExecutionProgress;
  running_tasks: string[];
  queue_stats: QueueStats;
}

/**
 * Task result from execution
 */
export interface TaskResult {
  task_id: string;
  success: boolean;
  worktree_path: string | null;
  branch: string | null;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  error: string | null;
  pr_url: string | null;
  confidence: number;
}

/**
 * Execution results response
 */
export interface ExecutionResults {
  results: TaskResult[];
  total: number;
  succeeded: number;
  failed: number;
}

/**
 * WebSocket event from the server
 */
export interface WebSocketEvent {
  type: string;
  timestamp: string;
  data: Record<string, unknown>;
}

/**
 * Kanban column configuration
 */
export interface KanbanColumn {
  id: string;
  title: string;
  statuses: TaskStatus[];
  filter?: (task: Task) => boolean;
}

/**
 * Default Kanban columns configuration
 */
export const KANBAN_COLUMNS: KanbanColumn[] = [
  {
    id: 'backlog',
    title: 'Backlog',
    statuses: ['pending'],
    filter: (task) => task.priority === 'P3' || task.priority === 'P4',
  },
  {
    id: 'ready',
    title: 'Ready',
    statuses: ['pending', 'ready'],
    filter: (task) => task.priority === 'P0' || task.priority === 'P1' || task.priority === 'P2',
  },
  {
    id: 'running',
    title: 'Running',
    statuses: ['running'],
  },
  {
    id: 'review',
    title: 'Review',
    statuses: ['complete'],
    filter: (task) => task.pr_url !== null && task.confidence !== null && task.confidence < 0.9,
  },
  {
    id: 'done',
    title: 'Done',
    statuses: ['complete'],
    filter: (task) => task.pr_url === null || (task.confidence !== null && task.confidence >= 0.9),
  },
];

/**
 * Priority display configuration
 */
export const PRIORITY_CONFIG: Record<TaskPriority, { label: string; color: string }> = {
  P0: { label: 'Critical', color: 'bg-red-500' },
  P1: { label: 'High', color: 'bg-orange-500' },
  P2: { label: 'Medium', color: 'bg-yellow-500' },
  P3: { label: 'Low', color: 'bg-blue-500' },
  P4: { label: 'Backlog', color: 'bg-gray-500' },
};

/**
 * Status display configuration
 */
export const STATUS_CONFIG: Record<TaskStatus, { label: string; icon: string; color: string }> = {
  pending: { label: 'Pending', icon: '⏳', color: 'text-gray-500' },
  ready: { label: 'Ready', icon: '✨', color: 'text-blue-500' },
  running: { label: 'Running', icon: '🔄', color: 'text-yellow-500' },
  complete: { label: 'Complete', icon: '✅', color: 'text-green-500' },
  failed: { label: 'Failed', icon: '❌', color: 'text-red-500' },
  cancelled: { label: 'Cancelled', icon: '🚫', color: 'text-gray-400' },
};
