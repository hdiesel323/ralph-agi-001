import { motion } from "framer-motion";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Cpu,
  Database,
  Layers,
  GitBranch,
  Workflow,
  Server,
  Shield,
  Activity,
  Box,
  Zap,
} from "lucide-react";

/* Architecture Page - Obsidian Vault Design
 * - System architecture diagrams
 * - Component specifications
 * - Data flow visualizations
 */

const architectureDiagram = `
┌─────────────────────────────────────────────────────────────────────────────┐
│                              RALPH-AGI SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         CONTROL PLANE                                   │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐ │ │
│  │  │   CLI/API    │  │    Config    │  │  Scheduler   │  │  Monitor   │ │ │
│  │  │  Interface   │  │   Manager    │  │   (Cron)     │  │ Dashboard  │ │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                        │
│                                     ▼                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      ORCHESTRATION LAYER                                │ │
│  │                                                                          │ │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │ │
│  │  │                      RALPH LOOP ENGINE                            │  │ │
│  │  │                                                                    │  │ │
│  │  │   while (iteration < max && !complete):                           │  │ │
│  │  │     1. Initialize/Resume Session                                  │  │ │
│  │  │     2. Load Context (Memory + Progress + Git)                     │  │ │
│  │  │     3. Select Task (PRD: highest priority, no blockers)           │  │ │
│  │  │     4. Execute Task (LLM + Tools)                                 │  │ │
│  │  │     5. Verify (Cascade Evaluation)                                │  │ │
│  │  │     6. Update State (PRD + Progress + Git Commit)                 │  │ │
│  │  │     7. Check Completion (Promise Detection)                       │  │ │
│  │  │                                                                    │  │ │
│  │  └──────────────────────────────────────────────────────────────────┘  │ │
│  │                                                                          │ │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐   │ │
│  │  │  Initializer   │  │    Coding      │  │    Specialized         │   │ │
│  │  │    Agent       │  │    Agent       │  │    Agents (Future)     │   │ │
│  │  └────────────────┘  └────────────────┘  └────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
`;

const components = [
  {
    id: "loop-engine",
    title: "Ralph Loop Engine",
    icon: <Workflow className="w-5 h-5" />,
    description:
      "The central orchestrator implementing a simple but powerful iterative pattern.",
    specs: [
      { label: "Implementation", value: "TypeScript/Node.js or Python" },
      { label: "Loop Type", value: "Synchronous, single-threaded" },
      { label: "Max Iterations", value: "Configurable (default: 100)" },
      { label: "Completion Signal", value: "<promise>COMPLETE</promise>" },
      { label: "Checkpoint Frequency", value: "Every iteration" },
      { label: "Error Handling", value: "Retry with exponential backoff" },
    ],
  },
  {
    id: "memory-system",
    title: "Memory System",
    icon: <Database className="w-5 h-5" />,
    description:
      "Three-tier memory providing context persistence across sessions.",
    specs: [
      { label: "Short-term", value: "progress.txt (per-sprint)" },
      { label: "Medium-term", value: "Git history (permanent)" },
      { label: "Long-term", value: "SQLite + Chroma (permanent)" },
      { label: "Access Pattern", value: "Semantic search + log traversal" },
      { label: "Embedding Model", value: "text-embedding-3-small" },
      { label: "Retention", value: "Configurable per tier" },
    ],
  },
  {
    id: "tool-registry",
    title: "Tool Registry",
    icon: <Box className="w-5 h-5" />,
    description:
      "Dynamic discovery using MCP CLI for token-efficient tool loading.",
    specs: [
      { label: "Discovery Method", value: "MCP CLI hierarchical" },
      { label: "Token Reduction", value: "99% vs static loading" },
      { label: "List Servers", value: "~50 tokens" },
      { label: "List Tools", value: "~100 tokens" },
      { label: "Get Schema", value: "~200 tokens" },
      { label: "Caching", value: "LRU with TTL" },
    ],
  },
  {
    id: "evaluation",
    title: "Evaluation Pipeline",
    icon: <Shield className="w-5 h-5" />,
    description:
      "Cascaded verification ensuring quality through progressive validation.",
    specs: [
      { label: "Stage 1", value: "Static Analysis (~1s)" },
      { label: "Stage 2", value: "Unit Tests (~10s)" },
      { label: "Stage 3", value: "Integration Tests (~30s)" },
      { label: "Stage 4", value: "E2E Tests (~60s)" },
      { label: "Stage 5", value: "LLM Judge (~30s)" },
      { label: "Logic", value: "Fail fast - cascade on pass" },
    ],
  },
];

const dataFlows = [
  {
    title: "First Run (Initialization)",
    steps: [
      "Parse user request",
      "Generate comprehensive feature list",
      "Create PRD.json with all features (passes: false)",
      "Create progress.txt (empty)",
      "Create init.sh script",
      "Initialize git repository",
      "Create initial commit",
      "Enter Ralph Loop",
    ],
  },
  {
    title: "Subsequent Runs (Coding Agent)",
    steps: [
      "Load Context (progress.txt + memory + git log)",
      "Select Task (PRD: highest priority, no blockers)",
      "Execute Task (LLM + Tools)",
      "Verify (Cascade Evaluation)",
      "Update State (PRD + Progress + Git Commit)",
      "Check Completion (Promise Detection)",
      "Repeat or Exit",
    ],
  },
];

const resourceRequirements = [
  {
    component: "RALPH-AGI Process",
    cpu: "2 cores",
    memory: "4 GB",
    storage: "-",
  },
  { component: "SQLite Database", cpu: "-", memory: "512 MB", storage: "1 GB" },
  {
    component: "Chroma Vector DB",
    cpu: "1 core",
    memory: "2 GB",
    storage: "10 GB",
  },
  {
    component: "Sandboxed Workspace",
    cpu: "2 cores",
    memory: "4 GB",
    storage: "50 GB",
  },
  {
    component: "Browser (Chromium)",
    cpu: "1 core",
    memory: "2 GB",
    storage: "-",
  },
  { component: "Total", cpu: "6 cores", memory: "12.5 GB", storage: "61 GB" },
];

export default function Architecture() {
  return (
    <Layout>
      <div className="max-w-6xl mx-auto px-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-sm text-primary mb-4">
            <Cpu className="w-4 h-4" />
            Technical Documentation
          </div>
          <h1 className="font-display font-extrabold text-4xl md:text-5xl mb-4">
            System Architecture
          </h1>
          <p className="text-xl text-muted-foreground">
            Detailed technical specifications and component design for RALPH-AGI
          </p>
        </motion.div>

        {/* Architecture Diagram */}
        <section className="mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Layers className="w-6 h-6 text-primary" />
              System Overview
            </h2>
            <Card className="bg-card/50 backdrop-blur overflow-hidden">
              <CardContent className="p-0">
                <div className="relative aspect-video">
                  <img
                    src="/images/hero-neural-network.png"
                    alt="System Architecture"
                    className="w-full h-full object-cover opacity-30"
                  />
                  <div className="absolute inset-0 flex items-center justify-center p-8">
                    <pre className="text-xs md:text-sm text-foreground/90 font-mono overflow-x-auto max-w-full">
                      {architectureDiagram}
                    </pre>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </section>

        {/* Component Specifications */}
        <section className="mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Server className="w-6 h-6 text-primary" />
              Component Specifications
            </h2>
            <Tabs defaultValue="loop-engine" className="w-full">
              <TabsList className="w-full justify-start mb-6 bg-card/50 p-1 overflow-x-auto">
                {components.map(comp => (
                  <TabsTrigger
                    key={comp.id}
                    value={comp.id}
                    className="data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
                  >
                    <span className="mr-2">{comp.icon}</span>
                    <span className="hidden sm:inline">{comp.title}</span>
                  </TabsTrigger>
                ))}
              </TabsList>
              {components.map(comp => (
                <TabsContent key={comp.id} value={comp.id}>
                  <Card className="bg-card/50 backdrop-blur">
                    <CardHeader>
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center text-primary">
                          {comp.icon}
                        </div>
                        <div>
                          <CardTitle className="font-display text-xl">
                            {comp.title}
                          </CardTitle>
                          <p className="text-sm text-muted-foreground mt-1">
                            {comp.description}
                          </p>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="grid md:grid-cols-2 gap-4">
                        {comp.specs.map(spec => (
                          <div
                            key={spec.label}
                            className="flex justify-between items-center p-3 rounded-lg bg-background/50"
                          >
                            <span className="text-sm text-muted-foreground">
                              {spec.label}
                            </span>
                            <span className="text-sm font-mono text-primary">
                              {spec.value}
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </TabsContent>
              ))}
            </Tabs>
          </motion.div>
        </section>

        {/* Data Flow */}
        <section className="mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <GitBranch className="w-6 h-6 text-primary" />
              Data Flow
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              {dataFlows.map(flow => (
                <Card key={flow.title} className="bg-card/50 backdrop-blur">
                  <CardHeader>
                    <CardTitle className="font-display">{flow.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {flow.steps.map((step, i) => (
                        <div key={i} className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-primary/20 flex items-center justify-center text-xs font-bold text-primary shrink-0">
                            {i + 1}
                          </div>
                          <span className="text-sm text-muted-foreground pt-0.5">
                            {step}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </motion.div>
        </section>

        {/* Feature Images */}
        <section className="mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Zap className="w-6 h-6 text-primary" />
              Visual Architecture
            </h2>
            <div className="grid md:grid-cols-2 gap-6">
              <Card className="bg-card/50 backdrop-blur overflow-hidden">
                <div className="aspect-video">
                  <img
                    src="/images/memory-system.png"
                    alt="Memory System"
                    className="w-full h-full object-cover"
                  />
                </div>
                <CardContent className="pt-4">
                  <h3 className="font-display font-semibold mb-2">
                    Three-Tier Memory System
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Short-term (cyan), medium-term (purple), and long-term
                    (gold) memory tiers with flowing data connections.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur overflow-hidden">
                <div className="aspect-video">
                  <img
                    src="/images/loop-engine.png"
                    alt="Loop Engine"
                    className="w-full h-full object-cover"
                  />
                </div>
                <CardContent className="pt-4">
                  <h3 className="font-display font-semibold mb-2">
                    Ralph Loop Engine
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Infinite loop visualization representing the continuous
                    processing cycle of the autonomous agent.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur overflow-hidden">
                <div className="aspect-square">
                  <img
                    src="/images/tool-registry.png"
                    alt="Tool Registry"
                    className="w-full h-full object-cover"
                  />
                </div>
                <CardContent className="pt-4">
                  <h3 className="font-display font-semibold mb-2">
                    Dynamic Tool Registry
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    MCP server connections with dynamic tool discovery for
                    token-efficient operations.
                  </p>
                </CardContent>
              </Card>
              <Card className="bg-card/50 backdrop-blur overflow-hidden">
                <div className="aspect-square">
                  <img
                    src="/images/evaluation-pipeline.png"
                    alt="Evaluation Pipeline"
                    className="w-full h-full object-cover"
                  />
                </div>
                <CardContent className="pt-4">
                  <h3 className="font-display font-semibold mb-2">
                    Cascaded Evaluation Pipeline
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Five-stage verification cascade with data flowing through
                    progressive validation stages.
                  </p>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        </section>

        {/* Resource Requirements */}
        <section className="mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Activity className="w-6 h-6 text-primary" />
              Resource Requirements
            </h2>
            <Card className="bg-card/50 backdrop-blur overflow-hidden">
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border bg-muted/30">
                        <th className="text-left py-4 px-6 font-medium">
                          Component
                        </th>
                        <th className="text-left py-4 px-6 font-medium">CPU</th>
                        <th className="text-left py-4 px-6 font-medium">
                          Memory
                        </th>
                        <th className="text-left py-4 px-6 font-medium">
                          Storage
                        </th>
                      </tr>
                    </thead>
                    <tbody className="text-muted-foreground">
                      {resourceRequirements.map((req, i) => (
                        <tr
                          key={req.component}
                          className={`border-b border-border/50 ${
                            i === resourceRequirements.length - 1
                              ? "bg-primary/5 font-medium text-foreground"
                              : ""
                          }`}
                        >
                          <td className="py-4 px-6">{req.component}</td>
                          <td className="py-4 px-6 font-mono">{req.cpu}</td>
                          <td className="py-4 px-6 font-mono">{req.memory}</td>
                          <td className="py-4 px-6 font-mono">{req.storage}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </section>

        {/* Security */}
        <section className="mb-16">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
              <Shield className="w-6 h-6 text-primary" />
              Security Considerations
            </h2>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  title: "Sandboxing",
                  desc: "All code execution occurs within isolated containers with limited capabilities, no host filesystem access, and whitelisted network endpoints.",
                },
                {
                  title: "Secret Management",
                  desc: "Secrets managed through environment variables, never stored in code or logs. Supports AWS Secrets Manager and HashiCorp Vault.",
                },
                {
                  title: "Rate Limiting",
                  desc: "Multi-level rate limiting prevents runaway resource consumption. API calls, tool executions, and Git commits are all limited.",
                },
              ].map(item => (
                <Card key={item.title} className="bg-card/50 backdrop-blur">
                  <CardHeader>
                    <CardTitle className="font-display text-lg">
                      {item.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">{item.desc}</p>
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
