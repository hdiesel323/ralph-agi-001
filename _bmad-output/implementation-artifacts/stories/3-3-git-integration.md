# Story 3.3: Git Integration (Medium-Term Memory)

Status: completed
Completed: 2026-01-11

## Story

As a **developer**,
I want **git history as searchable memory**,
so that **code changes are preserved and queryable**.

## Acceptance Criteria

1. **AC1:** Auto-commit after successful task completion
   - `GitMemory.commit_changes()` stages all changes and creates commit
   - Configurable commit message templates (feat, fix, refactor, docs, test, chore)
   - Task ID included in commit message when provided

2. **AC2:** Store commit metadata in Memvid frames
   - Commits automatically stored as memory frames
   - Frame metadata includes: SHA, author, timestamp, files changed
   - Tags for commit SHA enable reverse lookup

3. **AC3:** Commit message template: `feat: {description}`
   - Conventional commit format supported
   - Templates: FEAT_TEMPLATE, FIX_TEMPLATE, REFACTOR_TEMPLATE, etc.
   - Task ID appended as footer when provided

4. **AC4:** Query memory by git commit reference
   - `get_memory_by_commit(ref)` returns linked memory frames
   - Search by short SHA tag
   - Support for HEAD, branch names, full SHA

5. **AC5:** Support linking frames to commits
   - `_store_commit_frame()` creates frame with commit metadata
   - Bidirectional linkage via tags and metadata
   - Frame content includes commit summary

## Tasks / Subtasks

- [x] Task 1: Create GitMemory class (AC: 1, 2)
  - [x] Create `ralph_agi/memory/git.py`
  - [x] Implement GitCommit dataclass with all metadata
  - [x] Implement `_run_git()` helper for subprocess calls
  - [x] Implement `is_repo()`, `has_changes()`, `get_status()`

- [x] Task 2: Implement staging and commit (AC: 1, 3)
  - [x] Implement `stage_all()` and `stage_files()`
  - [x] Implement `commit()` with message and allow_empty
  - [x] Implement `commit_changes()` with templates and task_id
  - [x] Support author name/email configuration

- [x] Task 3: Implement memory integration (AC: 2, 5)
  - [x] Implement `_store_commit_frame()` for memory linkage
  - [x] Add tags: git, commit, sha:{short_sha}, task:{task_id}
  - [x] Store metadata: SHA, author, timestamp, files_changed

- [x] Task 4: Implement commit queries (AC: 4)
  - [x] Implement `get_head_commit()` and `get_commit(ref)`
  - [x] Implement `get_commits_since()` and `get_commits_for_file()`
  - [x] Implement `search_commits()` by message content
  - [x] Implement `get_memory_by_commit()` for frame lookup

- [x] Task 5: Write unit tests (AC: all)
  - [x] Create `tests/memory/test_git.py`
  - [x] Test GitCommit dataclass
  - [x] Test repo detection and status
  - [x] Test staging and commit operations
  - [x] Test memory integration
  - [x] Test commit queries
  - [x] 48 tests passing

## Dev Notes

### GitCommit Dataclass

```python
@dataclass(frozen=True)
class GitCommit:
    sha: str
    short_sha: str
    message: str
    author: str
    author_email: str
    timestamp: str
    files_changed: int = 0
```

### GitMemory API

```python
git_mem = GitMemory(repo_path=".", memory_store=store)

# Auto-commit with memory linkage
commit = git_mem.commit_changes(
    description="Add user authentication",
    task_id="TASK-001",
    commit_type="feat"
)

# Query commits
commits = git_mem.search_commits("authentication")
frames = git_mem.get_memory_by_commit("HEAD")
```

### File List

**Created:**
- `ralph_agi/memory/git.py` - GitMemory class, GitCommit dataclass, GitError
- `tests/memory/test_git.py` - 48 unit tests

**Modified:**
- `ralph_agi/memory/__init__.py` - Export GitMemory, GitCommit, GitError
