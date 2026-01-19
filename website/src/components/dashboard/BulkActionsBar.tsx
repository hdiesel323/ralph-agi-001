/**
 * BulkActionsBar component.
 * Shows bulk action buttons when tasks are selected.
 */

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { X, Trash2, CheckCircle, ArrowRight } from "lucide-react";
import type { TaskPriority, TaskStatus } from "@/types/task";

interface BulkActionsBarProps {
  selectedCount: number;
  onClearSelection: () => void;
  onBulkDelete: () => void;
  onBulkStatusChange: (status: TaskStatus) => void;
  onBulkPriorityChange: (priority: TaskPriority) => void;
}

export function BulkActionsBar({
  selectedCount,
  onClearSelection,
  onBulkDelete,
  onBulkStatusChange,
  onBulkPriorityChange,
}: BulkActionsBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-primary/10 border-b animate-in slide-in-from-top-2 duration-200">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onClearSelection}
          className="h-6 w-6"
        >
          <X className="h-4 w-4" />
        </Button>
        <span className="text-sm font-medium">
          {selectedCount} task{selectedCount > 1 ? "s" : ""} selected
        </span>
      </div>

      <div className="flex items-center gap-2 ml-auto">
        {/* Move to status */}
        <Select onValueChange={v => onBulkStatusChange(v as TaskStatus)}>
          <SelectTrigger className="h-8 w-[140px] text-xs">
            <ArrowRight className="h-3 w-3 mr-1" />
            <SelectValue placeholder="Move to..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="pending">Backlog</SelectItem>
            <SelectItem value="ready">Ready</SelectItem>
            <SelectItem value="complete">Complete</SelectItem>
            <SelectItem value="cancelled">Cancel</SelectItem>
          </SelectContent>
        </Select>

        {/* Change priority */}
        <Select onValueChange={v => onBulkPriorityChange(v as TaskPriority)}>
          <SelectTrigger className="h-8 w-[120px] text-xs">
            <SelectValue placeholder="Priority..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="P0">P0 - Critical</SelectItem>
            <SelectItem value="P1">P1 - High</SelectItem>
            <SelectItem value="P2">P2 - Medium</SelectItem>
            <SelectItem value="P3">P3 - Low</SelectItem>
            <SelectItem value="P4">P4 - Backlog</SelectItem>
          </SelectContent>
        </Select>

        {/* Approve all */}
        <Button
          variant="outline"
          size="sm"
          className="h-8 text-xs"
          onClick={() => onBulkStatusChange("ready")}
        >
          <CheckCircle className="h-3 w-3 mr-1" />
          Approve All
        </Button>

        {/* Delete */}
        <Button
          variant="destructive"
          size="sm"
          className="h-8 text-xs"
          onClick={onBulkDelete}
        >
          <Trash2 className="h-3 w-3 mr-1" />
          Delete
        </Button>
      </div>
    </div>
  );
}

export default BulkActionsBar;
