# RALPH-AGI: BMAD Workflow & Naming Conventions

**Purpose:** To align our development process with the BMAD method for clean, accurate, and efficient collaboration.

**Source:** https://docs.bmad-method.org/

---

## 🎯 Guiding Principle

We will use the **BMAD Method track** for our development:

```
Phase 1 (Analysis) → Phase 2 (Planning) → Phase 3 (Solutioning) → Phase 4 (Implementation)
```

This ensures we have a robust process for our complex project.

---

## 📁 Naming Conventions

### **General Format:**

`YYYY-MM-DD_phase_topic_status.md`

- **YYYY-MM-DD:** Date of creation
- **phase:** `analysis`, `planning`, `solutioning`, `implementation`
- **topic:** Short, descriptive title (e.g., `context-window-limits`)
- **status:** `open`, `in-progress`, `answered`, `approved`, `done`

### **File Naming Examples:**

| BMAD Phase | Folder | File Name |
| :--- | :--- | :--- |
| **Analysis** | `research/` | `2026-01-10_analysis_tldr-code-analysis_done.md` |
| **Planning** | `planning/` | `2026-01-10_planning_sprint-01-poc_in-progress.md` |
| **Solutioning** | `decisions/` | `2026-01-10_solutioning_two-agent-architecture_approved.md` |
| **Implementation** | `implementation/` | `2026-01-10_implementation_poc-checklist_in-progress.md` |
| **Q&A** | `questions/` | `2026-01-10_solutioning_context-window-limits_open.md` |

**Why this format?**
- **Sortable:** Files are automatically sorted by date
- **Scannable:** Quickly see phase, topic, and status
- **Searchable:** Easy to find files with `grep` or `find`
- **Accurate:** Reflects BMAD phases

---

## 💬 Q&A Workflow (Back-and-Forth)

This is how we will handle our iterative Q&A process:

### **Step 1: Ask a Question**

1. **Create a file** in `rnd/questions/`:
   ```bash
   cd ~/ralph-agi-001/rnd/questions
   cp TEMPLATE.md 2026-01-11_solutioning_hooks-system-design_open.md
   ```

2. **Edit the file:**
   - Fill out the question and context
   - Set status to `Open`

3. **Commit and push:**
   ```bash
   git add .
   git commit -m "q: Ask about hooks system design"
   git push
   ```

### **Step 2: Provide an Answer**

1. **Edit the same file:**
   - Add your answer under the `## Answer` section
   - Change status to `Answered`

2. **Commit and push:**
   ```bash
   git add .
   git commit -m "a: Provide initial design for hooks system"
   git push
   ```

### **Step 3: Iterate (If Needed)**

1. **Add follow-up questions** in the same file under a new `## Follow-up` section
2. **Change status** back to `In-Progress`
3. **Commit and push**

### **Step 4: Finalize and Approve**

1. Once the discussion is complete, **document the final decision** under `## Decision`
2. **Change status** to `Approved`
3. **Rename the file** to include `_approved`:
   ```bash
   mv 2026-01-11_solutioning_hooks-system-design_open.md 2026-01-11_solutioning_hooks-system-design_approved.md
   ```

4. **Commit and push:**
   ```bash
   git add .
   git commit -m "q: Approve hooks system design"
   git push
   ```

---

## 📋 Commit Message Prefixes

To keep our git history clean and scannable:

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

## 🚀 Our Current BMAD Phase

We are currently in **Phase 3: Solutioning**.

**What this means:**
- We are making key technical decisions
- We are creating Architecture Decision Records (ADRs) in `rnd/decisions/`
- We are breaking down work into epics and stories in `rnd/planning/`
- We are using the Q&A workflow to resolve technical questions

**Next up:** Phase 4: Implementation

---

## 💡 How to Use This Guide

### **When you have a question:**
1. Go to `rnd/questions/`
2. Create a new file using the naming convention
3. Use the `q:` commit prefix

### **When you answer a question:**
1. Edit the existing question file
2. Use the `a:` commit prefix

### **When you plan a sprint:**
1. Go to `rnd/planning/`
2. Create a new file using the naming convention
3. Use the `plan:` commit prefix

### **When you make a decision:**
1. Go to `rnd/decisions/`
2. Create a new ADR file
3. Use the `sol:` commit prefix

---

## ✅ Summary

**File Naming:** `YYYY-MM-DD_phase_topic_status.md`

**Commit Prefixes:** `q:`, `a:`, `plan:`, `sol:`, `impl:`, `res:`, `meet:`, `docs:`

**Q&A Workflow:**
1. Create `_open.md` file
2. Edit to answer, change status to `Answered`
3. Iterate with `In-Progress` status
4. Finalize, change status to `Approved`, rename file to `_approved.md`

**Current Phase:** Phase 3: Solutioning

**This system will keep our R&D process clean, organized, and aligned with BMAD best practices.**
