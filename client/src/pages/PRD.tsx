import { motion } from "framer-motion";
import { Streamdown } from "streamdown";
import Layout from "@/components/Layout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Target,
  Users,
  Layers,
  CheckCircle,
  Clock,
  AlertTriangle,
  Lightbulb,
  Workflow,
} from "lucide-react";

/* PRD Page - Obsidian Vault Design
 * - Full PRD content with proper formatting
 * - Table of contents for navigation
 * - Reading-optimized layout
 */

const tableOfContents = [
  { id: "executive-summary", title: "Executive Summary" },
  { id: "problem-statement", title: "Problem Statement" },
  { id: "goals", title: "Goals & Objectives" },
  { id: "target-users", title: "Target Users" },
  { id: "core-features", title: "Core Features" },
  { id: "user-stories", title: "User Stories" },
  { id: "non-functional", title: "Non-Functional Requirements" },
  { id: "success-metrics", title: "Success Metrics" },
  { id: "risks", title: "Risks & Mitigations" },
  { id: "roadmap", title: "Implementation Roadmap" },
];

export default function PRD() {
  const scrollToSection = (id: string) => {
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  return (
    <Layout>
      <div className="flex">
        {/* Table of Contents - Desktop */}
        <aside className="hidden xl:block w-64 shrink-0 sticky top-0 h-screen overflow-y-auto border-r border-border p-6">
          <h3 className="font-display font-semibold text-sm text-muted-foreground uppercase tracking-wider mb-4">
            On this page
          </h3>
          <nav className="space-y-1">
            {tableOfContents.map((item) => (
              <button
                key={item.id}
                onClick={() => scrollToSection(item.id)}
                className="block w-full text-left px-3 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-accent/50 rounded-lg transition-colors"
              >
                {item.title}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <div className="flex-1 min-w-0">
          <div className="max-w-4xl mx-auto px-6 py-12">
            {/* Header */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-12"
            >
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-sm text-primary mb-4">
                <Workflow className="w-4 h-4" />
                Product Requirements Document
              </div>
              <h1 className="font-display font-extrabold text-4xl md:text-5xl mb-4">
                RALPH-AGI PRD
              </h1>
              <p className="text-xl text-muted-foreground">
                Recursive Autonomous Long-horizon Processing with Hierarchical
                AGI-like Intelligence
              </p>
              <div className="flex items-center gap-4 mt-6 text-sm text-muted-foreground">
                <span>Version 1.0</span>
                <span>•</span>
                <span>January 10, 2026</span>
              </div>
            </motion.div>

            {/* Executive Summary */}
            <section id="executive-summary" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <Target className="w-6 h-6 text-primary" />
                  Executive Summary
                </h2>
                <Card className="bg-card/50 backdrop-blur border-primary/20">
                  <CardContent className="pt-6 prose-obsidian text-muted-foreground">
                    <p>
                      RALPH-AGI represents a comprehensive framework for building
                      autonomous AI agents capable of executing complex, multi-step
                      tasks over extended periods. The system synthesizes proven
                      patterns from multiple sources including the Ralph Wiggum
                      technique, Anthropic's effective harnesses for long-running
                      agents, Claude-Mem persistent memory, Beads dependency-aware
                      task tracking, and MCP CLI dynamic tool discovery.
                    </p>
                    <p>
                      The core innovation lies in combining a simple iterative loop
                      (the "Ralph Loop") with sophisticated memory management and
                      self-verification capabilities. This approach enables AI agents
                      to maintain context across sessions, learn from past
                      experiences, and autonomously complete projects that would
                      traditionally require continuous human oversight.
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            </section>

            {/* Problem Statement */}
            <section id="problem-statement" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <AlertTriangle className="w-6 h-6 text-accent" />
                  Problem Statement
                </h2>
                <div className="prose-obsidian text-muted-foreground space-y-4">
                  <p>
                    Current AI coding assistants face several fundamental
                    limitations that prevent them from achieving true autonomous
                    operation:
                  </p>
                  <div className="grid md:grid-cols-2 gap-4 my-6">
                    {[
                      {
                        title: "Context Window Limitations",
                        desc: "Large projects exceed token limits, causing loss of important context",
                      },
                      {
                        title: "Session Amnesia",
                        desc: "Each conversation starts fresh with no memory of previous work",
                      },
                      {
                        title: "Verification Gaps",
                        desc: "No systematic way to verify that generated code actually works",
                      },
                      {
                        title: "Tool Overhead",
                        desc: "Loading all available tools consumes significant context tokens",
                      },
                    ].map((item) => (
                      <Card
                        key={item.title}
                        className="bg-destructive/5 border-destructive/20"
                      >
                        <CardHeader className="pb-2">
                          <CardTitle className="text-base font-medium">
                            {item.title}
                          </CardTitle>
                        </CardHeader>
                        <CardContent>
                          <p className="text-sm text-muted-foreground">
                            {item.desc}
                          </p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                  <p>
                    These limitations result in AI assistants that require constant
                    human supervision, cannot work on tasks spanning multiple
                    sessions, and frequently produce code that fails in unexpected
                    ways. RALPH-AGI addresses each of these challenges through its
                    integrated architecture.
                  </p>
                </div>
              </motion.div>
            </section>

            {/* Goals & Objectives */}
            <section id="goals" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <CheckCircle className="w-6 h-6 text-emerald-500" />
                  Goals & Objectives
                </h2>
                <div className="space-y-6">
                  <Card className="bg-card/50 backdrop-blur">
                    <CardHeader>
                      <CardTitle className="text-lg">Primary Goals</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-3">
                        {[
                          "Enable autonomous execution of complex, multi-step software development tasks",
                          "Maintain persistent memory across sessions for continuous learning",
                          "Implement self-verification to ensure generated code meets quality standards",
                          "Reduce token overhead through dynamic tool discovery",
                          "Provide reliable error recovery through Git-backed checkpointing",
                        ].map((goal, i) => (
                          <li key={i} className="flex items-start gap-3">
                            <CheckCircle className="w-5 h-5 text-emerald-500 shrink-0 mt-0.5" />
                            <span className="text-muted-foreground">{goal}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </Card>

                  <Card className="bg-card/50 backdrop-blur">
                    <CardHeader>
                      <CardTitle className="text-lg">Success Criteria</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid md:grid-cols-3 gap-4">
                        {[
                          { metric: "80%", label: "Task Completion Rate" },
                          { metric: "99%", label: "Token Reduction" },
                          { metric: "< 5%", label: "Stuck Rate" },
                        ].map((item) => (
                          <div
                            key={item.label}
                            className="text-center p-4 rounded-lg bg-primary/5 border border-primary/10"
                          >
                            <p className="text-3xl font-display font-bold text-primary">
                              {item.metric}
                            </p>
                            <p className="text-sm text-muted-foreground mt-1">
                              {item.label}
                            </p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </motion.div>
            </section>

            {/* Target Users */}
            <section id="target-users" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <Users className="w-6 h-6 text-primary" />
                  Target Users
                </h2>
                <div className="grid md:grid-cols-2 gap-6">
                  {[
                    {
                      title: "Solo Developers",
                      desc: "Individual developers seeking to automate repetitive coding tasks and accelerate project delivery",
                      needs: [
                        "AFK mode for overnight builds",
                        "Minimal configuration",
                        "Clear progress visibility",
                      ],
                    },
                    {
                      title: "Development Teams",
                      desc: "Engineering teams looking to augment their workflow with autonomous agents for routine tasks",
                      needs: [
                        "Integration with existing CI/CD",
                        "Collaborative oversight",
                        "Audit trails",
                      ],
                    },
                    {
                      title: "AI Researchers",
                      desc: "Researchers exploring autonomous agent architectures and long-horizon task execution",
                      needs: [
                        "Extensible architecture",
                        "Detailed logging",
                        "Experiment reproducibility",
                      ],
                    },
                    {
                      title: "Enterprise Teams",
                      desc: "Large organizations requiring secure, scalable autonomous development capabilities",
                      needs: [
                        "Security compliance",
                        "Resource management",
                        "Multi-project support",
                      ],
                    },
                  ].map((user) => (
                    <Card
                      key={user.title}
                      className="bg-card/50 backdrop-blur hover:border-primary/50 transition-colors"
                    >
                      <CardHeader>
                        <CardTitle className="font-display">{user.title}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-muted-foreground mb-4">{user.desc}</p>
                        <div className="space-y-2">
                          {user.needs.map((need) => (
                            <div
                              key={need}
                              className="flex items-center gap-2 text-sm"
                            >
                              <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                              <span className="text-muted-foreground">{need}</span>
                            </div>
                          ))}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </motion.div>
            </section>

            {/* Core Features */}
            <section id="core-features" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <Layers className="w-6 h-6 text-primary" />
                  Core Features
                </h2>
                <div className="space-y-8">
                  {[
                    {
                      title: "1. Ralph Loop Engine",
                      features: [
                        "Simple iterative execution pattern processing one task at a time",
                        "Configurable maximum iterations with completion detection",
                        "Automatic checkpointing at each iteration",
                        "Promise-based completion signaling",
                      ],
                    },
                    {
                      title: "2. Three-Tier Memory System",
                      features: [
                        "Short-term: progress.txt for current session state",
                        "Medium-term: Git history for recoverable checkpoints",
                        "Long-term: SQLite + Chroma for semantic search across sessions",
                        "Automatic memory injection based on task relevance",
                      ],
                    },
                    {
                      title: "3. PRD-Driven Task Management",
                      features: [
                        "Structured JSON format with passes/steps/dependencies",
                        "Dependency graph for task ordering",
                        "Priority-based selection with blocker detection",
                        "Automatic status updates on completion",
                      ],
                    },
                    {
                      title: "4. Dynamic Tool Discovery",
                      features: [
                        "MCP CLI integration for on-demand tool loading",
                        "99% token reduction compared to static definitions",
                        "Hierarchical discovery: servers → tools → schemas",
                        "Caching for frequently used tools",
                      ],
                    },
                    {
                      title: "5. Cascaded Evaluation Pipeline",
                      features: [
                        "Stage 1: Static analysis (syntax, types, linting)",
                        "Stage 2: Unit tests with coverage requirements",
                        "Stage 3: Integration tests for component interaction",
                        "Stage 4: E2E tests with visual regression",
                        "Stage 5: LLM judge for semantic correctness",
                      ],
                    },
                  ].map((section) => (
                    <Card
                      key={section.title}
                      className="bg-card/50 backdrop-blur"
                    >
                      <CardHeader>
                        <CardTitle className="font-display text-xl">
                          {section.title}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2">
                          {section.features.map((feature, i) => (
                            <li
                              key={i}
                              className="flex items-start gap-3 text-muted-foreground"
                            >
                              <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2" />
                              {feature}
                            </li>
                          ))}
                        </ul>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </motion.div>
            </section>

            {/* User Stories */}
            <section id="user-stories" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <Lightbulb className="w-6 h-6 text-accent" />
                  User Stories
                </h2>
                <div className="space-y-4">
                  {[
                    {
                      as: "Solo Developer",
                      want: "start a project before bed and wake up to working code",
                      so: "I can maximize my productive hours",
                    },
                    {
                      as: "Team Lead",
                      want: "assign routine refactoring tasks to an autonomous agent",
                      so: "my team can focus on complex architectural decisions",
                    },
                    {
                      as: "AI Researcher",
                      want: "extend the memory system with custom embeddings",
                      so: "I can experiment with different retrieval strategies",
                    },
                    {
                      as: "DevOps Engineer",
                      want: "integrate RALPH-AGI into our CI/CD pipeline",
                      so: "automated code improvements can be reviewed and merged",
                    },
                  ].map((story, i) => (
                    <Card
                      key={i}
                      className="bg-card/50 backdrop-blur border-l-4 border-l-primary"
                    >
                      <CardContent className="pt-6">
                        <p className="text-muted-foreground">
                          <span className="text-foreground font-medium">
                            As a {story.as}
                          </span>
                          , I want to {story.want},{" "}
                          <span className="text-primary">so that</span> {story.so}.
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </motion.div>
            </section>

            {/* Non-Functional Requirements */}
            <section id="non-functional" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6">
                  Non-Functional Requirements
                </h2>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border">
                        <th className="text-left py-3 px-4 font-medium">
                          Category
                        </th>
                        <th className="text-left py-3 px-4 font-medium">
                          Requirement
                        </th>
                        <th className="text-left py-3 px-4 font-medium">Target</th>
                      </tr>
                    </thead>
                    <tbody className="text-muted-foreground">
                      {[
                        ["Performance", "Loop iteration time", "< 60 seconds"],
                        ["Performance", "Memory query latency", "< 500ms"],
                        ["Reliability", "System uptime", "> 99.5%"],
                        ["Reliability", "Data durability", "> 99.99%"],
                        ["Security", "Sandbox isolation", "Container-level"],
                        ["Security", "Secret management", "Encrypted at rest"],
                        ["Scalability", "Concurrent projects", "10+ per instance"],
                        ["Scalability", "Memory storage", "100GB+ per project"],
                      ].map(([cat, req, target], i) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-3 px-4">{cat}</td>
                          <td className="py-3 px-4">{req}</td>
                          <td className="py-3 px-4 font-mono text-primary">
                            {target}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            </section>

            {/* Success Metrics */}
            <section id="success-metrics" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6">
                  Success Metrics
                </h2>
                <div className="grid md:grid-cols-2 gap-6">
                  {[
                    {
                      metric: "Task Completion Rate",
                      target: "> 80%",
                      desc: "Percentage of PRD features successfully implemented",
                    },
                    {
                      metric: "Stuck Rate",
                      target: "< 5%",
                      desc: "Percentage of iterations without measurable progress",
                    },
                    {
                      metric: "Token Efficiency",
                      target: "99% reduction",
                      desc: "Token savings from dynamic tool discovery",
                    },
                    {
                      metric: "Memory Recall Accuracy",
                      target: "> 90%",
                      desc: "Relevance of retrieved memories to current task",
                    },
                  ].map((item) => (
                    <Card
                      key={item.metric}
                      className="bg-card/50 backdrop-blur"
                    >
                      <CardHeader className="pb-2">
                        <CardTitle className="text-lg font-display">
                          {item.metric}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <p className="text-3xl font-bold text-primary mb-2">
                          {item.target}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {item.desc}
                        </p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </motion.div>
            </section>

            {/* Risks */}
            <section id="risks" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <AlertTriangle className="w-6 h-6 text-accent" />
                  Risks & Mitigations
                </h2>
                <div className="space-y-4">
                  {[
                    {
                      risk: "Infinite Loops",
                      impact: "High",
                      mitigation:
                        "Maximum iteration limits, stuck detection, automatic termination",
                    },
                    {
                      risk: "Context Overflow",
                      impact: "Medium",
                      mitigation:
                        "Aggressive summarization, memory tiering, dynamic tool loading",
                    },
                    {
                      risk: "Incorrect Code Generation",
                      impact: "High",
                      mitigation:
                        "Cascaded evaluation pipeline, Git rollback, human review gates",
                    },
                    {
                      risk: "API Rate Limits",
                      impact: "Medium",
                      mitigation:
                        "Exponential backoff, model fallback, request queuing",
                    },
                  ].map((item) => (
                    <Card
                      key={item.risk}
                      className="bg-card/50 backdrop-blur"
                    >
                      <CardContent className="pt-6">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <h4 className="font-medium mb-1">{item.risk}</h4>
                            <p className="text-sm text-muted-foreground">
                              {item.mitigation}
                            </p>
                          </div>
                          <span
                            className={`px-2 py-1 rounded text-xs font-medium ${
                              item.impact === "High"
                                ? "bg-destructive/20 text-destructive"
                                : "bg-accent/20 text-accent"
                            }`}
                          >
                            {item.impact}
                          </span>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </motion.div>
            </section>

            {/* Roadmap */}
            <section id="roadmap" className="mb-16 scroll-mt-8">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
              >
                <h2 className="font-display font-bold text-2xl mb-6 flex items-center gap-3">
                  <Clock className="w-6 h-6 text-primary" />
                  Implementation Roadmap
                </h2>
                <div className="space-y-6">
                  {[
                    {
                      phase: "Phase 1: MVP",
                      duration: "Weeks 1-4",
                      items: [
                        "Core Ralph Loop implementation",
                        "Basic PRD.json task management",
                        "Git-backed progress tracking",
                        "Simple evaluation (syntax + unit tests)",
                      ],
                    },
                    {
                      phase: "Phase 2: Memory",
                      duration: "Weeks 5-8",
                      items: [
                        "SQLite observation storage",
                        "Chroma vector integration",
                        "Memory injection pipeline",
                        "Session summarization",
                      ],
                    },
                    {
                      phase: "Phase 3: Tools",
                      duration: "Weeks 9-12",
                      items: [
                        "MCP CLI integration",
                        "Dynamic tool discovery",
                        "Tool caching layer",
                        "Custom tool registration",
                      ],
                    },
                    {
                      phase: "Phase 4: Polish",
                      duration: "Weeks 13-16",
                      items: [
                        "Full evaluation cascade",
                        "Monitoring dashboard",
                        "Documentation",
                        "Performance optimization",
                      ],
                    },
                  ].map((phase, i) => (
                    <div key={phase.phase} className="flex gap-6">
                      <div className="flex flex-col items-center">
                        <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center text-primary font-bold">
                          {i + 1}
                        </div>
                        {i < 3 && (
                          <div className="w-0.5 h-full bg-border mt-2" />
                        )}
                      </div>
                      <Card className="flex-1 bg-card/50 backdrop-blur">
                        <CardHeader className="pb-2">
                          <div className="flex items-center justify-between">
                            <CardTitle className="font-display">
                              {phase.phase}
                            </CardTitle>
                            <span className="text-sm text-muted-foreground">
                              {phase.duration}
                            </span>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <ul className="space-y-2">
                            {phase.items.map((item) => (
                              <li
                                key={item}
                                className="flex items-center gap-2 text-sm text-muted-foreground"
                              >
                                <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                                {item}
                              </li>
                            ))}
                          </ul>
                        </CardContent>
                      </Card>
                    </div>
                  ))}
                </div>
              </motion.div>
            </section>
          </div>
        </div>
      </div>
    </Layout>
  );
}
