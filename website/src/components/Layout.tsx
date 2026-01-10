import { useState } from "react";
import { Link, useLocation } from "wouter";
import { motion, AnimatePresence } from "framer-motion";
import {
  Brain,
  BookOpen,
  Cpu,
  Rocket,
  Briefcase,
  Menu,
  X,
  Github,
  ChevronRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";

/* Layout Component - Obsidian Vault Design
 * - Collapsible sidebar navigation
 * - Full-width reading mode with centered content
 * - Floating table of contents for long documents
 */

interface NavItem {
  title: string;
  href: string;
  icon: React.ReactNode;
  description: string;
}

const navItems: NavItem[] = [
  {
    title: "Overview",
    href: "/",
    icon: <Brain className="w-5 h-5" />,
    description: "Introduction to RALPH-AGI",
  },
  {
    title: "PRD",
    href: "/prd",
    icon: <BookOpen className="w-5 h-5" />,
    description: "Product Requirements Document",
  },
  {
    title: "Architecture",
    href: "/architecture",
    icon: <Cpu className="w-5 h-5" />,
    description: "Technical Architecture",
  },
  {
    title: "Getting Started",
    href: "/getting-started",
    icon: <Rocket className="w-5 h-5" />,
    description: "Quick Start Guide",
  },
  {
    title: "Use Cases",
    href: "/use-cases",
    icon: <Briefcase className="w-5 h-5" />,
    description: "Real-World Applications",
  },
];

interface LayoutProps {
  children: React.ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [location] = useLocation();

  return (
    <div className="min-h-screen bg-background">
      {/* Mobile Header */}
      <header className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="flex items-center justify-between px-4 h-16">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center glow-purple">
              <Brain className="w-5 h-5 text-primary" />
            </div>
            <span className="font-display font-bold text-lg">RALPH-AGI</span>
          </Link>
          <div className="flex items-center gap-2">
            <a
              href="https://github.com/hdiesel323/ralph-agi-001"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="ghost" size="icon">
                <Github className="w-5 h-5" />
              </Button>
            </a>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarOpen(!sidebarOpen)}
            >
              {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </Button>
          </div>
        </div>
      </header>

      {/* Mobile Sidebar Overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="lg:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={`
          fixed top-0 left-0 z-50 h-full w-72 bg-sidebar border-r border-sidebar-border
          transform transition-transform duration-300 ease-out
          lg:translate-x-0
          ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
        `}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="p-6 border-b border-sidebar-border">
            <Link href="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center glow-purple">
                <Brain className="w-6 h-6 text-primary" />
              </div>
              <div>
                <h1 className="font-display font-bold text-lg text-sidebar-foreground">
                  RALPH-AGI
                </h1>
                <p className="text-xs text-muted-foreground">Documentation</p>
              </div>
            </Link>
          </div>

          {/* Navigation */}
          <ScrollArea className="flex-1 px-4 py-6">
            <nav className="space-y-2">
              {navItems.map((item) => {
                const isActive = location === item.href;
                return (
                  <Link key={item.href} href={item.href}>
                    <motion.div
                      whileHover={{ x: 4 }}
                      className={`
                        group flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200
                        ${
                          isActive
                            ? "bg-sidebar-accent text-sidebar-accent-foreground glow-purple"
                            : "text-sidebar-foreground hover:bg-sidebar-accent/50"
                        }
                      `}
                      onClick={() => setSidebarOpen(false)}
                    >
                      <span
                        className={`
                          ${isActive ? "text-primary" : "text-muted-foreground group-hover:text-primary"}
                          transition-colors
                        `}
                      >
                        {item.icon}
                      </span>
                      <div className="flex-1">
                        <p className="font-medium text-sm">{item.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {item.description}
                        </p>
                      </div>
                      <ChevronRight
                        className={`
                          w-4 h-4 transition-all duration-200
                          ${isActive ? "opacity-100 text-primary" : "opacity-0 group-hover:opacity-50"}
                        `}
                      />
                    </motion.div>
                  </Link>
                );
              })}
            </nav>
          </ScrollArea>

          {/* Footer */}
          <div className="p-4 border-t border-sidebar-border">
            <a
              href="https://github.com/hdiesel323/ralph-agi-001"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-muted-foreground hover:text-foreground hover:bg-sidebar-accent/50 transition-all"
            >
              <Github className="w-5 h-5" />
              <span className="text-sm">View on GitHub</span>
            </a>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:pl-72 pt-16 lg:pt-0 min-h-screen">
        {children}
      </main>
    </div>
  );
}
