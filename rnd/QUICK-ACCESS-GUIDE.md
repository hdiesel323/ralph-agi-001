# R&D Quick Access Guide

**For accessing R&D workspace from any terminal session**

---

## 🚀 One-Time Setup

### Step 1: Clone the Repository

```bash
cd ~
git clone https://github.com/hdiesel323/ralph-agi-001.git
```

### Step 2: Create an Alias (Optional but Recommended)

Add this to your `~/.bashrc` or `~/.zshrc`:

```bash
# RALPH-AGI R&D Workspace
alias rnd='cd ~/ralph-agi-001/rnd'
alias rnd-questions='cd ~/ralph-agi-001/rnd/questions'
alias rnd-planning='cd ~/ralph-agi-001/rnd/planning'
alias rnd-decisions='cd ~/ralph-agi-001/rnd/decisions'
```

Then reload your shell:

```bash
source ~/.bashrc  # or source ~/.zshrc
```

---

## 📋 Daily Usage

### Access R&D Workspace

```bash
# If you set up the alias:
rnd

# Or without alias:
cd ~/ralph-agi-001/rnd
```

### View Current Sprint

```bash
rnd
cat planning/sprint-01-poc.md
```

### Ask a Question

```bash
rnd-questions
cp TEMPLATE.md 2026-01-10-my-question.md
nano 2026-01-10-my-question.md  # or vim, code, etc.
```

### Document a Decision

```bash
rnd-decisions
cp TEMPLATE.md 002-my-decision.md
nano 002-my-decision.md
```

### Check Open Questions

```bash
rnd-questions
ls -l | grep -v ANSWERED
```

---

## 🔄 Sync with Team

### Pull Latest Changes

```bash
cd ~/ralph-agi-001
git pull origin main
```

### Push Your Changes

```bash
cd ~/ralph-agi-001
git add rnd/
git commit -m "rnd: Add question about context window limits"
git push origin main
```

---

## 📁 Quick Navigation

| Command | Destination |
| :--- | :--- |
| `rnd` | Main R&D workspace |
| `rnd-questions` | Questions folder |
| `rnd-planning` | Planning folder |
| `rnd-decisions` | Decisions folder |
| `cd ~/ralph-agi-001/rnd/research` | Research folder |
| `cd ~/ralph-agi-001/rnd/meeting-notes` | Meeting notes |
| `cd ~/ralph-agi-001/rnd/implementation` | Implementation checklists |

---

## 💡 Pro Tips

### Search for Keywords

```bash
# Find all mentions of "memory system"
cd ~/ralph-agi-001/rnd
grep -r "memory system" .
```

### List Recent Files

```bash
# Show files modified in the last 7 days
cd ~/ralph-agi-001/rnd
find . -type f -mtime -7 -ls
```

### View File Tree

```bash
cd ~/ralph-agi-001/rnd
tree
```

### Quick Edit in VS Code

```bash
cd ~/ralph-agi-001/rnd
code .
```

---

## 🆘 Troubleshooting

### "Repository not found"

```bash
# Make sure you've cloned the repo
cd ~
git clone https://github.com/hdiesel323/ralph-agi-001.git
```

### "Permission denied"

```bash
# Make sure you have access to the repository
# Contact the repo owner to be added as a collaborator
```

### "Alias not working"

```bash
# Make sure you've reloaded your shell
source ~/.bashrc  # or source ~/.zshrc

# Or open a new terminal window
```

---

## 📞 Need Help?

- Check the main README: `cat ~/ralph-agi-001/rnd/README.md`
- Ask in the questions folder: `rnd-questions`
- Contact the team lead
