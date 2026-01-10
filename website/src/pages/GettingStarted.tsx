import { motion } from "framer-motion";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Rocket,
  Terminal,
  FileCode,
  Settings,
  Play,
  CheckCircle,
  Copy,
  ExternalLink,
  BookOpen,
  Zap,
  AlertCircle,
} from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

/* Getting Started Page - Obsidian Vault Design
 * - Quick start guide
 * - Installation instructions
 * - Configuration examples
 */

const installSteps = [
  {
    title: "Clone the Repository",
    code: `git clone https://github.com/hdiesel323/ralph-agi-001.git
cd ralph-agi-001`,
  },
  {
    title: "Install Dependencies",
    code: `pnpm install`,
  },
  {
    title: "Configure Environment",
    code: `cp .env.example .env
# Edit .env with your API keys`,
  },
  {
    title: "Initialize the System",
    code: `pnpm run init`,
  },
];

const configExample = `{
  "system": {
    "name": "ralph-agi",
    "version": "1.0.0"
  },
  "orchestration": {
    "loopType": "ralph",
    "maxIterations": 100,
    "completionPromise": "<promise>COMPLETE</promise>",
    "humanInLoop": false,
    "checkpointInterval": 1
  },
  "taskManagement": {
    "prdPath": "./prd.json",
    "prdFormat": "json",
    "gitBacked": true,
    "autoCommit": true
  },
  "memory": {
    "shortTerm": {
      "type": "progress_file",
      "path": "./progress.txt",
      "mode": "append"
    },
    "longTerm": {
      "enabled": true,
      "sqlitePath": "./memory.db",
      "vectorDb": "chroma"
    }
  },
  "tools": {
    "discovery": "mcp_cli",
    "configPath": "./mcp-config.json"
  },
  "llm": {
    "defaultModel": "claude-sonnet-4-20250514",
    "ensemble": [
      { "model": "claude-sonnet-4-20250514", "weight": 0.5 },
      { "model": "claude-3-5-haiku-20241022", "weight": 0.3 },
      { "model": "claude-opus-4-20250514", "weight": 0.2 }
    ]
  }
}`;

const prdExample = `{
  "project": "my-web-app",
  "features": [
    {
      "id": "auth",
      "title": "User Authentication",
      "description": "Implement user login and registration",
      "priority": 1,
      "passes": false,
      "steps": [
        "Create user model",
        "Implement registration endpoint",
        "Implement login endpoint",
        "Add JWT token generation"
      ],
      "dependencies": []
    },
    {
      "id": "dashboard",
      "title": "User Dashboard",
      "description": "Create main dashboard view",
      "priority": 2,
      "passes": false,
      "steps": [
        "Design dashboard layout",
        "Implement data fetching",
        "Add charts and widgets"
      ],
      "dependencies": ["auth"]
    }
  ]
}`;

const cliCommands = [
  {
    command: "ralph-agi init",
    description: "Initialize a new project with PRD generation",
    example: `ralph-agi init --name "my-project" --prompt "Build a todo app with React"`,
  },
  {
    command: "ralph-agi run",
    description: "Start the autonomous execution loop",
    example: `ralph-agi run --max-iterations 100 --notify slack`,
  },
  {
    command: "ralph-agi status",
    description: "Check current project status and progress",
    example: `ralph-agi status`,
  },
  {
    command: "ralph-agi logs",
    description: "View execution logs and history",
    example: `ralph-agi logs --tail 50`,
  },
  {
    command: "ralph-agi resume",
    description: "Resume from a previous checkpoint",
    example: `ralph-agi resume --checkpoint latest`,
  },
];

function CodeBlock({ code, language = "bash" }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    toast.success("Copied to clipboard");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="relative group">
      <pre className="bg-background/80 border border-border rounded-lg p-4 overflow-x-auto text-sm font-mono">
        <code className="text-muted-foreground">{code}</code>
      </pre>
      <Button
        variant="ghost"
        size="icon"
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
        onClick={copyToClipboard}
      >
        {copied ? (
          <CheckCircle className="w-4 h-4 text-emerald-500" />
        ) : (
          <Copy className="w-4 h-4" />
        )}
      </Button>
    </div>
  );
}

export default function GettingStarted() {
  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-sm text-primary mb-4">
            <Rocket className="w-4 h-4" />
            Quick Start Guide
          </div>
          <h1 className="font-display font-extrabold text-4xl md:text-5xl mb-4">
            Getting Started
          </h1>
          <p className="text-xl text-muted-foreground">
            Set up RALPH-AGI and start building autonomous AI agents in minutes
          </p>
        </motion.div>

        {/* Prerequisites */}
        <section className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <AlertCircle className="w-6 h-6 text-accent" />
              Prerequisites
            </h2>
            <Card className="bg-card/50 backdrop-blur">
              <CardContent className="pt-6">
                <div className="grid md:grid-cols-2 gap-4">
                  {[
                    { name: "Node.js", version: "18.0+" },
                    { name: "pnpm", version: "8.0+" },
                    { name: "Git", version: "2.30+" },
                    { name: "Anthropic API Key", version: "Required" },
                  ].map((req) => (
                    <div
                      key={req.name}
                      className="flex items-center justify-between p-3 rounded-lg bg-background/50"
                    >
                      <span className="font-medium">{req.name}</span>
                      <span className="text-sm text-muted-foreground font-mono">
                        {req.version}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </section>

        {/* Installation */}
        <section className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Terminal className="w-6 h-6 text-primary" />
              Installation
            </h2>
            <div className="space-y-6">
              {installSteps.map((step, i) => (
                <div key={step.title} className="flex gap-4">
                  <div className="flex flex-col items-center">
                    <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold text-sm">
                      {i + 1}
                    </div>
                    {i < installSteps.length - 1 && (
                      <div className="w-0.5 h-full bg-border mt-2" />
                    )}
                  </div>
                  <div className="flex-1 pb-6">
                    <h3 className="font-medium mb-3">{step.title}</h3>
                    <CodeBlock code={step.code} />
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Configuration */}
        <section className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Settings className="w-6 h-6 text-primary" />
              Configuration
            </h2>
            <Tabs defaultValue="config" className="w-full">
              <TabsList className="mb-4 bg-card/50">
                <TabsTrigger value="config">ralph.config.json</TabsTrigger>
                <TabsTrigger value="prd">prd.json</TabsTrigger>
              </TabsList>
              <TabsContent value="config">
                <Card className="bg-card/50 backdrop-blur">
                  <CardHeader>
                    <CardTitle className="text-lg font-display">
                      System Configuration
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Main configuration file for RALPH-AGI system settings
                    </p>
                  </CardHeader>
                  <CardContent>
                    <CodeBlock code={configExample} language="json" />
                  </CardContent>
                </Card>
              </TabsContent>
              <TabsContent value="prd">
                <Card className="bg-card/50 backdrop-blur">
                  <CardHeader>
                    <CardTitle className="text-lg font-display">
                      PRD Structure
                    </CardTitle>
                    <p className="text-sm text-muted-foreground">
                      Product Requirements Document format for task management
                    </p>
                  </CardHeader>
                  <CardContent>
                    <CodeBlock code={prdExample} language="json" />
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </motion.div>
        </section>

        {/* CLI Commands */}
        <section className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <FileCode className="w-6 h-6 text-primary" />
              CLI Commands
            </h2>
            <div className="space-y-4">
              {cliCommands.map((cmd) => (
                <Card key={cmd.command} className="bg-card/50 backdrop-blur">
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <code className="text-primary font-mono font-medium">
                        {cmd.command}
                      </code>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {cmd.description}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <CodeBlock code={cmd.example} />
                  </CardContent>
                </Card>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Quick Start Example */}
        <section className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Play className="w-6 h-6 text-emerald-500" />
              Quick Start Example
            </h2>
            <Card className="bg-card/50 backdrop-blur border-emerald-500/20">
              <CardHeader>
                <CardTitle className="font-display">
                  Build a Todo App in AFK Mode
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Start a project, let RALPH-AGI work overnight, and wake up to
                  working code
                </p>
              </CardHeader>
              <CardContent className="space-y-4">
                <CodeBlock
                  code={`# Initialize a new project
ralph-agi init --name "todo-app" --prompt "Build a full-stack todo application with React frontend, Express backend, and PostgreSQL database. Include user authentication, CRUD operations for todos, and a clean modern UI."

# Start autonomous execution (AFK mode)
ralph-agi run --max-iterations 100 --notify slack

# Check progress in the morning
ralph-agi status
ralph-agi logs --tail 20`}
                />
                <div className="flex items-start gap-3 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <Zap className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-emerald-400">
                      Pro Tip
                    </p>
                    <p className="text-sm text-muted-foreground">
                      Use the <code className="text-primary">--notify</code> flag
                      to receive Slack or email notifications when the project
                      completes or encounters issues.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </section>

        {/* Next Steps */}
        <section className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <BookOpen className="w-6 h-6 text-primary" />
              Next Steps
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              {[
                {
                  title: "Read the PRD",
                  desc: "Understand the full system requirements and capabilities",
                  href: "/prd",
                  icon: <FileCode className="w-5 h-5" />,
                },
                {
                  title: "Explore Architecture",
                  desc: "Deep dive into technical specifications and components",
                  href: "/architecture",
                  icon: <Settings className="w-5 h-5" />,
                },
              ].map((item) => (
                <Card
                  key={item.title}
                  className="bg-card/50 backdrop-blur hover:border-primary/50 transition-colors group"
                >
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center text-primary">
                        {item.icon}
                      </div>
                      <div>
                        <CardTitle className="font-display text-lg group-hover:text-primary transition-colors">
                          {item.title}
                        </CardTitle>
                        <p className="text-sm text-muted-foreground">
                          {item.desc}
                        </p>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Button variant="outline" className="w-full" asChild>
                      <a href={item.href}>
                        Learn More
                        <ExternalLink className="w-4 h-4 ml-2" />
                      </a>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </motion.div>
        </section>
      </div>
    </Layout>
  );
}
