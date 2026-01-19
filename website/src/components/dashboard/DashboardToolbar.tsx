/**
 * DashboardToolbar component.
 * Provides search, filtering, and view options for the dashboard.
 */

import { Search, Filter, X, ArrowUpDown } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { TaskPriority } from "@/types/task";

export type SortOption = "priority" | "created" | "updated" | "name";

interface DashboardToolbarProps {
  searchTerm: string;
  onSearchChange: (value: string) => void;
  priorityFilter: TaskPriority | "ALL";
  onPriorityFilterChange: (value: TaskPriority | "ALL") => void;
  showCompleted: boolean;
  onShowCompletedChange: (value: boolean) => void;
  sortBy: SortOption;
  onSortChange: (value: SortOption) => void;
  totalTasks: number;
  filteredCount: number;
  inputRef?: React.RefObject<HTMLInputElement>;
}

export function DashboardToolbar({
  searchTerm,
  onSearchChange,
  priorityFilter,
  onPriorityFilterChange,
  showCompleted,
  onShowCompletedChange,
  sortBy,
  onSortChange,
  totalTasks,
  filteredCount,
  inputRef,
}: DashboardToolbarProps) {
  const hasActiveFilters =
    searchTerm || priorityFilter !== "ALL" || !showCompleted || sortBy !== "priority";

  const handleClearFilters = () => {
    onSearchChange("");
    onPriorityFilterChange("ALL");
    onShowCompletedChange(true);
    onSortChange("priority");
  };

  return (
    <div className="flex flex-col sm:flex-row gap-4 p-4 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex-1 flex items-center gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            ref={inputRef}
            placeholder="Search tasks... (Cmd+K)"
            value={searchTerm}
            onChange={e => onSearchChange(e.target.value)}
            className="pl-9 bg-muted/50 focus:bg-background transition-colors"
          />
          {searchTerm && (
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-1 h-8 w-8 hover:bg-transparent"
              onClick={() => onSearchChange("")}
            >
              <X className="h-4 w-4 text-muted-foreground" />
            </Button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 overflow-x-auto pb-2 sm:pb-0">
        <Select
          value={priorityFilter}
          onValueChange={val =>
            onPriorityFilterChange(val as TaskPriority | "ALL")
          }
        >
          <SelectTrigger className="w-[140px]">
            <Filter className="mr-2 h-4 w-4 text-muted-foreground" />
            <SelectValue placeholder="Priority" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Priorities</SelectItem>
            <SelectItem value="P0">P0 - Critical</SelectItem>
            <SelectItem value="P1">P1 - High</SelectItem>
            <SelectItem value="P2">P2 - Medium</SelectItem>
            <SelectItem value="P3">P3 - Low</SelectItem>
            <SelectItem value="P4">P4 - Backlog</SelectItem>
          </SelectContent>
        </Select>

        <Select value={sortBy} onValueChange={val => onSortChange(val as SortOption)}>
          <SelectTrigger className="w-[130px]">
            <ArrowUpDown className="mr-2 h-4 w-4 text-muted-foreground" />
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="priority">Priority</SelectItem>
            <SelectItem value="created">Created</SelectItem>
            <SelectItem value="updated">Updated</SelectItem>
            <SelectItem value="name">Name</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex items-center border rounded-md h-10 p-1 bg-muted/50">
          <Button
            variant={showCompleted ? "secondary" : "ghost"}
            size="sm"
            className="h-8 text-xs px-3"
            onClick={() => onShowCompletedChange(true)}
          >
            All
          </Button>
          <Button
            variant={!showCompleted ? "secondary" : "ghost"}
            size="sm"
            className="h-8 text-xs px-3"
            onClick={() => onShowCompletedChange(false)}
          >
            Active
          </Button>
        </div>

        {hasActiveFilters && (
          <div className="flex items-center gap-2 ml-2">
            <div className="h-6 w-px bg-border" />
            <span className="text-xs text-muted-foreground whitespace-nowrap">
              {filteredCount} of {totalTasks}
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-8 text-xs text-muted-foreground hover:text-foreground"
              onClick={handleClearFilters}
            >
              Reset
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
