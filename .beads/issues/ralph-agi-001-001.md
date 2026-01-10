---
id: ralph-agi-001-001
title: Daily Twitter Build Update
type: chore
status: open
priority: 2
labels: [build-in-public, twitter, recurring]
created: 2026-01-10
---

# Daily Twitter Build Update

## Purpose
Generate two Twitter posts each day to update followers on RALPH-AGI progress.

## Tweet Templates

### VERSION 1: Everyone Can Understand
```
[MILESTONE/UPDATE] ✅ [What happened in plain English]

What it does:
• [Simple explanation 1]
• [Simple explanation 2]
• [Simple explanation 3]

[Relatable analogy or metaphor]

Week [X]: [Progress] 🚀
```

### VERSION 2: Dev / Technical
```
[Technical milestone]:

• [Technical detail 1]
• [Technical detail 2]
• [Technical detail 3]
• [Metrics: tests, coverage, etc.]

github.com/hdiesel323/ralph-agi-001

#buildinpublic #AI
```

## Daily Process
1. Review what was accomplished today
2. Generate "Everyone" version (no jargon, use analogies)
3. Generate "Dev" version (technical details, metrics, code snippets)
4. Post "Everyone" version as main reply to thread
5. Post "Dev" version as follow-up reply

## Content Guidelines (from SOP)
- **Authenticity over Perfection** - share the messy middle
- **Visuals Amplify Reach** - use code screenshots (carbon.now.sh), diagrams
- **Best Times:** 10 AM - 5 PM, Tuesday-Thursday
- **Hashtags:** #buildinpublic #AI #AGI

## Command
Run: `generate-twitter-update` or ask Claude: "Generate today's Twitter update for RALPH-AGI"
