import { motion } from "framer-motion";
import { Link } from "wouter";
import {
  TrendingUp,
  DollarSign,
  Target,
  FileText,
  Code,
  MessageSquare,
  Building2,
  Shield,
  Briefcase,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import Layout from "@/components/Layout";

/* Use Cases Page
 * Showcasing RALPH-AGI applications across industries
 * Focus on marketing, finance, insurance, and software development
 */

const marketingUseCases = [
  {
    icon: <TrendingUp className="w-6 h-6" />,
    title: "Content Marketing Automation",
    description: "Generate blog posts, social media content, and email campaigns based on trend analysis and audience insights.",
    example: "Ralph Wiggum Marketer: Automated content production from trend scouting to final drafts",
    roi: "Increased content output with consistent quality",
  },
  {
    icon: <Target className="w-6 h-6" />,
    title: "Campaign Analysis & Optimization",
    description: "Continuously analyze campaign performance, identify winning patterns, and generate optimization recommendations.",
    example: "Multi-agent system: TrendScout → Research → ProductAgent → MarketingAgent → Ralph (content producer)",
    roi: "Improved campaign performance insights",
  },
  {
    icon: <FileText className="w-6 h-6" />,
    title: "Ad Copy Generation",
    description: "Create hundreds of ad variations for A/B testing across platforms, optimized for different audience segments.",
    example: "Automated ad copy testing across Meta, Google, LinkedIn with performance tracking",
    roi: "Faster ad creation and iteration cycles",
  },
  {
    icon: <MessageSquare className="w-6 h-6" />,
    title: "Customer Communication",
    description: "Generate personalized email sequences, SMS campaigns, and chatbot responses based on customer behavior.",
    example: "Behavior-triggered campaigns with dynamic content personalization",
    roi: "Enhanced engagement through personalization",
  },
];

const financeUseCases = [
  {
    icon: <DollarSign className="w-6 h-6" />,
    title: "Lead Pricing Automation",
    description: "Automatically price leads based on quality scores, market conditions, and historical performance data.",
    example: "Real-time lead valuation for broker models with dynamic pricing based on conversion probability",
    roi: "Optimized pricing through data-driven insights",
  },
  {
    icon: <FileText className="w-6 h-6" />,
    title: "Financial Report Generation",
    description: "Automated quarterly reports, investment summaries, and compliance documentation with data validation.",
    example: "Multi-source data aggregation with automated fact-checking and regulatory compliance",
    roi: "Reduced time spent on report preparation",
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: "Risk Assessment",
    description: "Continuous monitoring and analysis of portfolio risk with automated alerts and recommendations.",
    example: "Real-time risk scoring with historical pattern analysis and predictive modeling",
    roi: "Improved early detection of risk events",
  },
];

const insuranceUseCases = [
  {
    icon: <Building2 className="w-6 h-6" />,
    title: "Claims Processing",
    description: "Automated claims analysis, fraud detection, and documentation generation with human oversight.",
    example: "Multi-stage verification: document analysis → fraud detection → payout calculation → approval workflow",
    roi: "Streamlined claims processing workflow",
  },
  {
    icon: <Target className="w-6 h-6" />,
    title: "Policy Personalization",
    description: "Generate customized policy recommendations based on customer profiles, risk factors, and market conditions.",
    example: "Dynamic policy generation with real-time pricing and coverage optimization",
    roi: "Better-matched policies for customers",
  },
  {
    icon: <MessageSquare className="w-6 h-6" />,
    title: "Customer Qualification",
    description: "Automated lead qualification and hot transfer system for ACA, Medicare, and specialty insurance products.",
    example: "Compliant data processing with multi-factor qualification before hot transfers",
    roi: "More efficient lead qualification",
  },
];

const softwareUseCases = [
  {
    icon: <Code className="w-6 h-6" />,
    title: "Autonomous Development",
    description: "Build features, fix bugs, and refactor code with minimal human intervention over extended periods.",
    example: "Multi-day development sessions with persistent memory and self-verification",
    roi: "Increased development velocity for routine tasks",
  },
  {
    icon: <FileText className="w-6 h-6" />,
    title: "Documentation Generation",
    description: "Automatically generate and maintain technical documentation, API references, and user guides.",
    example: "Code-to-docs pipeline with automatic updates on every commit",
    roi: "Documentation stays in sync with code",
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: "Code Review & Testing",
    description: "Automated code review, test generation, and quality assurance with cascaded evaluation.",
    example: "5-stage verification: syntax → linting → unit tests → integration tests → LLM judge",
    roi: "Earlier bug detection in development cycle",
  },
];

export default function UseCases() {
  return (
    <Layout>
      <div className="container py-12 max-w-6xl">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-12"
        >
          <div className="inline-block px-3 py-1 mb-4 text-xs font-medium rounded-full bg-primary/10 text-primary">
            Real-World Applications
          </div>
          <h1 className="text-4xl font-display font-bold mb-4 gradient-text">
            RALPH-AGI Use Cases
          </h1>
          <p className="text-xl text-muted-foreground max-w-3xl">
            From marketing automation to financial services, RALPH-AGI powers autonomous workflows across high-value industries.
          </p>
        </motion.div>

        {/* Highlighted Marketing Example */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.1 }}
          className="mb-12"
        >
          <Card className="border-primary/50 bg-gradient-to-br from-primary/5 to-transparent">
            <CardHeader>
              <div className="flex items-center gap-3 mb-2">
                <div className="p-2 rounded-lg bg-primary/20">
                  <TrendingUp className="w-6 h-6 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-2xl">Ralph Wiggum Marketer</CardTitle>
                  <CardDescription className="text-base">
                    Production-Ready Marketing Automation System
                  </CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-muted-foreground">
                A real-world implementation demonstrating how RALPH-AGI patterns power autonomous marketing workflows. 
                Multiple specialized agents feed data to a shared SQLite database, while Ralph continuously produces 
                high-quality content.
              </p>
              
              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg bg-background/50 border border-border">
                  <h4 className="font-semibold mb-2 flex items-center gap-2">
                    <Code className="w-4 h-4 text-primary" />
                    Architecture Pattern
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• <strong>Producer Agents:</strong> TrendScout, Research, Product/Marketing</li>
                    <li>• <strong>Shared Database:</strong> SQLite for async coordination</li>
                    <li>• <strong>Consumer Agent:</strong> Ralph produces final content</li>
                    <li>• <strong>Full Audit Trail:</strong> Every decision tracked</li>
                  </ul>
                </div>
                
                <div className="p-4 rounded-lg bg-background/50 border border-border">
                  <h4 className="font-semibold mb-2 flex items-center gap-2">
                    <Target className="w-4 h-4 text-primary" />
                    Business Impact
                  </h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    <li>• <strong>10x Content Output:</strong> Automated blog posts, social media</li>
                    <li>• <strong>Consistent Quality:</strong> Multi-stage verification</li>
                    <li>• <strong>Decoupled Operation:</strong> Agents work independently</li>
                    <li>• <strong>Scalable:</strong> Add agents without coordination complexity</li>
                  </ul>
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <a href="https://github.com/muratcankoylan/ralph-wiggum-marketer" target="_blank" rel="noopener noreferrer">
                  <Button variant="default">
                    GitHub Repository
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </a>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Industry Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <Tabs defaultValue="marketing" className="w-full">
            <TabsList className="grid w-full grid-cols-4 mb-8">
              <TabsTrigger value="marketing">Marketing</TabsTrigger>
              <TabsTrigger value="finance">Finance</TabsTrigger>
              <TabsTrigger value="insurance">Insurance</TabsTrigger>
              <TabsTrigger value="software">Software</TabsTrigger>
            </TabsList>

            <TabsContent value="marketing" className="space-y-6">
              <div className="prose prose-invert max-w-none mb-6">
                <h3>Marketing & Advertising Automation</h3>
                <p>
                  High-value industries like finance and insurance spend billions on marketing. RALPH-AGI enables 
                  autonomous content production, campaign optimization, and customer communication at scale—with 
                  consistent quality and full audit trails for compliance.
                </p>
              </div>
              <div className="grid md:grid-cols-2 gap-6">
                {marketingUseCases.map((useCase, index) => (
                  <Card key={index} className="hover:border-primary/50 transition-colors">
                    <CardHeader>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-primary/20">
                          {useCase.icon}
                        </div>
                        <CardTitle>{useCase.title}</CardTitle>
                      </div>
                      <CardDescription>{useCase.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="p-3 rounded-lg bg-muted/50 text-sm">
                        <strong className="text-primary">Example:</strong> {useCase.example}
                      </div>
                      <div className="text-sm font-semibold text-green-400">
                        📈 {useCase.roi}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="finance" className="space-y-6">
              <div className="prose prose-invert max-w-none mb-6">
                <h3>Financial Services Automation</h3>
                <p>
                  From lead pricing to risk assessment, RALPH-AGI brings autonomous intelligence to financial operations. 
                  Built-in verification ensures accuracy, while persistent memory enables complex multi-day analyses.
                </p>
              </div>
              <div className="grid md:grid-cols-2 gap-6">
                {financeUseCases.map((useCase, index) => (
                  <Card key={index} className="hover:border-primary/50 transition-colors">
                    <CardHeader>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-primary/20">
                          {useCase.icon}
                        </div>
                        <CardTitle>{useCase.title}</CardTitle>
                      </div>
                      <CardDescription>{useCase.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="p-3 rounded-lg bg-muted/50 text-sm">
                        <strong className="text-primary">Example:</strong> {useCase.example}
                      </div>
                      <div className="text-sm font-semibold text-green-400">
                        📈 {useCase.roi}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="insurance" className="space-y-6">
              <div className="prose prose-invert max-w-none mb-6">
                <h3>Insurance Industry Applications</h3>
                <p>
                  Insurance operations demand accuracy, compliance, and speed. RALPH-AGI automates claims processing, 
                  policy generation, and customer qualification while maintaining full audit trails for regulatory compliance.
                </p>
              </div>
              <div className="grid md:grid-cols-2 gap-6">
                {insuranceUseCases.map((useCase, index) => (
                  <Card key={index} className="hover:border-primary/50 transition-colors">
                    <CardHeader>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-primary/20">
                          {useCase.icon}
                        </div>
                        <CardTitle>{useCase.title}</CardTitle>
                      </div>
                      <CardDescription>{useCase.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="p-3 rounded-lg bg-muted/50 text-sm">
                        <strong className="text-primary">Example:</strong> {useCase.example}
                      </div>
                      <div className="text-sm font-semibold text-green-400">
                        📈 {useCase.roi}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>

            <TabsContent value="software" className="space-y-6">
              <div className="prose prose-invert max-w-none mb-6">
                <h3>Software Development Automation</h3>
                <p>
                  The original RALPH-AGI use case: autonomous software development with persistent memory, 
                  self-verification, and git-backed progress tracking. Build features, fix bugs, and maintain 
                  codebases with minimal human intervention.
                </p>
              </div>
              <div className="grid md:grid-cols-2 gap-6">
                {softwareUseCases.map((useCase, index) => (
                  <Card key={index} className="hover:border-primary/50 transition-colors">
                    <CardHeader>
                      <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 rounded-lg bg-primary/20">
                          {useCase.icon}
                        </div>
                        <CardTitle>{useCase.title}</CardTitle>
                      </div>
                      <CardDescription>{useCase.description}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div className="p-3 rounded-lg bg-muted/50 text-sm">
                        <strong className="text-primary">Example:</strong> {useCase.example}
                      </div>
                      <div className="text-sm font-semibold text-green-400">
                        📈 {useCase.roi}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </TabsContent>
          </Tabs>
        </motion.div>

        {/* CTA Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-16 text-center"
        >
          <Card className="border-primary/50 bg-gradient-to-br from-primary/5 to-transparent">
            <CardContent className="py-12">
              <h2 className="text-3xl font-display font-bold mb-4">
                Ready to Build Your Own Use Case?
              </h2>
              <p className="text-muted-foreground mb-6 max-w-2xl mx-auto">
                RALPH-AGI's modular architecture adapts to any industry. Start with the PRD and architecture docs 
                to understand how to apply these patterns to your specific needs.
              </p>
              <div className="flex gap-4 justify-center">
                <Link href="/prd">
                  <Button size="lg" variant="default">
                    View PRD
                    <ArrowRight className="w-4 h-4 ml-2" />
                  </Button>
                </Link>
                <Link href="/architecture">
                  <Button size="lg" variant="outline">
                    Technical Architecture
                  </Button>
                </Link>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </Layout>
  );
}
