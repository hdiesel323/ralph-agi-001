/**
 * TaskEditor component.
 * Form for creating and editing tasks.
 */

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Spinner } from "@/components/ui/spinner";
import { HelpCircle } from "lucide-react";
import type { Task, TaskCreate, TaskPriority } from "@/types/task";

const taskSchema = z.object({
  description: z.string().min(1, "Description is required"),
  priority: z.enum(["P0", "P1", "P2", "P3", "P4"]),
  acceptance_criteria: z.string().optional(),
  dependencies: z.string().optional(),
});

type TaskFormData = z.infer<typeof taskSchema>;

interface TaskEditorProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  task?: Task | null;
  onSubmit: (data: TaskCreate) => Promise<void>;
  availableTasks?: Task[];
}

export function TaskEditor({
  open,
  onOpenChange,
  task,
  onSubmit,
  availableTasks = [],
}: TaskEditorProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isEditing = !!task;

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<TaskFormData>({
    resolver: zodResolver(taskSchema),
    defaultValues: {
      description: "",
      priority: "P2",
      acceptance_criteria: "",
      dependencies: "",
    },
  });

  // Reset form when task changes
  useEffect(() => {
    if (task) {
      reset({
        description: task.description,
        priority: task.priority,
        acceptance_criteria: task.acceptance_criteria.join("\n"),
        dependencies: task.dependencies.join(", "),
      });
    } else {
      reset({
        description: "",
        priority: "P2",
        acceptance_criteria: "",
        dependencies: "",
      });
    }
  }, [task, reset]);

  const onFormSubmit = async (data: TaskFormData) => {
    setIsSubmitting(true);
    try {
      const taskData: TaskCreate = {
        description: data.description,
        priority: data.priority as TaskPriority,
        acceptance_criteria: data.acceptance_criteria
          ? data.acceptance_criteria.split("\n").filter(c => c.trim())
          : [],
        dependencies: data.dependencies
          ? data.dependencies
              .split(",")
              .map(d => d.trim())
              .filter(Boolean)
          : [],
      };
      await onSubmit(taskData);
      onOpenChange(false);
      reset();
    } finally {
      setIsSubmitting(false);
    }
  };

  const priorityOptions: { value: TaskPriority; label: string; hint: string }[] = [
    { value: "P0", label: "P0 - Critical", hint: "Executes immediately" },
    { value: "P1", label: "P1 - High", hint: "Executes immediately" },
    { value: "P2", label: "P2 - Medium", hint: "Executes immediately" },
    { value: "P3", label: "P3 - Low", hint: "Needs approval" },
    { value: "P4", label: "P4 - Backlog", hint: "Needs approval" },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit Task" : "Create Task"}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update the task details below."
              : "Add a new task to the queue for autonomous processing."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
          {/* Task Description */}
          <div className="space-y-2">
            <Label htmlFor="description">What needs to be done? *</Label>
            <Textarea
              id="description"
              placeholder="e.g., Add dark mode toggle to settings page"
              {...register("description")}
              className={errors.description ? "border-destructive" : ""}
            />
            <p className="text-xs text-muted-foreground">
              Describe the task clearly. The AI agent will work on this
              autonomously.
            </p>
            {errors.description && (
              <p className="text-sm text-destructive">
                {errors.description.message}
              </p>
            )}
          </div>

          {/* Priority Selection */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label htmlFor="priority">How urgent is this?</Label>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button type="button" className="inline-flex">
                    <HelpCircle className="h-4 w-4 text-muted-foreground" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-xs">
                  <p className="font-semibold mb-2">Priority Guide:</p>
                  <ul className="text-xs space-y-1">
                    <li><strong>P0-P2:</strong> High priority - Goes to Ready queue and executes immediately</li>
                    <li><strong>P3-P4:</strong> Low priority - Goes to Backlog and requires manual approval</li>
                  </ul>
                </TooltipContent>
              </Tooltip>
            </div>
            <Select
              value={watch("priority")}
              onValueChange={value =>
                setValue("priority", value as TaskPriority)
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                {priorityOptions.map(option => (
                  <SelectItem key={option.value} value={option.value}>
                    <div className="flex items-center justify-between w-full gap-4">
                      <span>{option.label}</span>
                      <span className="text-xs text-muted-foreground">{option.hint}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              P0-P2 appear in "Ready", P3-P4 go to "Backlog"
            </p>
          </div>

          {/* Acceptance Criteria */}
          <div className="space-y-2">
            <Label htmlFor="acceptance_criteria">
              How will we know it's done?
            </Label>
            <Textarea
              id="acceptance_criteria"
              placeholder={
                "e.g.,\nToggle switch appears in settings\nPreference saves to localStorage\nTheme changes immediately on toggle"
              }
              {...register("acceptance_criteria")}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              List checkable requirements, one per line. Leave blank if obvious.
            </p>
          </div>

          {/* Dependencies */}
          <div className="space-y-2">
            <Label htmlFor="dependencies">
              Does this depend on other tasks?
            </Label>
            {availableTasks.length > 0 ? (
              <>
                <div className="flex flex-wrap gap-1.5 p-2 border rounded-md bg-muted/30 max-h-24 overflow-auto">
                  {availableTasks.map(t => {
                    const currentDeps =
                      watch("dependencies")
                        ?.split(",")
                        .map(d => d.trim())
                        .filter(Boolean) || [];
                    const isSelected = currentDeps.includes(t.id);
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => {
                          if (isSelected) {
                            setValue(
                              "dependencies",
                              currentDeps.filter(d => d !== t.id).join(", ")
                            );
                          } else {
                            setValue(
                              "dependencies",
                              [...currentDeps, t.id].join(", ")
                            );
                          }
                        }}
                        className={`text-xs px-2 py-1 rounded-full transition-colors ${
                          isSelected
                            ? "bg-primary text-primary-foreground"
                            : "bg-muted hover:bg-muted/80 text-muted-foreground"
                        }`}
                        title={t.id}
                      >
                        {t.description.length > 30
                          ? t.description.slice(0, 30) + "..."
                          : t.description}
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-muted-foreground">
                  Click tasks that must finish before this one can start
                </p>
              </>
            ) : (
              <p className="text-xs text-muted-foreground italic">
                No other tasks available to depend on
              </p>
            )}
            <input type="hidden" {...register("dependencies")} />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Spinner className="mr-2 h-4 w-4" />
                  {isEditing ? "Saving..." : "Creating..."}
                </>
              ) : isEditing ? (
                "Save Changes"
              ) : (
                "Create Task"
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default TaskEditor;
