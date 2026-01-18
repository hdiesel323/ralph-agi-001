/**
 * ExecutionStatus component.
 * Displays detailed execution status and progress.
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { CheckCircle, XCircle, Clock, Zap } from 'lucide-react';
import type { ExecutionStatus as ExecutionStatusType, ExecutionResults } from '@/types/task';

interface ExecutionStatusProps {
  status: ExecutionStatusType | null;
  results: ExecutionResults | null;
}

export function ExecutionStatus({ status, results }: ExecutionStatusProps) {
  if (!status) {
    return null;
  }

  const { progress, state, running_tasks } = status;
  const totalProcessed = progress.completed + progress.failed;
  const progressPercent =
    progress.total_tasks > 0 ? (totalProcessed / progress.total_tasks) * 100 : 0;

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Execution Status</CardTitle>
          <Badge
            variant={state === 'running' ? 'default' : 'secondary'}
            className={state === 'running' ? 'bg-green-500' : ''}
          >
            {state}
          </Badge>
        </div>
        <CardDescription>
          {state === 'running'
            ? `Processing ${running_tasks.length} task(s) concurrently`
            : state === 'idle'
            ? 'Ready to process tasks'
            : 'Execution stopped'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Progress Bar */}
        {progress.total_tasks > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Progress</span>
              <span>
                {totalProcessed} / {progress.total_tasks} ({progress.success_rate})
              </span>
            </div>
            <Progress value={progressPercent} className="h-2" />
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4">
          <StatCard
            icon={<Clock className="h-4 w-4" />}
            label="Running"
            value={progress.running}
            color="text-yellow-500"
          />
          <StatCard
            icon={<Zap className="h-4 w-4" />}
            label="Pending"
            value={progress.pending}
            color="text-blue-500"
          />
          <StatCard
            icon={<CheckCircle className="h-4 w-4" />}
            label="Completed"
            value={progress.completed}
            color="text-green-500"
          />
          <StatCard
            icon={<XCircle className="h-4 w-4" />}
            label="Failed"
            value={progress.failed}
            color="text-red-500"
          />
        </div>

        {/* Running Tasks */}
        {running_tasks.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Running Tasks</p>
            <div className="flex flex-wrap gap-1">
              {running_tasks.map((taskId) => (
                <Badge key={taskId} variant="outline" className="text-xs">
                  {taskId.length > 20 ? taskId.slice(0, 20) + '...' : taskId}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Recent Results */}
        {results && results.results.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Recent Results</p>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {results.results.slice(-5).reverse().map((result) => (
                <div
                  key={result.task_id}
                  className={`flex items-center justify-between text-xs p-2 rounded ${
                    result.success ? 'bg-green-500/10' : 'bg-red-500/10'
                  }`}
                >
                  <span className="truncate flex-1 mr-2">{result.task_id}</span>
                  <div className="flex items-center gap-2">
                    {result.duration_seconds && (
                      <span className="text-muted-foreground">
                        {result.duration_seconds.toFixed(1)}s
                      </span>
                    )}
                    {result.success ? (
                      <CheckCircle className="h-3 w-3 text-green-500" />
                    ) : (
                      <XCircle className="h-3 w-3 text-red-500" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/50">
      <div className={color}>{icon}</div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="font-semibold">{value}</p>
      </div>
    </div>
  );
}

export default ExecutionStatus;
