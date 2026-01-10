# RALPH-AGI R&D Workspace

**Purpose:** Central knowledge base and collaboration workspace for the RALPH-AGI development team using the BMAD Method.

**BMAD Phase:** Phase 3: Solutioning → Phase 4: Implementation

---

## 📁 Folder Structure

```
rnd/
├── README.md                    # This file - start here
├── BMAD-WORKFLOW-GUIDE.md      # BMAD naming conventions and workflow
├── PROJECT-ONBOARDING.md       # Project overview for new team members
├── QUICK-ACCESS-GUIDE.md       # Terminal access guide
├── questions/                   # Team questions and answers
│   ├── README.md
│   ├── TEMPLATE.md
│   └── YYYY-MM-DD_phase_topic_status.md
├── planning/                    # Sprint planning and task breakdown
│   ├── README.md
│   ├── TEMPLATE.md
│   └── YYYY-MM-DD_planning_sprint-XX_status.md
├── decisions/                   # Architecture Decision Records (ADRs)
│   ├── README.md
│   ├── TEMPLATE.md
│   └── YYYY-MM-DD_solutioning_decision-title_status.md
├── research/                    # Research notes and experiments
│   ├── README.md
│   └── YYYY-MM-DD_analysis_topic_status.md
├── meeting-notes/              # Team meeting notes
│   ├── README.md
│   ├── TEMPLATE.md
│   └── YYYY-MM-DD_meet_meeting-type_done.md
└── implementation/             # Implementation guides and checklists
    ├── README.md
    └── YYYY-MM-DD_implementation_feature-name_status.md
```

---

## 🚀 Quick Start

### Access from Any Terminal

```bash
# Clone the repository (one-time)
git clone https://github.com/hdiesel323/ralph-agi-001.git
cd ralph-agi-001/rnd

# View this README
cat README.md

# View BMAD workflow guide
cat BMAD-WORKFLOW-GUIDE.md
```

### Set Up Aliases (Recommended)

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias rnd='cd ~/ralph-agi-001/rnd'
alias rnd-questions='cd ~/ralph-agi-001/rnd/questions'
alias rnd-planning='cd ~/ralph-agi-001/rnd/planning'
alias rnd-decisions='cd ~/ralph-agi-001/rnd/decisions'
```

Then reload: `source ~/.bashrc`

---

## 📋 Naming Conventions (BMAD-Aligned)

**Format:** `YYYY-MM-DD_phase_topic_status.md`

- **YYYY-MM-DD:** Date of creation
- **phase:** `analysis`, `planning`, `solutioning`, `implementation`
- **topic:** Short, descriptive title (e.g., `context-window-limits`)
- **status:** `open`, `in-progress`, `answered`, `approved`, `done`

**Examples:**
- `2026-01-10_solutioning_context-window-limits_open.md`
- `2026-01-10_planning_sprint-01-poc_in-progress.md`
- `2026-01-10_solutioning_two-agent-architecture_approved.md`

**See:** `BMAD-WORKFLOW-GUIDE.md` for complete details

---

## 💬 Q&A Workflow

### Ask a Question

```bash
cd ~/ralph-agi-001/rnd/questions
cp TEMPLATE.md 2026-01-11_solutioning_hooks-system_open.md
# Edit the file
git add .
git commit -m "q: Ask about hooks system design"
git push
```

### Answer a Question

```bash
# Edit the existing question file
# Add your answer under ## Answer section
# Change status to Answered
git add .
git commit -m "a: Provide hooks system design"
git push
```

### Finalize and Approve

```bash
# Document final decision under ## Decision
# Change status to Approved
mv 2026-01-11_solutioning_hooks-system_open.md 2026-01-11_solutioning_hooks-system_approved.md
git add .
git commit -m "q: Approve hooks system design"
git push
```

---

## 🏷️ Commit Message Prefixes

| Prefix | Meaning | Example |
| :--- | :--- | :--- |
| `q:` | Question | `q: Ask about memory system` |
| `a:` | Answer | `a: Propose SQLite + ChromaDB` |
| `plan:` | Planning | `plan: Create sprint 2 plan` |
| `sol:` | Solutioning | `sol: Document ADR for two-agent arch` |
| `impl:` | Implementation | `impl: Add checklist for PoC` |
| `res:` | Research | `res: Add notes on TLDR analysis` |
| `meet:` | Meeting | `meet: Add notes for 2026-01-11 standup` |
| `docs:` | Documentation | `docs: Update main README` |

---

## 📊 Current Status

**BMAD Phase:** Phase 3: Solutioning → Phase 4: Implementation

| Phase | Status | Current Work |
| :--- | :--- | :--- |
| Phase 1: Analysis | ✅ Complete | Research complete (9 implementations) |
| Phase 2: Planning | ✅ Complete | PRD, Architecture, Roadmap done |
| Phase 3: Solutioning | 🔄 In Progress | Creating ADRs, answering technical questions |
| Phase 4: Implementation | ⏳ Next | Sprint 01: PoC ready to start |

---

## 🔗 Related Documentation

- **Main Docs:** `../DOCUMENTATION-INDEX.md`
- **PRD:** `../RALPH-AGI-PRODUCT-REQUIREMENTS-DOCUMENT.md`
- **Architecture:** `../RALPH-AGI-TECHNICAL-ARCHITECTURE.md`
- **Roadmap:** `../RALPH-AGI-IMPLEMENTATION-ROADMAP.md`
- **Developer Guide:** `../RALPH-AGI-DEVELOPER-GUIDE.md`
- **BMAD Workflow:** `BMAD-WORKFLOW-GUIDE.md`
- **Project Onboarding:** `PROJECT-ONBOARDING.md`

---

## 💡 Tips

### For New Team Members

1. Read `PROJECT-ONBOARDING.md`
2. Read `BMAD-WORKFLOW-GUIDE.md`
3. Check current questions in `questions/`
4. Review current sprint in `planning/`
5. Read approved decisions in `decisions/`

### For Daily Work

```bash
# Start of day: Pull latest changes
cd ~/ralph-agi-001 && git pull origin main

# Check current sprint
cat rnd/planning/2026-01-10_planning_sprint-01-poc_in-progress.md

# Check open questions
ls rnd/questions/ | grep _open

# End of day: Commit your work
git add rnd/
git commit -m "q: Add question about memory system"
git push origin main
```

---

## 📞 Support

- **GitHub Issues:** https://github.com/hdiesel323/ralph-agi-001/issues
- **Questions Folder:** `rnd/questions/`
- **BMAD Docs:** https://docs.bmad-method.org/

---

## 📝 License

All R&D documentation is internal and confidential. Do not share outside the team without approval.
