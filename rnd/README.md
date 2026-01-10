# RALPH-AGI R&D Workspace

**Purpose:** Central knowledge base and collaboration workspace for the RALPH-AGI development team.

---

## 📁 Folder Structure

```
rnd/
├── README.md                    # This file - start here
├── questions/                   # Team questions and answers
│   ├── README.md
│   └── YYYY-MM-DD-question-title.md
├── planning/                    # Sprint planning and task breakdown
│   ├── README.md
│   ├── sprint-01-poc.md
│   └── sprint-02-foundation.md
├── decisions/                   # Architecture Decision Records (ADRs)
│   ├── README.md
│   └── 001-two-agent-architecture.md
├── research/                    # Research notes and experiments
│   ├── README.md
│   └── experiment-tldr-analysis.md
├── meeting-notes/              # Team meeting notes
│   ├── README.md
│   └── YYYY-MM-DD-standup.md
└── implementation/             # Implementation guides and checklists
    ├── README.md
    └── phase-1-poc-checklist.md
```

---

## 🚀 Quick Start

### Access from Any Terminal

```bash
# Clone the repository
git clone https://github.com/hdiesel323/ralph-agi-001.git
cd ralph-agi-001/rnd

# View this README
cat README.md

# List all questions
ls questions/

# Add a new question
cp questions/TEMPLATE.md questions/2026-01-10-my-question.md
# Edit the file and commit
```

### Workflow

1. **Ask a Question:** Create a file in `questions/` using the template
2. **Plan a Sprint:** Create a file in `planning/` for each sprint
3. **Document a Decision:** Create an ADR in `decisions/`
4. **Share Research:** Add notes to `research/`
5. **Record Meetings:** Add notes to `meeting-notes/`
6. **Track Implementation:** Use checklists in `implementation/`

---

## 📋 Templates

Each folder has a `TEMPLATE.md` file. Copy it to create new documents:

```bash
# Example: Create a new question
cp rnd/questions/TEMPLATE.md rnd/questions/2026-01-10-how-to-handle-git-conflicts.md

# Example: Create a new sprint plan
cp rnd/planning/TEMPLATE.md rnd/planning/sprint-03-memory-layer.md
```

---

## 🤝 Collaboration Guidelines

### Naming Conventions

- **Questions:** `YYYY-MM-DD-question-title.md`
- **Planning:** `sprint-XX-phase-name.md`
- **Decisions:** `XXX-decision-title.md` (numbered)
- **Research:** `experiment-name.md` or `research-topic.md`
- **Meeting Notes:** `YYYY-MM-DD-meeting-type.md`
- **Implementation:** `phase-X-checklist.md`

### Commit Messages

```bash
# Good commit messages
git commit -m "rnd: Add question about memory system scalability"
git commit -m "rnd: Document decision to use SQLite for medium-term memory"
git commit -m "rnd: Add sprint 1 planning document"

# Bad commit messages
git commit -m "update"
git commit -m "stuff"
```

### Review Process

1. Create your document in the appropriate folder
2. Commit and push to a feature branch
3. Create a pull request
4. Tag relevant team members for review
5. Merge after approval

---

## 📊 Current Status

| Phase | Status | Sprint | Folder |
| :--- | :--- | :--- | :--- |
| Phase 0: Pre-Launch | ✅ Complete | - | - |
| Phase 1: PoC | 🔄 In Progress | Sprint 1 | `planning/sprint-01-poc.md` |
| Phase 2: Foundation | ⏳ Planned | Sprint 2-3 | `planning/sprint-02-foundation.md` |
| Phase 3: Memory Layer | ⏳ Planned | Sprint 4-5 | - |
| Phase 4: Specialization | ⏳ Planned | Sprint 6-7 | - |
| Phase 5: Safety | ⏳ Planned | Sprint 8 | - |
| Phase 6: Scale | ⏳ Planned | Sprint 9-12 | - |

---

## 🔗 Related Documentation

- **Main Docs:** `../DOCUMENTATION-INDEX.md`
- **PRD:** `../RALPH-AGI-PRODUCT-REQUIREMENTS-DOCUMENT.md`
- **Architecture:** `../RALPH-AGI-TECHNICAL-ARCHITECTURE.md`
- **Roadmap:** `../RALPH-AGI-IMPLEMENTATION-ROADMAP.md`
- **Developer Guide:** `../RALPH-AGI-DEVELOPER-GUIDE.md`

---

## 💡 Tips

### For New Team Members

1. Read the main `DOCUMENTATION-INDEX.md`
2. Review the `PRD` and `Technical Architecture`
3. Check `questions/` for common questions
4. Review recent `meeting-notes/`
5. Look at current sprint in `planning/`

### For Daily Work

```bash
# Start of day: Pull latest changes
git pull origin main

# Check current sprint
cat rnd/planning/sprint-01-poc.md

# Check open questions
ls rnd/questions/ | grep -v ANSWERED

# End of day: Commit your work
git add rnd/
git commit -m "rnd: Add research notes on hooks system"
git push origin feature/my-work
```

### For Terminal Access in Other Sessions

```bash
# From anywhere, access the R&D workspace
cd ~/ralph-agi-001/rnd

# Or set an alias in your ~/.bashrc or ~/.zshrc
alias rnd='cd ~/ralph-agi-001/rnd'

# Then just type:
rnd
```

---

## 📞 Support

- **GitHub Issues:** For bugs and feature requests
- **Questions Folder:** For technical questions
- **Meeting Notes:** For team discussions
- **Slack/Discord:** For real-time communication (if applicable)

---

## 📝 License

All R&D documentation is internal and confidential. Do not share outside the team without approval.
