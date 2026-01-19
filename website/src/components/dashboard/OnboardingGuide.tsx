/**
 * OnboardingGuide component.
 * Shows setup instructions when the API is not connected or no tasks exist.
 */

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  CheckCircle2,
  Circle,
  Terminal,
  FileJson,
  Play,
  Copy,
  ExternalLink,
  AlertTriangle,
  Loader2,
  RefreshCw,
} from "lucide-react";

interface OnboardingGuideProps {
  isApiConnected: boolean;
  isWebSocketConnected: boolean;
  hasAnyTasks: boolean;
  onRetryConnection: () => void;
  onCreateTask: () => void;
  repoContext?: {
    name: string;
    origin_url: string | null;
    current_branch: string;
    project_root: string;
  } | null;
}

interface StepProps {
  number: number;
  title: string;
  description: string;
  isComplete: boolean;
  isActive: boolean;
  children: React.ReactNode;
}

function Step({
  number,
  title,
  description,
  isComplete,
  isActive,
  children,
}: StepProps) {
  return (
    <div className={`relative pl-10 pb-8 ${isActive ? "" : "opacity-60"}`}>
      {/* Step indicator */}
      <div className="absolute left-0 top-0">
        {isComplete ? (
          <CheckCircle2 className="h-7 w-7 text-green-500" />
        ) : (
          <div
            className={`h-7 w-7 rounded-full border-2 flex items-center justify-center text-sm font-medium ${
              isActive
                ? "border-primary text-primary"
                : "border-muted-foreground text-muted-foreground"
            }`}
          >
            {number}
          </div>
        )}
      </div>
      {/* Connector line */}
      <div className="absolute left-[13px] top-8 bottom-0 w-0.5 bg-border" />

      <div className="space-y-3">
        <div>
          <h3 className="font-semibold text-base">{title}</h3>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
        {isActive && children}
      </div>
    </div>
  );
}

function CodeBlock({
  code,
  language = "bash",
}: {
  code: string;
  language?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <pre className="bg-zinc-950 text-zinc-100 p-4 rounded-lg text-sm overflow-x-auto font-mono">
        <code>{code}</code>
      </pre>
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={handleCopy}
      >
        {copied ? (
          <CheckCircle2 className="h-4 w-4 text-green-500" />
        ) : (
          <Copy className="h-4 w-4" />
        )}
      </Button>
    </div>
  );
}

export function OnboardingGuide({
  isApiConnected,
  isWebSocketConnected,
  hasAnyTasks,
  onRetryConnection,
  onCreateTask,
  repoContext,
}: OnboardingGuideProps) {
  const currentStep = !isApiConnected ? 1 : !hasAnyTasks ? 2 : 3;

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold mb-2">Welcome to RALPH-AGI</h1>
        <p className="text-muted-foreground">
          Let's get you set up to run your first autonomous coding task
        </p>
      </div>

      {/* Connection Status Alert */}
      {!isApiConnected && (
        <Alert variant="destructive" className="mb-6">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>Cannot connect to RALPH-AGI API server</span>
            <Button variant="outline" size="sm" onClick={onRetryConnection}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {/* Current Project Info (when connected) */}
      {isApiConnected && repoContext && (
        <Card className="mb-6 border-green-200 dark:border-green-800 bg-green-50/50 dark:bg-green-950/20">
          <CardContent className="pt-4">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <span className="font-semibold">Connected to Project</span>
                </div>
                <div className="pl-7 space-y-1 text-sm">
                  <p className="font-mono font-medium">{repoContext.name}</p>
                  <p
                    className="text-muted-foreground truncate max-w-md"
                    title={repoContext.project_root}
                  >
                    {repoContext.project_root}
                  </p>
                  {repoContext.current_branch && (
                    <p className="text-muted-foreground">
                      Branch:{" "}
                      <code className="bg-muted px-1 rounded">
                        {repoContext.current_branch}
                      </code>
                    </p>
                  )}
                </div>
              </div>
              <Badge
                variant="outline"
                className="text-green-600 border-green-300"
              >
                Active
              </Badge>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Steps */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Terminal className="h-5 w-5" />
            Quick Start Guide
          </CardTitle>
          <CardDescription>
            Follow these steps to start using RALPH-AGI
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Step 1: Install RALPH-AGI */}
          <Step
            number={1}
            title="Install RALPH-AGI"
            description="First time only - get RALPH-AGI set up on your computer"
            isComplete={isApiConnected}
            isActive={currentStep === 1}
          >
            <div className="space-y-4">
              <Tabs defaultValue="new" className="w-full">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="new">First Time Setup</TabsTrigger>
                  <TabsTrigger value="existing">Already Installed</TabsTrigger>
                </TabsList>

                <TabsContent value="new" className="space-y-4 mt-4">
                  <div className="space-y-3">
                    <p className="text-sm font-medium">1. Clone the RALPH-AGI repository:</p>
                    <CodeBlock code="git clone https://github.com/hdiesel323/ralph-agi-001.git" />
                  </div>

                  <div className="space-y-3">
                    <p className="text-sm font-medium">2. Go into the folder:</p>
                    <CodeBlock code="cd ralph-agi-001" />
                  </div>

                  <div className="space-y-3">
                    <p className="text-sm font-medium">3. Run the installer (creates everything for you):</p>
                    <CodeBlock code="./install.sh" />
                    <p className="text-xs text-muted-foreground">
                      This installs Python dependencies and prompts for your Anthropic API key.
                    </p>
                  </div>

                  <div className="space-y-3">
                    <p className="text-sm font-medium">4. Start the API server:</p>
                    <CodeBlock code="./run-ralph.sh serve" />
                  </div>

                  <Alert className="bg-amber-50 dark:bg-amber-950/30 border-amber-200 dark:border-amber-800">
                    <AlertTriangle className="h-4 w-4 text-amber-600" />
                    <AlertDescription className="text-sm text-amber-800 dark:text-amber-200">
                      <strong>Need an API key?</strong> Get one from{" "}
                      <a
                        href="https://console.anthropic.com/settings/keys"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="underline font-medium"
                      >
                        console.anthropic.com
                      </a>
                    </AlertDescription>
                  </Alert>
                </TabsContent>

                <TabsContent value="existing" className="space-y-4 mt-4">
                  <p className="text-sm">
                    If RALPH-AGI is already installed, just start the server:
                  </p>
                  <div className="space-y-2">
                    <CodeBlock code="cd ~/path/to/ralph-agi-001" />
                    <CodeBlock code="./run-ralph.sh serve" />
                  </div>

                  <Alert className="bg-blue-50 dark:bg-blue-950/30 border-blue-200 dark:border-blue-800">
                    <AlertTriangle className="h-4 w-4 text-blue-600" />
                    <AlertDescription className="text-sm text-blue-800 dark:text-blue-200">
                      <strong>Want to work on a different project?</strong> RALPH works on files 
                      relative to where you start it. You can specify a project path or copy your 
                      project files to the RALPH directory.
                    </AlertDescription>
                  </Alert>
                </TabsContent>
              </Tabs>

              <p className="text-sm text-muted-foreground">
                Once running, the API server will be at{" "}
                <code className="bg-muted px-1 rounded">
                  http://localhost:8000
                </code>
              </p>

              {!isApiConnected && (
                <div className="flex items-center gap-2 pt-2">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-sm text-muted-foreground">
                    Waiting for connection...
                  </span>
                </div>
              )}
            </div>
          </Step>

          {/* Step 2: Add Tasks */}
          <Step
            number={2}
            title="Add Your First Task"
            description="Create tasks for RALPH to work on"
            isComplete={hasAnyTasks}
            isActive={currentStep === 2}
          >
            <Tabs defaultValue="manual" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="manual">Add Manually</TabsTrigger>
                <TabsTrigger value="prd">From PRD.json</TabsTrigger>
              </TabsList>

              <TabsContent value="manual" className="space-y-4 mt-4">
                <p className="text-sm">
                  Click the button below to create your first task:
                </p>
                <Button onClick={onCreateTask}>
                  <Play className="h-4 w-4 mr-2" />
                  Create Your First Task
                </Button>
              </TabsContent>

              <TabsContent value="prd" className="space-y-4 mt-4">
                <p className="text-sm">
                  If you have a{" "}
                  <code className="bg-muted px-1 rounded">PRD.json</code> file,
                  you can import tasks from it:
                </p>
                <CodeBlock code={`ralph-agi run --prd PRD.json --dry-run`} />
                <p className="text-sm text-muted-foreground">
                  The <code className="bg-muted px-1 rounded">--dry-run</code>{" "}
                  flag validates without executing. Remove it to start
                  processing.
                </p>

                <details className="mt-4">
                  <summary className="text-sm font-medium cursor-pointer hover:text-primary">
                    Example PRD.json structure
                  </summary>
                  <div className="mt-2">
                    <CodeBlock
                      language="json"
                      code={`{
  "project": {
    "name": "My Project",
    "description": "What the project does"
  },
  "features": [
    {
      "id": "feature-1",
      "description": "Create a hello world script",
      "tasks": [
        {
          "id": "task-1",
          "description": "Create hello.py",
          "priority": "P0",
          "status": "pending",
          "acceptance_criteria": [
            "File hello.py exists",
            "Running it prints 'Hello World'"
          ]
        }
      ]
    }
  ]
}`}
                    />
                  </div>
                </details>
              </TabsContent>
            </Tabs>
          </Step>

          {/* Step 3: Start Execution */}
          <Step
            number={3}
            title="Start Execution"
            description="Let RALPH autonomously process your tasks"
            isComplete={false}
            isActive={currentStep === 3}
          >
            <div className="space-y-4">
              <p className="text-sm">
                Click the{" "}
                <Badge variant="secondary" className="bg-green-600 text-white">
                  Start
                </Badge>{" "}
                button in the toolbar to begin processing tasks.
              </p>
              <p className="text-sm text-muted-foreground">
                RALPH will work through tasks in priority order, creating PRs
                and waiting for your approval before merging.
              </p>
            </div>
          </Step>
        </CardContent>
      </Card>

      {/* Additional Resources */}
      <div className="mt-6 flex flex-wrap gap-4 justify-center">
        <a
          href="https://github.com/hdiesel323/ralph-agi-001#readme"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button variant="outline" size="sm">
            <ExternalLink className="h-4 w-4 mr-2" />
            Documentation
          </Button>
        </a>
        <a
          href="https://github.com/hdiesel323/ralph-agi-001/tree/main/demo"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button variant="outline" size="sm">
            <FileJson className="h-4 w-4 mr-2" />
            Example PRDs
          </Button>
        </a>
      </div>
    </div>
  );
}

export default OnboardingGuide;
