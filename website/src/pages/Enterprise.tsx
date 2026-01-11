import { useState } from "react";
import { motion } from "framer-motion";
import { Link } from "wouter";
import {
  Building2,
  Cloud,
  Shield,
  BarChart3,
  Headphones,
  Wrench,
  DollarSign,
  CheckCircle2,
  ArrowLeft,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import Layout from "@/components/Layout";

const enterpriseFeatures = [
  {
    icon: <Cloud className="w-5 h-5" />,
    title: "Hosted Cloud Version",
    description: "No setup required - get started in minutes with our managed infrastructure",
  },
  {
    icon: <Shield className="w-5 h-5" />,
    title: "SSO/SAML Authentication",
    description: "Enterprise-grade security with single sign-on and SAML 2.0 support",
  },
  {
    icon: <BarChart3 className="w-5 h-5" />,
    title: "Team Dashboards & Analytics",
    description: "Track agent performance, task completion, and team productivity",
  },
  {
    icon: <Headphones className="w-5 h-5" />,
    title: "Priority Support & SLAs",
    description: "Dedicated support team with guaranteed response times",
  },
  {
    icon: <Wrench className="w-5 h-5" />,
    title: "Custom Integrations",
    description: "Connect RALPH-AGI to your existing tools and workflows",
  },
  {
    icon: <DollarSign className="w-5 h-5" />,
    title: "Flexible Pricing",
    description: "Subscription plans that scale with your team's needs",
  },
];

export default function Enterprise() {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);

    const form = e.currentTarget;
    const formData = new FormData(form);

    try {
      await fetch("/", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams(formData as any).toString(),
      });
      setSubmitted(true);
    } catch (error) {
      console.error("Form submission error:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout>
      {/* Header */}
      <section className="py-12 border-b border-border">
        <div className="container">
          <Link href="/">
            <Button variant="ghost" size="sm" className="mb-6">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Home
            </Button>
          </Link>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="w-12 h-12 rounded-xl bg-primary/20 flex items-center justify-center glow-purple">
                <Building2 className="w-6 h-6 text-primary" />
              </div>
              <h1 className="font-display font-bold text-3xl md:text-4xl">
                Enterprise Edition
              </h1>
            </div>
            <p className="text-muted-foreground text-lg max-w-2xl">
              For teams that need managed infrastructure, enterprise security, and dedicated support.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Main Content */}
      <section className="py-16">
        <div className="container">
          <div className="grid lg:grid-cols-2 gap-16">
            {/* Features Column */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.2 }}
            >
              <h2 className="font-display font-bold text-2xl mb-8">
                What's Included
              </h2>

              <div className="space-y-4">
                {enterpriseFeatures.map((feature, index) => (
                  <motion.div
                    key={feature.title}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.3 + index * 0.1 }}
                  >
                    <Card className="bg-card/50 border-border hover:border-primary/50 transition-colors">
                      <CardHeader className="pb-2">
                        <div className="flex items-center gap-3">
                          <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                            <span className="text-primary">{feature.icon}</span>
                          </div>
                          <CardTitle className="font-display text-base">
                            {feature.title}
                          </CardTitle>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <CardDescription>
                          {feature.description}
                        </CardDescription>
                      </CardContent>
                    </Card>
                  </motion.div>
                ))}
              </div>
            </motion.div>

            {/* Form Column */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.6, delay: 0.4 }}
            >
              <Card className="bg-card/80 backdrop-blur border-primary/20">
                <CardHeader>
                  <CardTitle className="font-display text-2xl">
                    Join the Waitlist
                  </CardTitle>
                  <CardDescription className="text-base">
                    Be the first to know when Enterprise Edition launches. Early access members get special pricing.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {submitted ? (
                    <motion.div
                      initial={{ opacity: 0, scale: 0.9 }}
                      animate={{ opacity: 1, scale: 1 }}
                      className="text-center py-8"
                    >
                      <div className="w-16 h-16 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4">
                        <CheckCircle2 className="w-8 h-8 text-green-500" />
                      </div>
                      <h3 className="font-display font-semibold text-xl mb-2">
                        You're on the list!
                      </h3>
                      <p className="text-muted-foreground">
                        We'll be in touch when Enterprise Edition is ready. Thanks for your interest!
                      </p>
                    </motion.div>
                  ) : (
                    <form
                      name="enterprise-waitlist"
                      method="POST"
                      data-netlify="true"
                      netlify-honeypot="bot-field"
                      onSubmit={handleSubmit}
                      className="space-y-6"
                    >
                      {/* Hidden fields for Netlify */}
                      <input type="hidden" name="form-name" value="enterprise-waitlist" />
                      <p className="hidden">
                        <label>
                          Don't fill this out if you're human: <input name="bot-field" />
                        </label>
                      </p>

                      <div className="grid sm:grid-cols-2 gap-4">
                        <div className="space-y-2">
                          <Label htmlFor="firstName">First Name *</Label>
                          <Input
                            id="firstName"
                            name="firstName"
                            placeholder="Jane"
                            required
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="lastName">Last Name *</Label>
                          <Input
                            id="lastName"
                            name="lastName"
                            placeholder="Smith"
                            required
                          />
                        </div>
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="email">Work Email *</Label>
                        <Input
                          id="email"
                          name="email"
                          type="email"
                          placeholder="jane@company.com"
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="company">Company Name *</Label>
                        <Input
                          id="company"
                          name="company"
                          placeholder="Acme Inc."
                          required
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="teamSize">Team Size</Label>
                        <Input
                          id="teamSize"
                          name="teamSize"
                          placeholder="e.g., 10-50 developers"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="useCase">How do you plan to use RALPH-AGI?</Label>
                        <Textarea
                          id="useCase"
                          name="useCase"
                          placeholder="Tell us about your use case..."
                          rows={3}
                        />
                      </div>

                      <Button
                        type="submit"
                        size="lg"
                        className="w-full glow-purple"
                        disabled={loading}
                      >
                        {loading ? (
                          <>
                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                            Submitting...
                          </>
                        ) : (
                          "Join the Waitlist"
                        )}
                      </Button>

                      <p className="text-xs text-muted-foreground text-center">
                        We respect your privacy. No spam, ever.
                      </p>
                    </form>
                  )}
                </CardContent>
              </Card>
            </motion.div>
          </div>
        </div>
      </section>
    </Layout>
  );
}
