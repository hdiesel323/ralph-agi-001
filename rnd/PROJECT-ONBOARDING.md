# RALPH-AGI: Project Onboarding

**Purpose:** Quick reference for onboarding new team members, AI assistants, or tools to the RALPH-AGI project.

**Use this when:**

- Setting up a new AI assistant (Claude, GPT, etc.)
- Onboarding a new developer
- Configuring automated tools
- Answering "What is this project?" questions

---

## Quick Summary

**RALPH-AGI** is an autonomous AI agent system that enables LLMs to complete long-horizon, complex tasks in software development, marketing, and business operations with minimal human supervision.

---

## What problem are you solving?

Current autonomous AI agents fail at long-running tasks due to **context loss**, **lack of long-term memory**, **premature task completion**, and **inability to self-correct**. Even frontier LLMs like Claude 4.5 and GPT-4.1 struggle with multi-day projects that require maintaining coherent understanding across large codebases.

RALPH-AGI solves this by providing a robust architectural harness that enables LLMs to achieve true long-horizon autonomy through:

- Persistent loops (Ralph Wiggum Pattern)
- Multi-layer memory (short, medium, long-term)
- Event-driven automation (hooks system)
- Cascaded evaluation (5-stage quality pipeline)

---

## Who is this for?

### Primary Personas

**1. Alex, the Startup CTO**

- Manages a small, agile engineering team
- Needs to accelerate development velocity 3x with limited resources
- Wants to automate code reviews, documentation, and testing

**2. Maria, the Marketing Manager**

- Runs campaigns for a financial services company
- Needs to produce high-quality, compliant content at scale
- Wants to ensure brand consistency and regulatory compliance

**3. David, the Lead Broker**

- Runs a lead generation business
- Needs to automate lead pricing, qualification, and distribution
- Wants to improve lead conversion rates and margins

---

## What's the vision?

An autonomous agent that can:

- **Code for days** without human intervention
- **Remember every conversation** and learn from mistakes
- **Complete complex, multi-step tasks** in software development, marketing, and business operations
- **Deliver production-quality work** with proper testing and verification
- **Operate at a fraction of the cost** of human labor

### The Ultimate Vision

Give the agent a task on Friday night, wake up Monday morning to:

- 50+ commits
- All tests passing
- Production-ready code
- Cost: $297 in API costs (proven by Ralph Wiggum: $50k contract for $297)

---

## What stage is it in?

**Current Stage:** Planning Complete, Ready for Implementation (Phase 1: PoC)

### ✅ What's Done

- Comprehensive research of 9 reference implementations:
  1. Anthropic Official Guidance (Nov 2025)
  2. AI-Long-Task (AlphaEvolve-inspired)
  3. Continuous-Claude-v3 (2k⭐, 133 forks)
  4. Ralph Wiggum Marketer (276⭐)
  5. Ralph Wiggum Pattern ($50k for $297)
  6. Beads (9.4k⭐)
  7. Claude-Mem (12.9k⭐)
  8. MCP-CLI
  9. Anthropic Harnesses

- Complete Product Requirements Document (PRD)
- Technical Architecture with system diagrams
- API Specification
- 12-week Implementation Roadmap
- Developer Guide
- Documentation website (live)
- Twitter build-in-public strategy
- GitHub repository with all documentation
- R&D workspace for team collaboration

### 🔄 What's Next

**Week 1 (Current):** Build Proof of Concept

- Implement basic Ralph Wiggum loop
- Test with 3-5 simple coding tasks
- Validate API integrations

**Weeks 2-3:** Foundation

- Two-agent architecture (Initializer + Coding Agent)
- Beads integration (dependency-aware tasks)
- Git-first workflow

**Weeks 4-5:** Memory Layer

- SQLite (medium-term memory)
- ChromaDB (long-term memory)
- Automatic learning extraction

**Weeks 6-7:** Agent Specialization

- Testing Agent
- QA Agent
- Code Cleanup Agent
- Multi-agent coordination

**Week 8:** Safety & Verification

- 5-stage cascaded evaluation pipeline
- File claims tracking

**Weeks 9-12:** Scale & Optimize

- TLDR code analysis (95% token savings)
- Claude Code Plugin
- Cost monitoring dashboard

---

## Key Technical Details

### Architecture

**Two-Agent System:**

1. **Initializer Agent** - Sets up environment (runs once)
2. **Coding Agent** - Implements features (loops)

**Supporting Systems:**

- **Memory System:** Short (context), Medium (SQLite), Long (ChromaDB)
- **Hooks System:** 30+ automatic behaviors at lifecycle points
- **Beads Task Graph:** Dependency-aware execution
- **Shared Database:** Multi-agent coordination via SQLite
- **Git-First Workflow:** Automatic commits after each feature

### Technology Stack

| Layer              | Technology           | Rationale                                  |
| :----------------- | :------------------- | :----------------------------------------- |
| Language           | Python 3.11+         | Rich AI/ML ecosystem                       |
| LLM                | Claude 4.5 / GPT-4.1 | Frontier models with large context         |
| Database           | SQLite, ChromaDB     | Structured + vector search                 |
| Version Control    | Git                  | Industry standard, robust state management |
| Browser Automation | Puppeteer (MCP-CLI)  | E2E testing, web interaction               |
| Deployment         | Docker               | Containerization                           |

### Unique Differentiators

- Built on **Anthropic's official engineering guidance** (Nov 2025)
- Combines **8 battle-tested open-source patterns**
- **95% token savings** via TLDR code analysis
- **Proven ROI model:** $50k for $297 (Ralph Wiggum)
- **Multi-domain applicability:** Software, marketing, finance, insurance

---

## Project Goals

### Success Metrics

- **Task Completion Rate:** >90% without human intervention
- **Cost per Task:** <$10 for standard development tasks
- **Human Intervention Rate:** <1 intervention per 10 features
- **Community Engagement:** 1000+ GitHub stars, 5000+ Twitter followers

### Phase Goals

| Phase                   | Duration   | Key Deliverables                     |
| :---------------------- | :--------- | :----------------------------------- |
| Phase 1: PoC            | Week 1     | Basic Ralph loop, 3-5 tasks complete |
| Phase 2: Foundation     | Weeks 2-3  | Two-agent architecture, Beads        |
| Phase 3: Memory         | Weeks 4-5  | SQLite + ChromaDB integration        |
| Phase 4: Specialization | Weeks 6-7  | Testing, QA, Cleanup agents          |
| Phase 5: Safety         | Week 8     | 5-stage evaluation pipeline          |
| Phase 6: Scale          | Weeks 9-12 | TLDR, plugin, cost monitoring        |

---

## Repository Information

**GitHub:** https://github.com/hdiesel323/ralph-agi-001

**Key Documentation:**

- `DOCUMENTATION-INDEX.md` - Start here
- `RALPH-AGI-PRODUCT-REQUIREMENTS-DOCUMENT.md` - Complete PRD
- `RALPH-AGI-TECHNICAL-ARCHITECTURE.md` - System architecture
- `RALPH-AGI-IMPLEMENTATION-ROADMAP.md` - 12-week plan
- `RALPH-AGI-DEVELOPER-GUIDE.md` - Developer tutorial
- `rnd/` - R&D workspace (this folder)

**Documentation Website:** https://3000-i1wlhoo22mockh1l4bgho-90b8cf24.us2.manus.computer

---

## Immediate Next Steps

### For Developers

1. Clone the repository: `git clone https://github.com/hdiesel323/ralph-agi-001.git`
2. Set up Python 3.11+ environment
3. Install dependencies: `pip install -r requirements.txt`
4. Configure API keys in `.env`
5. Review `rnd/planning/sprint-01-poc.md`
6. Start implementing tasks

### For AI Assistants

1. Read this document (PROJECT-ONBOARDING.md)
2. Review the PRD: `RALPH-AGI-PRODUCT-REQUIREMENTS-DOCUMENT.md`
3. Review the Technical Architecture: `RALPH-AGI-TECHNICAL-ARCHITECTURE.md`
4. Check current sprint: `rnd/planning/sprint-01-poc.md`
5. Ask questions in: `rnd/questions/`

### For Stakeholders

1. Read the PRD for vision and requirements
2. Review the Implementation Roadmap for timeline
3. Check the Twitter SOP for build-in-public strategy

---

## Build-in-Public Strategy

We're building this in public over 12 weeks with weekly progress updates on Twitter.

**Launch announcement highlights:**

- Analysis of 9 autonomous agent systems
- Built on Anthropic's official guidance + 8 battle-tested patterns
- 12-week roadmap with transparent metrics
- Open-source, community-driven development

**Target:** Create a viral build-in-public campaign that attracts contributors, early adopters, and potential customers/investors.

---

## Quick Reference

### File Structure

```
ralph-agi-001/
├── DOCUMENTATION-INDEX.md          # Start here
├── RALPH-AGI-PRODUCT-REQUIREMENTS-DOCUMENT.md
├── RALPH-AGI-TECHNICAL-ARCHITECTURE.md
├── RALPH-AGI-IMPLEMENTATION-ROADMAP.md
├── RALPH-AGI-DEVELOPER-GUIDE.md
├── COMPREHENSIVE_ANALYSIS_V2.md
├── rnd/                            # R&D workspace
│   ├── PROJECT-ONBOARDING.md       # This file
│   ├── questions/                  # Team Q&A
│   ├── planning/                   # Sprint planning
│   ├── decisions/                  # Architecture decisions
│   ├── research/                   # Research notes
│   ├── meeting-notes/             # Team meetings
│   └── implementation/            # Implementation checklists
└── client/                         # Documentation website
```

### Key Commands

```bash
# Access R&D workspace
cd ~/ralph-agi-001/rnd

# View current sprint
cat rnd/planning/sprint-01-poc.md

# Ask a question
cd rnd/questions
cp TEMPLATE.md 2026-01-11-my-question.md

# Document a decision
cd rnd/decisions
cp TEMPLATE.md 002-my-decision.md
```

---

## Contact & Support

- **GitHub Issues:** https://github.com/hdiesel323/ralph-agi-001/issues
- **Twitter:** @hdiesel323
- **R&D Questions:** `rnd/questions/`

---

**Last Updated:** 2026-01-10
**Version:** 1.0
