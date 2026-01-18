/**
 * TaskEditor component.
 * Form for creating and editing tasks.
 */

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Spinner } from '@/components/ui/spinner';
import type { Task, TaskCreate, TaskPriority } from '@/types/task';

const taskSchema = z.object({
  description: z.string().min(1, 'Description is required'),
  priority: z.enum(['P0', 'P1', 'P2', 'P3', 'P4']),
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
      description: '',
      priority: 'P2',
      acceptance_criteria: '',
      dependencies: '',
    },
  });

  // Reset form when task changes
  useEffect(() => {
    if (task) {
      reset({
        description: task.description,
        priority: task.priority,
        acceptance_criteria: task.acceptance_criteria.join('\n'),
        dependencies: task.dependencies.join(', '),
      });
    } else {
      reset({
        description: '',
        priority: 'P2',
        acceptance_criteria: '',
        dependencies: '',
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
          ? data.acceptance_criteria.split('\n').filter((c) => c.trim())
          : [],
        dependencies: data.dependencies
          ? data.dependencies.split(',').map((d) => d.trim()).filter(Boolean)
          : [],
      };
      await onSubmit(taskData);
      onOpenChange(false);
      reset();
    } finally {
      setIsSubmitting(false);
    }
  };

  const priorityOptions: { value: TaskPriority; label: string }[] = [
    { value: 'P0', label: 'P0 - Critical' },
    { value: 'P1', label: 'P1 - High' },
    { value: 'P2', label: 'P2 - Medium' },
    { value: 'P3', label: 'P3 - Low' },
    { value: 'P4', label: 'P4 - Backlog' },
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Task' : 'Create Task'}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Update the task details below.'
              : 'Add a new task to the queue for autonomous processing.'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onFormSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="description">Description *</Label>
            <Textarea
              id="description"
              placeholder="What should this task accomplish?"
              {...register('description')}
              className={errors.description ? 'border-destructive' : ''}
            />
            {errors.description && (
              <p className="text-sm text-destructive">{errors.description.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="priority">Priority</Label>
            <Select
              value={watch('priority')}
              onValueChange={(value) => setValue('priority', value as TaskPriority)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select priority" />
              </SelectTrigger>
              <SelectContent>
                {priorityOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="acceptance_criteria">Acceptance Criteria</Label>
            <Textarea
              id="acceptance_criteria"
              placeholder="One criterion per line..."
              {...register('acceptance_criteria')}
              rows={3}
            />
            <p className="text-xs text-muted-foreground">
              Enter each acceptance criterion on a new line
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="dependencies">Dependencies</Label>
            <Input
              id="dependencies"
              placeholder="task-id-1, task-id-2"
              {...register('dependencies')}
            />
            <p className="text-xs text-muted-foreground">
              Comma-separated list of task IDs that must complete first
            </p>
            {availableTasks.length > 0 && (
              <div className="text-xs text-muted-foreground mt-1">
                Available: {availableTasks.map((t) => t.id).join(', ')}
              </div>
            )}
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
                  {isEditing ? 'Saving...' : 'Creating...'}
                </>
              ) : (
                isEditing ? 'Save Changes' : 'Create Task'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default TaskEditor;
