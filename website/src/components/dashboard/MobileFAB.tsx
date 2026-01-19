/**
 * MobileFAB component.
 * Floating action button for mobile devices with Start/Stop and expandable actions.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { Play, Square, Plus, RefreshCw, X } from "lucide-react";
import type { ExecutionStatus } from "@/types/task";

interface MobileFABProps {
  executionStatus: ExecutionStatus | null;
  onStart: () => Promise<void>;
  onStop: () => Promise<void>;
  onRefresh: () => Promise<void>;
  onCreateTask: () => void;
  disabled?: boolean;
}

export function MobileFAB({
  executionStatus,
  onStart,
  onStop,
  onRefresh,
  onCreateTask,
  disabled,
}: MobileFABProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const isRunning = executionStatus?.state === "running";
  const isStopping = executionStatus?.state === "stopping";

  const handlePrimaryAction = async () => {
    setIsLoading(true);
    try {
      if (isRunning) {
        await onStop();
      } else {
        await onStart();
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    try {
      await onRefresh();
    } finally {
      setIsLoading(false);
      setIsExpanded(false);
    }
  };

  const handleCreateTask = () => {
    onCreateTask();
    setIsExpanded(false);
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-3 md:hidden">
      {/* Expanded Actions */}
      {isExpanded && (
        <div className="flex flex-col gap-2 animate-in fade-in slide-in-from-bottom-2 duration-200">
          <Button
            size="icon"
            variant="secondary"
            className="h-12 w-12 rounded-full shadow-lg"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            {isLoading ? (
              <Spinner className="h-5 w-5" />
            ) : (
              <RefreshCw className="h-5 w-5" />
            )}
          </Button>
          <Button
            size="icon"
            variant="secondary"
            className="h-12 w-12 rounded-full shadow-lg"
            onClick={handleCreateTask}
          >
            <Plus className="h-5 w-5" />
          </Button>
        </div>
      )}

      {/* Main FAB */}
      <div className="flex gap-2">
        {/* Expand/Collapse button */}
        <Button
          size="icon"
          variant="outline"
          className="h-14 w-14 rounded-full shadow-lg bg-background"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          {isExpanded ? (
            <X className="h-6 w-6" />
          ) : (
            <Plus className="h-6 w-6" />
          )}
        </Button>

        {/* Primary Action (Start/Stop) */}
        <Button
          size="icon"
          className={`h-14 w-14 rounded-full shadow-lg ${
            isRunning
              ? "bg-red-500 hover:bg-red-600"
              : "bg-green-500 hover:bg-green-600"
          }`}
          onClick={handlePrimaryAction}
          disabled={isLoading || isStopping || disabled}
        >
          {isLoading || isStopping ? (
            <Spinner className="h-6 w-6 text-white" />
          ) : isRunning ? (
            <Square className="h-6 w-6 text-white" />
          ) : (
            <Play className="h-6 w-6 text-white" />
          )}
        </Button>
      </div>
    </div>
  );
}

export default MobileFAB;
