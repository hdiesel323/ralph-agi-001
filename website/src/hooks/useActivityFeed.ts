/**
 * Hook for managing live activity feed from WebSocket events.
 */

import { useState, useCallback, useRef, useEffect } from "react";
import type { WebSocketEvent } from "@/types/task";

export interface ActivityItem {
  id: string;
  type: "tool" | "agent" | "log" | "error" | "task";
  icon: string;
  message: string;
  detail?: string;
  timestamp: Date;
}

interface UseActivityFeedOptions {
  maxItems?: number;
}

interface UseActivityFeedReturn {
  items: ActivityItem[];
  addEvent: (event: WebSocketEvent) => void;
  clear: () => void;
}

const TOOL_ICONS: Record<string, string> = {
  read_file: "📄",
  write_file: "✏️",
  edit_file: "✏️",
  list_directory: "📁",
  run_command: "⚡",
  git_status: "🔀",
  git_commit: "🔀",
  git_push: "🔀",
};

export function useActivityFeed(
  options: UseActivityFeedOptions = {}
): UseActivityFeedReturn {
  const { maxItems = 50 } = options;
  const [items, setItems] = useState<ActivityItem[]>([]);
  const idCounter = useRef(0);

  const addEvent = useCallback(
    (event: WebSocketEvent) => {
      const newItem = parseEvent(event, idCounter.current++);
      if (!newItem) return;

      setItems(prev => {
        const updated = [newItem, ...prev];
        return updated.slice(0, maxItems);
      });
    },
    [maxItems]
  );

  const clear = useCallback(() => {
    setItems([]);
  }, []);

  return { items, addEvent, clear };
}

function parseEvent(event: WebSocketEvent, id: number): ActivityItem | null {
  const timestamp = new Date(event.timestamp);
  const baseItem = { id: `activity-${id}`, timestamp };

  switch (event.type) {
    case "tool_called": {
      const toolName = event.data.tool_name as string;
      const args = event.data.args as Record<string, unknown>;
      const icon = TOOL_ICONS[toolName] || "🔧";
      let detail = "";

      if (
        toolName === "read_file" ||
        toolName === "write_file" ||
        toolName === "edit_file"
      ) {
        detail = (args.path as string) || "";
      } else if (toolName === "run_command") {
        detail = (args.command as string)?.slice(0, 50) || "";
      }

      return {
        ...baseItem,
        type: "tool",
        icon,
        message: toolName.replace(/_/g, " "),
        detail,
      };
    }

    case "tool_result": {
      const toolName = event.data.tool_name as string;
      const success = event.data.success as boolean;
      return {
        ...baseItem,
        type: success ? "tool" : "error",
        icon: success ? "✓" : "✗",
        message: `${toolName.replace(/_/g, " ")} ${success ? "completed" : "failed"}`,
        detail: !success
          ? (event.data.result as string)?.slice(0, 100)
          : undefined,
      };
    }

    case "agent_thinking": {
      const thought = event.data.thought as string;
      return {
        ...baseItem,
        type: "agent",
        icon: "💭",
        message: "Thinking...",
        detail: thought?.slice(0, 100),
      };
    }

    case "agent_action": {
      const action = event.data.action as string;
      return {
        ...baseItem,
        type: "agent",
        icon: "🤖",
        message: action?.slice(0, 80) || "Action",
      };
    }

    case "task_started": {
      const taskName = event.data.task_name as string;
      return {
        ...baseItem,
        type: "task",
        icon: "▶️",
        message: "Started task",
        detail: taskName,
      };
    }

    case "task_completed": {
      const success = event.data.success as boolean;
      const taskId = event.data.task_id as string;
      return {
        ...baseItem,
        type: success ? "task" : "error",
        icon: success ? "✅" : "❌",
        message: success ? "Task completed" : "Task failed",
        detail: taskId,
      };
    }

    case "log_message": {
      const message = event.data.message as string;
      const level = event.data.level as string;
      return {
        ...baseItem,
        type: level === "error" ? "error" : "log",
        icon: level === "error" ? "❌" : "ℹ️",
        message: message?.slice(0, 100) || "Log",
      };
    }

    case "log_error": {
      const message = event.data.message as string;
      return {
        ...baseItem,
        type: "error",
        icon: "❌",
        message: message?.slice(0, 100) || "Error",
      };
    }

    case "iteration_started": {
      const iteration = event.data.iteration as number;
      return {
        ...baseItem,
        type: "log",
        icon: "🔄",
        message: `Iteration ${iteration} started`,
      };
    }

    case "iteration_completed": {
      const iteration = event.data.iteration as number;
      const success = event.data.success as boolean;
      return {
        ...baseItem,
        type: success ? "log" : "error",
        icon: success ? "✓" : "✗",
        message: `Iteration ${iteration} ${success ? "completed" : "failed"}`,
      };
    }

    default:
      return null;
  }
}

export function formatRelativeTime(date: Date): string {
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (seconds < 5) return "now";
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return date.toLocaleDateString();
}
