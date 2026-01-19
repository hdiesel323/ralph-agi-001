/**
 * SettingsPanel component - Shows repo context and runtime settings.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  FolderGit2,
  GitBranch,
  ExternalLink,
  Settings,
  Loader2,
  Trash2,
  Moon,
  Sun,
} from "lucide-react";
import type { ConfigResponse, ConfigUpdate, TaskPriority } from "@/types/task";
import { useTheme } from "@/contexts/ThemeContext";

interface SettingsPanelProps {
  config: ConfigResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpdateSettings: (updates: ConfigUpdate) => Promise<void>;
  onClearTasks?: (includeRunning?: boolean) => Promise<void>;
}

export function SettingsPanel({
  config,
  open,
  onOpenChange,
  onUpdateSettings,
  onClearTasks,
}: SettingsPanelProps) {
  const { theme, toggleTheme } = useTheme();
  const [saving, setSaving] = useState(false);
  const [localSettings, setLocalSettings] = useState({
    auto_merge_threshold: config?.settings.auto_merge_threshold ?? 0.9,
    default_priority: config?.settings.default_priority ?? "P2",
    require_approval: config?.settings.require_approval ?? true,
  });

  // Reset local state when config changes
  if (
    config &&
    localSettings.auto_merge_threshold !== config.settings.auto_merge_threshold
  ) {
    setLocalSettings({
      auto_merge_threshold: config.settings.auto_merge_threshold,
      default_priority: config.settings.default_priority,
      require_approval: config.settings.require_approval,
    });
  }

  const handleSave = async () => {
    setSaving(true);
    try {
      await onUpdateSettings(localSettings);
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to save settings:", error);
    } finally {
      setSaving(false);
    }
  };

  const formatRepoUrl = (url: string | null): string => {
    if (!url) return "-";
    // Convert SSH URL to HTTPS for display
    if (url.startsWith("git@")) {
      return url.replace("git@github.com:", "github.com/").replace(".git", "");
    }
    return url.replace(".git", "");
  };

  const getGitHubUrl = (url: string | null): string | null => {
    if (!url) return null;
    if (url.startsWith("git@")) {
      return (
        "https://" +
        url.replace("git@github.com:", "github.com/").replace(".git", "")
      );
    }
    return url.replace(".git", "");
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            Settings
          </SheetTitle>
          <SheetDescription>
            Repository context and runtime configuration
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-6 py-4">
          {/* Repository Context */}
          <div className="space-y-3">
            <h4 className="text-sm font-medium flex items-center gap-2">
              <FolderGit2 className="h-4 w-4" />
              Repository
            </h4>
            <div className="rounded-lg border p-4 space-y-3 text-sm">
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground">Name</span>
                <Badge variant="outline" className="font-mono">
                  {config?.repo.name ?? "-"}
                </Badge>
              </div>
              <div className="flex justify-between items-start">
                <span className="text-muted-foreground">Origin</span>
                <div className="flex items-center gap-1">
                  <span className="font-mono text-xs max-w-[180px] truncate">
                    {formatRepoUrl(config?.repo.origin_url ?? null)}
                  </span>
                  {getGitHubUrl(config?.repo.origin_url ?? null) && (
                    <a
                      href={getGitHubUrl(config?.repo.origin_url ?? null)!}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground"
                    >
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-muted-foreground flex items-center gap-1">
                  <GitBranch className="h-3 w-3" />
                  Branch
                </span>
                <span className="font-mono text-xs">
                  {config?.repo.current_branch ?? "-"}
                </span>
              </div>
              <div className="flex justify-between items-start">
                <span className="text-muted-foreground">Root</span>
                <span
                  className="font-mono text-xs max-w-[180px] truncate"
                  title={config?.repo.project_root}
                >
                  {config?.repo.project_root ?? "-"}
                </span>
              </div>
            </div>
          </div>

          <Separator />

          {/* Appearance */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium">Appearance</h4>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="theme-toggle">Dark Mode</Label>
                <p className="text-xs text-muted-foreground">
                  Toggle between light and dark themes
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Sun className="h-4 w-4 text-muted-foreground" />
                <Switch
                  id="theme-toggle"
                  checked={theme === "dark"}
                  onCheckedChange={toggleTheme}
                />
                <Moon className="h-4 w-4 text-muted-foreground" />
              </div>
            </div>
          </div>

          <Separator />

          {/* Runtime Settings */}
          <div className="space-y-4">
            <h4 className="text-sm font-medium">Runtime Settings</h4>

            {/* Require Approval */}
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="require-approval">Require Approval</Label>
                <p className="text-xs text-muted-foreground">
                  Tasks need manual approval before execution
                </p>
              </div>
              <Switch
                id="require-approval"
                checked={localSettings.require_approval}
                onCheckedChange={checked =>
                  setLocalSettings(prev => ({
                    ...prev,
                    require_approval: checked,
                  }))
                }
              />
            </div>

            {/* Default Priority */}
            <div className="space-y-2">
              <Label htmlFor="default-priority">Default Priority</Label>
              <Select
                value={localSettings.default_priority}
                onValueChange={value =>
                  setLocalSettings(prev => ({
                    ...prev,
                    default_priority: value as TaskPriority,
                  }))
                }
              >
                <SelectTrigger id="default-priority">
                  <SelectValue placeholder="Select priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="P0">P0 - Critical</SelectItem>
                  <SelectItem value="P1">P1 - High</SelectItem>
                  <SelectItem value="P2">P2 - Medium</SelectItem>
                  <SelectItem value="P3">P3 - Low</SelectItem>
                  <SelectItem value="P4">P4 - Backlog</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Priority for newly created tasks
              </p>
            </div>

            {/* Auto-Merge Threshold */}
            <div className="space-y-2">
              <Label htmlFor="merge-threshold">Auto-Merge Threshold</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="merge-threshold"
                  type="number"
                  min="0"
                  max="1"
                  step="0.05"
                  value={localSettings.auto_merge_threshold}
                  onChange={e =>
                    setLocalSettings(prev => ({
                      ...prev,
                      auto_merge_threshold: parseFloat(e.target.value) || 0,
                    }))
                  }
                  className="w-24"
                />
                <span className="text-sm text-muted-foreground">
                  ({(localSettings.auto_merge_threshold * 100).toFixed(0)}%)
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Tasks with confidence above this threshold may be auto-merged
              </p>
            </div>
          </div>

          {/* Danger Zone */}
          {onClearTasks && (
            <>
              <Separator />
              <div className="space-y-4">
                <h4 className="text-sm font-medium text-red-600 dark:text-red-400">
                  Danger Zone
                </h4>

                <div className="space-y-3">
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start text-muted-foreground hover:text-foreground"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Clear Completed Tasks
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>
                          Clear completed tasks?
                        </AlertDialogTitle>
                        <AlertDialogDescription>
                          This will remove all completed and failed tasks from
                          the queue. This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction onClick={() => onClearTasks(false)}>
                          Clear Completed
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>

                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="outline"
                        size="sm"
                        className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-950"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Clear All Tasks
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Clear ALL tasks?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will remove ALL tasks including running ones.
                          This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => onClearTasks(true)}
                          className="bg-destructive hover:bg-destructive/90"
                        >
                          Clear All
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            </>
          )}
        </div>

        <SheetFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save Changes
          </Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}

export default SettingsPanel;
