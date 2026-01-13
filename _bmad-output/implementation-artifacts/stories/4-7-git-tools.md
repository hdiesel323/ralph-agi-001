# Story 4.7: Git Tools

**Epic:** 04 - Tool Integration
**Sprint:** 6
**Points:** 2
**Priority:** P0
**Status:** In Progress

## User Story

**As a** RALPH agent
**I want** git operations
**So that** I can commit changes and track version history

## Acceptance Criteria

- [ ] `status()` - Get repository status (staged, modified, untracked)
- [ ] `add(files)` - Stage files for commit
- [ ] `commit(message)` - Create a commit with message
- [ ] `log(limit)` - Get recent commit history
- [ ] `diff(staged)` - Get diff of changes
- [ ] `current_branch()` - Get current branch name
- [ ] `is_repo()` - Check if directory is a git repo
- [ ] Repository path validation
- [ ] 90%+ test coverage

## Technical Design

### Module Structure

```
ralph_agi/tools/
├── __init__.py          # Updated exports
├── git.py               # NEW - Git operations
└── ...
```

### Core Classes

```python
@dataclass
class GitStatus:
    """Repository status information.

    Attributes:
        branch: Current branch name
        staged: List of staged files
        modified: List of modified (unstaged) files
        untracked: List of untracked files
        ahead: Commits ahead of remote
        behind: Commits behind remote
    """

@dataclass
class GitCommit:
    """Commit information.

    Attributes:
        hash: Commit SHA (short)
        message: Commit message (first line)
        author: Author name
        date: Commit date
    """

class GitTools:
    """Git operations for version control.

    Usage:
        git = GitTools(repo_path="/path/to/repo")

        # Check status
        status = git.status()
        print(f"On branch: {status.branch}")

        # Stage and commit
        git.add(["file.py"])
        git.commit("Add new feature")

        # View history
        for commit in git.log(limit=5):
            print(commit.message)
    """
```

### API Reference

```python
def status(self) -> GitStatus:
    """Get repository status.

    Returns:
        GitStatus with branch, staged, modified, untracked files
    """

def add(self, files: list[str] | str = ".") -> bool:
    """Stage files for commit.

    Args:
        files: File paths to stage, or "." for all

    Returns:
        True if successful
    """

def commit(self, message: str, allow_empty: bool = False) -> str | None:
    """Create a commit.

    Args:
        message: Commit message
        allow_empty: Allow empty commits

    Returns:
        Commit hash if successful, None otherwise
    """

def log(self, limit: int = 10) -> list[GitCommit]:
    """Get recent commit history.

    Args:
        limit: Maximum commits to return

    Returns:
        List of GitCommit objects
    """
```

## Test Plan

1. **Status**: Clean repo, staged files, modified files, untracked
2. **Add**: Single file, multiple files, all files
3. **Commit**: Normal commit, empty message handling
4. **Log**: Parse history, respect limit
5. **Diff**: Unstaged changes, staged changes
6. **Edge cases**: Not a repo, no commits yet

## Dependencies

- Story 4.6: Shell Tools (COMPLETE - for git command execution)
- Git CLI (system dependency)

## Notes

Enables Meta-Ralph to commit its own changes and track progress.
