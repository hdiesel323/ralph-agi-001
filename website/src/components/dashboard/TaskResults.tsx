/**
 * TaskResults component - Displays task execution output, logs, and artifacts.
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  FileText,
  Terminal,
  FolderOpen,
  Copy,
  Check,
  Download,
  ExternalLink,
  AlertCircle,
  Info,
  AlertTriangle,
  FileCode,
  File,
} from "lucide-react";
import type { TaskOutput, TaskArtifact, ExecutionLog } from "@/types/task";

interface TaskResultsProps {
  output: TaskOutput | null;
  worktreePath?: string | null;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(fileType: string | undefined) {
  const codeTypes = ["ts", "tsx", "js", "jsx", "py", "rs", "go", "java", "cpp", "c", "h"];
  if (fileType && codeTypes.includes(fileType)) {
    return <FileCode className="h-4 w-4 text-blue-500" />;
  }
  return <File className="h-4 w-4 text-muted-foreground" />;
}

function LogLevelIcon({ level }: { level: string }) {
  switch (level) {
    case "error":
      return <AlertCircle className="h-4 w-4 text-red-500" />;
    case "warn":
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
    default:
      return <Info className="h-4 w-4 text-blue-500" />;
  }
}

function CopyButton({ text, label }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant="ghost" size="sm" onClick={handleCopy} title={label || "Copy"}>
      {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
    </Button>
  );
}

function ResultsTab({ output }: { output: TaskOutput }) {
  const content = output.markdown || output.text || output.summary;

  if (!content) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <FileText className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm">No text output available</p>
        <p className="text-xs mt-1">Check the Files or Logs tabs for more details</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {output.summary && output.summary !== content && (
        <div className="rounded-lg border bg-muted/30 p-3">
          <h4 className="text-sm font-medium mb-1">Summary</h4>
          <p className="text-sm text-muted-foreground">{output.summary}</p>
        </div>
      )}
      <div className="relative">
        <div className="absolute right-2 top-2">
          <CopyButton text={content} label="Copy output" />
        </div>
        <ScrollArea className="h-[300px] rounded-lg border bg-muted/20 p-4">
          {output.markdown ? (
            <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
              {output.markdown}
            </div>
          ) : (
            <pre className="text-sm whitespace-pre-wrap font-mono">{content}</pre>
          )}
        </ScrollArea>
      </div>
      {(output.tokens_used || output.api_calls) && (
        <div className="flex gap-4 text-xs text-muted-foreground">
          {output.tokens_used && <span>Tokens: {output.tokens_used.toLocaleString()}</span>}
          {output.api_calls && <span>API calls: {output.api_calls}</span>}
        </div>
      )}
    </div>
  );
}

function LogsTab({ logs }: { logs: ExecutionLog[] }) {
  const [filter, setFilter] = useState<string>("all");

  if (logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <Terminal className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm">No execution logs available</p>
      </div>
    );
  }

  const filteredLogs = filter === "all" ? logs : logs.filter(log => log.level === filter);
  const errorCount = logs.filter(l => l.level === "error").length;
  const warnCount = logs.filter(l => l.level === "warn").length;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Button
          variant={filter === "all" ? "secondary" : "ghost"}
          size="sm"
          onClick={() => setFilter("all")}
        >
          All ({logs.length})
        </Button>
        {errorCount > 0 && (
          <Button
            variant={filter === "error" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setFilter("error")}
            className="text-red-500"
          >
            Errors ({errorCount})
          </Button>
        )}
        {warnCount > 0 && (
          <Button
            variant={filter === "warn" ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setFilter("warn")}
            className="text-yellow-500"
          >
            Warnings ({warnCount})
          </Button>
        )}
      </div>
      <ScrollArea className="h-[300px] rounded-lg border bg-black/90 p-3">
        <div className="space-y-1 font-mono text-xs">
          {filteredLogs.map((log, index) => (
            <div
              key={index}
              className={`flex items-start gap-2 py-1 ${
                log.level === "error"
                  ? "text-red-400"
                  : log.level === "warn"
                    ? "text-yellow-400"
                    : "text-green-400"
              }`}
            >
              <LogLevelIcon level={log.level} />
              <span className="text-muted-foreground shrink-0">[{log.timestamp}]</span>
              <span className="break-all">{log.message}</span>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

function FilesTab({
  artifacts,
  worktreePath,
}: {
  artifacts: TaskArtifact[];
  worktreePath?: string | null;
}) {
  const [expandedFile, setExpandedFile] = useState<string | null>(null);

  if (artifacts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <FolderOpen className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm">No files were created or modified</p>
        {worktreePath && (
          <p className="text-xs mt-2">
            Worktree: <code className="bg-muted px-1 rounded">{worktreePath}</code>
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">
          {artifacts.length} file{artifacts.length !== 1 ? "s" : ""} created/modified
        </span>
        {worktreePath && (
          <Button variant="outline" size="sm" asChild>
            <a href={`vscode://file/${worktreePath}`} title="Open in VS Code">
              <ExternalLink className="h-4 w-4 mr-1" />
              Open Folder
            </a>
          </Button>
        )}
      </div>
      <ScrollArea className="h-[300px]">
        <div className="space-y-2">
          {artifacts.map((artifact, index) => (
            <div key={index} className="rounded-lg border bg-muted/20">
              <div
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-muted/30"
                onClick={() => setExpandedFile(expandedFile === artifact.path ? null : artifact.path)}
              >
                <div className="flex items-center gap-2 min-w-0">
                  {getFileIcon(artifact.file_type)}
                  <span className="font-mono text-sm truncate">{artifact.path}</span>
                  {artifact.file_type && (
                    <Badge variant="outline" className="text-xs">
                      .{artifact.file_type}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {artifact.size !== undefined && (
                    <span className="text-xs text-muted-foreground">
                      {formatFileSize(artifact.size)}
                    </span>
                  )}
                  <CopyButton
                    text={artifact.absolute_path || artifact.path}
                    label="Copy path"
                  />
                </div>
              </div>
              {expandedFile === artifact.path && artifact.content && (
                <div className="border-t p-3">
                  <ScrollArea className="h-[200px]">
                    <pre className="text-xs font-mono whitespace-pre-wrap bg-black/50 p-3 rounded">
                      {artifact.content}
                    </pre>
                  </ScrollArea>
                </div>
              )}
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}

export function TaskResults({ output, worktreePath }: TaskResultsProps) {
  if (!output) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
        <AlertCircle className="h-12 w-12 mb-4 opacity-50" />
        <p className="text-sm font-medium">No results available</p>
        <p className="text-xs mt-1">
          This task hasn't produced any output yet. Results will appear here once the task completes.
        </p>
      </div>
    );
  }

  const hasResults = output.text || output.markdown || output.summary;
  const hasLogs = output.logs && output.logs.length > 0;
  const hasFiles = output.artifacts && output.artifacts.length > 0;

  const defaultTab = hasResults ? "results" : hasFiles ? "files" : "logs";

  return (
    <Tabs defaultValue={defaultTab} className="w-full">
      <TabsList className="grid w-full grid-cols-3">
        <TabsTrigger value="results" className="flex items-center gap-1">
          <FileText className="h-4 w-4" />
          Results
        </TabsTrigger>
        <TabsTrigger value="logs" className="flex items-center gap-1">
          <Terminal className="h-4 w-4" />
          Logs
          {hasLogs && (
            <Badge variant="secondary" className="ml-1 text-xs">
              {output.logs.length}
            </Badge>
          )}
        </TabsTrigger>
        <TabsTrigger value="files" className="flex items-center gap-1">
          <FolderOpen className="h-4 w-4" />
          Files
          {hasFiles && (
            <Badge variant="secondary" className="ml-1 text-xs">
              {output.artifacts.length}
            </Badge>
          )}
        </TabsTrigger>
      </TabsList>
      <TabsContent value="results" className="mt-4">
        <ResultsTab output={output} />
      </TabsContent>
      <TabsContent value="logs" className="mt-4">
        <LogsTab logs={output.logs || []} />
      </TabsContent>
      <TabsContent value="files" className="mt-4">
        <FilesTab artifacts={output.artifacts || []} worktreePath={worktreePath} />
      </TabsContent>
    </Tabs>
  );
}

export default TaskResults;
