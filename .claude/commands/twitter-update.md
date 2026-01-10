# Generate Daily Twitter Update

Generate two Twitter posts for today's RALPH-AGI build-in-public update.

## Instructions

1. Check recent git commits: `git log --oneline -5`
2. Check sprint progress: `_bmad-output/implementation-artifacts/sprint-status.yaml`
3. Review any completed stories or work

Then generate:

### VERSION 1: Everyone Can Understand
- No technical jargon
- Use analogies and metaphors
- Explain what it DOES, not how it works
- Keep it relatable and human
- End with progress indicator

### VERSION 2: Dev / Technical
- Technical details, metrics
- Code snippets if relevant
- Test counts, coverage percentages
- Specific implementations
- Link to GitHub repo
- Use #buildinpublic #AI hashtags

## Output Format

Provide copy-paste ready tweets clearly labeled:

```
💬 EVERYONE VERSION:
[tweet text]

💬 DEV VERSION:
[tweet text]
```

## Reference
- Main thread: https://x.com/hdiesel_/status/2009969887356256679
- GitHub: github.com/hdiesel323/ralph-agi-001
- SOP: RALPH-AGI-Twitter-SOP.md
