import { Toaster } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import NotFound from "@/pages/NotFound";
import { Route, Switch } from "wouter";
import ErrorBoundary from "./components/ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import Home from "./pages/Home";
import PRD from "./pages/PRD";
import Architecture from "./pages/Architecture";
import GettingStarted from "./pages/GettingStarted";
import UseCases from "./pages/UseCases";
import Enterprise from "./pages/Enterprise";
import Dashboard from "./pages/Dashboard";

function Router() {
  return (
    <Switch>
      <Route path="/" component={Home} />
      <Route path="/dashboard" component={Dashboard} />
      <Route path="/prd" component={PRD} />
      <Route path="/architecture" component={Architecture} />
      <Route path="/getting-started" component={GettingStarted} />
      <Route path="/use-cases" component={UseCases} />
      <Route path="/enterprise" component={Enterprise} />
      <Route path="/404" component={NotFound} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider defaultTheme="dark" switchable={true}>
        <TooltipProvider>
          <Toaster />
          <Router />
        </TooltipProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}

export default App;
