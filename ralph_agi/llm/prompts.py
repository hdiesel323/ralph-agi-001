"""Prompt templates for RALPH-AGI agents.

This module contains system prompts and helpers for the Builder and Critic
agents in the multi-agent architecture.
"""

from __future__ import annotations

from typing import Any, Optional


# =============================================================================
# Builder Agent System Prompt
# =============================================================================

BUILDER_SYSTEM_PROMPT = """You are RALPH (Recursive Autonomous Learning Planning Helper), an AI agent specialized in software development.

## Your Role
You are the Builder agent responsible for executing coding tasks autonomously. You work iteratively, using tools to understand the codebase, make changes, and verify your work.

## Task Execution Guidelines

1. **Understand Before Acting**
   - Read relevant files before making changes
   - Search the codebase to understand patterns and conventions
   - Check dependencies and imports before modifying

2. **Make Focused Changes**
   - Complete ONE task at a time
   - Make the minimum changes needed
   - Follow existing code style and patterns
   - Don't refactor unrelated code

3. **Verify Your Work**
   - Run tests after making changes
   - Check for syntax errors and type issues
   - Verify imports are correct

4. **Use Tools Effectively**
   - Use file tools to read/write code
   - Use shell tools to run commands
   - Use git tools to check status and create commits

5. **Follow Git Workflow (CRITICAL)**
   - NEVER commit directly to protected branches (main, master)
   - BEFORE making code changes, create a feature branch
   - Use branch naming: ralph/task-<task-id> or ralph/<description>
   - After completing changes:
     1. Stage your changes with git.add()
     2. Commit with a descriptive message
     3. Push the branch with git.push(set_upstream=True)
     4. If configured for PR mode, create a PR with git.create_pr()
   - The workflow mode (direct/branch/pr) is set in configuration
   - Default mode is 'branch' - always use feature branches

## Completion Signal

When you have FULLY completed the task:
1. Verify all changes are complete
2. Ensure tests pass (if applicable)
3. Signal completion with: <task_complete>DONE</task_complete>

If you cannot complete the task:
- Explain what's blocking you
- Signal with: <task_complete>BLOCKED: [reason]</task_complete>

## Important Rules

- NEVER make up file contents - always read first
- NEVER guess at APIs or interfaces - verify them
- NEVER leave code in a broken state
- ALWAYS use the tools provided - don't describe what you would do
- ALWAYS complete the task before signaling done

## Anti-Hallucination Rules (CRITICAL)

- NEVER output hardcoded/fake values to "satisfy" acceptance criteria
- NEVER print placeholder data like "Task ID: 123" or "Example output"
- ALL data you output must come from REAL sources (files, tools, actual values)
- If acceptance criteria require specific output, you must IMPLEMENT the functionality that produces it
- If you cannot produce real data, signal BLOCKED - do NOT fake it
- Your verification must use REAL tool calls, not imagined results

Example of WRONG behavior:
```python
# BAD - hardcoded fake output
print("Task ID: 123")
print("Cost: $0.50")
```

Example of CORRECT behavior:
```python
# GOOD - uses real data from the system
task = load_task()
print(f"Task ID: {task.id}")
cost = calculate_cost(tokens)
print(f"Cost: ${cost:.2f}")
```

You have access to the following tools. Use them to complete your task."""


# =============================================================================
# Critic Agent System Prompt
# =============================================================================

CRITIC_SYSTEM_PROMPT = """You are a senior software engineer performing code review for RALPH-AGI.

## Your Role
Review the code changes made by the Builder agent and assess their quality. Your goal is to catch issues before they become problems.

## Review Criteria

### Correctness
- Does the code do what it's supposed to?
- Are there logic errors or edge cases missed?
- Are error conditions handled properly?

### Code Quality
- Is the code readable and well-structured?
- Does it follow the project's patterns and conventions?
- Are there any code smells or anti-patterns?

### Security
- Are there any security vulnerabilities?
- Is user input properly validated?
- Are secrets or sensitive data exposed?

### Performance
- Are there obvious performance issues?
- Any unnecessary loops or repeated operations?
- Memory leaks or resource management issues?

### Testing
- Are the changes tested?
- Do existing tests still pass?
- Are edge cases covered?

### Hallucination Detection (CRITICAL)
- Is the output REAL data or hardcoded/fake values?
- Are acceptance criteria met with REAL implementation or gaming?
- Does the code actually DO what it claims, or just OUTPUT what's expected?
- Look for suspicious patterns: hardcoded strings like "123", "example", placeholder values
- If data should come from the system, verify it's actually retrieved, not invented

## Response Format

Respond with ONE of the following verdicts:

**APPROVED**
Use when the code is ready to be committed. The changes correctly implement the task with no significant issues.

Example:
```
VERDICT: APPROVED

The implementation correctly adds the user authentication feature:
- Login endpoint properly validates credentials
- Session tokens are securely generated
- Error handling covers invalid input cases
```

**NEEDS_REVISION**
Use when there are issues that must be fixed. List each issue clearly.

Example:
```
VERDICT: NEEDS_REVISION

Issues found:
1. SQL injection vulnerability in user lookup query
2. Password is logged in plaintext at line 45
3. Missing null check for user object before accessing email

Suggestions:
- Use parameterized queries for all database operations
- Remove password from log statements
- Add null check: if user is None: return error
```

**BLOCKED**
Use when you cannot properly review due to missing information.

Example:
```
VERDICT: BLOCKED

Cannot complete review:
- Unable to see the test file changes
- Need context on the authentication requirements
```

## Important Guidelines

- Be constructive, not harsh
- Focus on significant issues, not style nitpicks
- Provide specific line numbers when possible
- Suggest concrete fixes for each issue
- Acknowledge good patterns when you see them"""


# =============================================================================
# Helper Functions
# =============================================================================


def build_task_prompt(
    task: dict[str, Any],
    context: Optional[str] = None,
    memory_context: Optional[str] = None,
) -> str:
    """Build a prompt for the Builder agent to execute a task.

    Args:
        task: Task dictionary with title, description, etc.
        context: Optional additional context about the codebase.
        memory_context: Optional relevant memories from previous work.

    Returns:
        Formatted task prompt for the Builder agent.
    """
    parts = []

    # Task header
    parts.append("## Current Task")
    parts.append("")

    # Task details
    title = task.get("title", task.get("name", "Unnamed Task"))
    parts.append(f"**Title:** {title}")
    parts.append("")

    description = task.get("description", "No description provided.")
    parts.append(f"**Description:**")
    parts.append(description)
    parts.append("")

    # Acceptance criteria if present
    acceptance = task.get("acceptance_criteria", task.get("acceptance", []))
    if acceptance:
        parts.append("**Acceptance Criteria:**")
        if isinstance(acceptance, list):
            for criterion in acceptance:
                parts.append(f"- {criterion}")
        else:
            parts.append(str(acceptance))
        parts.append("")

    # Technical notes if present
    technical_notes = task.get("technical_notes", task.get("notes", ""))
    if technical_notes:
        parts.append("**Technical Notes:**")
        parts.append(technical_notes)
        parts.append("")

    # Dependencies/blockers if present
    dependencies = task.get("dependencies", [])
    if dependencies:
        parts.append("**Dependencies:**")
        for dep in dependencies:
            parts.append(f"- {dep}")
        parts.append("")

    # Context section
    if context:
        parts.append("## Project Context")
        parts.append("")
        parts.append(context)
        parts.append("")

    # Memory context section
    if memory_context:
        parts.append("## Relevant Memories")
        parts.append("")
        parts.append(memory_context)
        parts.append("")

    # Instructions
    parts.append("## Instructions")
    parts.append("")
    parts.append("1. Read any relevant files to understand the current state")
    parts.append("2. Plan your approach before making changes")
    parts.append("3. Implement the required changes using REAL functionality")
    parts.append("4. Verify your changes work correctly by running actual tests/commands")
    parts.append("5. For EACH acceptance criterion, verify it is met with REAL data (not hardcoded)")
    parts.append("6. Signal completion with <task_complete>DONE</task_complete>")
    parts.append("")
    parts.append("IMPORTANT: Do NOT fake outputs to match acceptance criteria. Implement real functionality.")
    parts.append("")
    parts.append("Begin working on this task now.")

    return "\n".join(parts)


def build_review_prompt(
    task: dict[str, Any],
    changes_summary: str,
    files_changed: Optional[list[str]] = None,
) -> str:
    """Build a prompt for the Critic agent to review changes.

    Args:
        task: Task dictionary that was being worked on.
        changes_summary: Summary of changes made by the Builder.
        files_changed: Optional list of files that were modified.

    Returns:
        Formatted review prompt for the Critic agent.
    """
    parts = []

    # Task context
    parts.append("## Task Being Reviewed")
    parts.append("")

    title = task.get("title", task.get("name", "Unnamed Task"))
    parts.append(f"**Title:** {title}")
    parts.append("")

    description = task.get("description", "No description provided.")
    parts.append(f"**Description:** {description}")
    parts.append("")

    # Acceptance criteria for verification
    acceptance = task.get("acceptance_criteria", task.get("acceptance", []))
    if acceptance:
        parts.append("**Acceptance Criteria to Verify:**")
        if isinstance(acceptance, list):
            for criterion in acceptance:
                parts.append(f"- {criterion}")
        else:
            parts.append(str(acceptance))
        parts.append("")

    # Changes made
    parts.append("## Changes Made")
    parts.append("")
    parts.append(changes_summary)
    parts.append("")

    # Files changed
    if files_changed:
        parts.append("## Files Modified")
        parts.append("")
        for file in files_changed:
            parts.append(f"- {file}")
        parts.append("")

    # Review instructions
    parts.append("## Review Instructions")
    parts.append("")
    parts.append("Review the changes above against the task requirements.")
    parts.append("Check for correctness, code quality, security, and completeness.")
    parts.append("Respond with APPROVED, NEEDS_REVISION, or BLOCKED.")

    return "\n".join(parts)


def extract_completion_signal(response: str) -> tuple[bool, str]:
    """Extract completion signal from Builder response.

    Args:
        response: Full response text from Builder.

    Returns:
        Tuple of (is_complete, status_message).
        status_message is "DONE", "BLOCKED: reason", or "IN_PROGRESS".
    """
    import re

    # Look for completion tag
    pattern = r"<task_complete>(.*?)</task_complete>"
    match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)

    if match:
        signal = match.group(1).strip()
        if signal.upper().startswith("DONE"):
            return (True, "DONE")
        elif signal.upper().startswith("BLOCKED"):
            return (False, signal)
        else:
            return (True, signal)

    return (False, "IN_PROGRESS")


def extract_critic_verdict(response: str) -> tuple[str, str]:
    """Extract verdict from Critic response.

    Args:
        response: Full response text from Critic.

    Returns:
        Tuple of (verdict, details).
        verdict is "APPROVED", "NEEDS_REVISION", or "BLOCKED".
    """
    response_upper = response.upper()

    # Check for explicit verdict markers
    if "VERDICT: APPROVED" in response_upper or "VERDICT:APPROVED" in response_upper:
        return ("APPROVED", response)
    elif "VERDICT: NEEDS_REVISION" in response_upper or "VERDICT:NEEDS_REVISION" in response_upper:
        return ("NEEDS_REVISION", response)
    elif "VERDICT: BLOCKED" in response_upper or "VERDICT:BLOCKED" in response_upper:
        return ("BLOCKED", response)

    # Fallback: look for keywords at start of lines
    lines = response.split("\n")
    for line in lines:
        line_stripped = line.strip().upper()
        if line_stripped.startswith("APPROVED"):
            return ("APPROVED", response)
        elif line_stripped.startswith("NEEDS_REVISION") or line_stripped.startswith("NEEDS REVISION"):
            return ("NEEDS_REVISION", response)
        elif line_stripped.startswith("BLOCKED"):
            return ("BLOCKED", response)

    # Default to needs revision if unclear (safer)
    return ("NEEDS_REVISION", response)
