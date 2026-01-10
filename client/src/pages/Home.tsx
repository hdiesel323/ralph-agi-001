import { motion } from "framer-motion";
import { Link } from "wouter";
import {
  Brain,
  Cpu,
  Database,
  Zap,
  GitBranch,
  Shield,
  ArrowRight,
  Sparkles,
  Infinity,
  Layers,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Layout from "@/components/Layout";

/* Home Page - Obsidian Vault Design
 * - Hero section with neural network visualization
 * - Feature cards highlighting key capabilities
 * - Quick navigation to documentation sections
 */

const features = [
  {
    icon: <Infinity className="w-6 h-6" />,
    title: "Ralph Loop Engine",
    description:
      "Simple iterative execution pattern that processes one task at a time, preventing context overload and enabling long-horizon autonomy.",
    image: "/images/loop-engine.png",
  },
  {
    icon: <Database className="w-6 h-6" />,
    title: "Three-Tier Memory",
    description:
      "Persistent memory system with short-term (progress), medium-term (Git), and long-term (vector DB) storage for cross-session learning.",
    image: "/images/memory-system.png",
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: "Dynamic Tool Discovery",
    description:
      "MCP CLI integration for on-demand tool loading, reducing token usage by 99% compared to static tool definitions.",
    image: "/images/tool-registry.png",
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: "Cascaded Evaluation",
    description:
      "Five-stage verification pipeline from syntax checks to LLM judges, ensuring quality through progressive validation.",
    image: "/images/evaluation-pipeline.png",
  },
];

const capabilities = [
  {
    icon: <Brain className="w-5 h-5" />,
    title: "Long-horizon Autonomy",
    description: "Execute complex multi-step tasks over extended periods",
  },
  {
    icon: <GitBranch className="w-5 h-5" />,
    title: "Git-backed Progress",
    description: "Every action committed with automatic rollback capability",
  },
  {
    icon: <Layers className="w-5 h-5" />,
    title: "PRD-driven Tasks",
    description: "Structured task management with dependency tracking",
  },
  {
    icon: <Sparkles className="w-5 h-5" />,
    title: "Self-verification",
    description: "Automated testing and quality assurance at every step",
  },
];

export default function Home() {
  return (
    <Layout>
      {/* Hero Section */}
      <section className="relative min-h-[90vh] flex items-center overflow-hidden">
        {/* Background Image */}
        <div className="absolute inset-0 z-0">
          <img
            src="/images/hero-neural-network.png"
            alt="Neural Network Visualization"
            className="w-full h-full object-cover opacity-40"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-background/60 via-background/80 to-background" />
        </div>

        {/* Content */}
        <div className="container relative z-10 py-20">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="max-w-4xl"
          >
            {/* Badge */}
            <motion.div
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 border border-primary/20 mb-8"
            >
              <Sparkles className="w-4 h-4 text-primary" />
              <span className="text-sm font-medium text-primary">
                Autonomous AI Agent Framework
              </span>
            </motion.div>

            {/* Title */}
            <h1 className="font-display font-extrabold text-5xl md:text-7xl leading-tight mb-6">
              <span className="text-gradient-purple">RALPH</span>
              <span className="text-foreground">-AGI</span>
            </h1>

            {/* Subtitle */}
            <p className="text-xl md:text-2xl text-muted-foreground mb-4 font-display">
              Recursive Autonomous Long-horizon Processing
              <br />
              with Hierarchical AGI-like Intelligence
            </p>

            {/* Description */}
            <p className="text-lg text-muted-foreground/80 max-w-2xl mb-10 leading-relaxed">
              A comprehensive framework for building autonomous AI agents that can
              execute complex, multi-step tasks over extended periods with
              persistent memory, self-verification, and incremental learning.
            </p>

            {/* CTA Buttons */}
            <div className="flex flex-wrap gap-4">
              <Link href="/getting-started">
                <Button size="lg" className="glow-purple group">
                  Get Started
                  <ArrowRight className="w-4 h-4 ml-2 group-hover:translate-x-1 transition-transform" />
                </Button>
              </Link>
              <Link href="/prd">
                <Button size="lg" variant="outline">
                  Read the PRD
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Capabilities Grid */}
      <section className="py-20 border-t border-border">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display font-bold text-3xl md:text-4xl mb-4">
              AGI-like Capabilities
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              RALPH-AGI combines proven patterns from leading AI research to create
              a system that approaches general intelligence for software development tasks.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {capabilities.map((cap, index) => (
              <motion.div
                key={cap.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="h-full bg-card/50 backdrop-blur border-border hover:border-primary/50 transition-all duration-300 hover:glow-purple">
                  <CardHeader>
                    <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
                      <span className="text-primary">{cap.icon}</span>
                    </div>
                    <CardTitle className="font-display text-lg">
                      {cap.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-muted-foreground">
                      {cap.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Core Components */}
      <section className="py-20 bg-card/30">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-center mb-16"
          >
            <h2 className="font-display font-bold text-3xl md:text-4xl mb-4">
              Core Components
            </h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Four interconnected systems working together to enable autonomous,
              long-running AI agent operations.
            </p>
          </motion.div>

          <div className="grid lg:grid-cols-2 gap-8">
            {features.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="overflow-hidden bg-card/50 backdrop-blur border-border hover:border-primary/50 transition-all duration-300 group">
                  <div className="aspect-video relative overflow-hidden">
                    <img
                      src={feature.image}
                      alt={feature.title}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-card to-transparent" />
                  </div>
                  <CardHeader className="relative -mt-16 z-10">
                    <div className="flex items-center gap-4 mb-2">
                      <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center glow-purple">
                        <span className="text-primary">{feature.icon}</span>
                      </div>
                      <CardTitle className="font-display text-xl">
                        {feature.title}
                      </CardTitle>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-muted-foreground text-base leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 border-t border-border">
        <div className="container">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="max-w-3xl mx-auto text-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-primary/20 flex items-center justify-center mx-auto mb-8 glow-purple">
              <Cpu className="w-8 h-8 text-primary" />
            </div>
            <h2 className="font-display font-bold text-3xl md:text-4xl mb-6">
              Ready to Build AGI-like Agents?
            </h2>
            <p className="text-muted-foreground text-lg mb-10 leading-relaxed">
              Explore the complete Product Requirements Document and Technical
              Architecture to understand how RALPH-AGI can transform your AI
              development workflow.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              <Link href="/prd">
                <Button size="lg" className="glow-purple">
                  View Full PRD
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
              <Link href="/architecture">
                <Button size="lg" variant="outline">
                  Technical Architecture
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 border-t border-border">
        <div className="container">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
                <Brain className="w-5 h-5 text-primary" />
              </div>
              <span className="font-display font-semibold">RALPH-AGI</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Built with insights from Anthropic, Claude-Mem, Beads, and MCP CLI
            </p>
          </div>
        </div>
      </footer>
    </Layout>
  );
}
