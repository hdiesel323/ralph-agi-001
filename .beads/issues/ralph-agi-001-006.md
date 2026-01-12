---
id: ralph-agi-001-006
title: Claude-Mem Memory Gaps - Sessions Not Processing
type: bug
status: partial
priority: 0
labels: [memory, reliability, critical, claude-mem, infrastructure]
created: 2026-01-11
updated: 2026-01-11
epic: epic-03-memory-system
---

# Claude-Mem Memory Gaps - Sessions Not Processing

## Problem Statement

Claude-mem is failing to extract observations from most sessions. Out of 57 JSONL session files, only 1 session has observations in the database. Critical conversations (like the multi-agent architecture discussion) are being lost.

**This is blocking for RALPH-AGI autonomous operation** - if Ralph can't reliably remember conversations, it can't pick up where it left off.

## Evidence

### Quantitative Gap
| Metric | Count |
|--------|-------|
| JSONL session files | 57 |
| Sessions registered in claude-mem | 35 |
| Sessions with observations | **1** (3 observations total) |
| Data loss rate | **97%** |

### Specific Lost Session
```
Session: e470314c-d75a-4f7e-a8b1-92880721e8af
Content: 543KB multi-agent architecture discussion
Status in DB: "active" (orphaned)
Observations: 0
Recovery: Only possible via manual JSONL grep
```

### Database State
```sql
-- All 35 sessions stuck in "active"
SELECT status, COUNT(*) FROM sdk_sessions GROUP BY status;
-- Result: active|35

-- Only 1 session has observations
SELECT memory_session_id, COUNT(*) FROM observations
WHERE project = 'ralph-agi-001' GROUP BY memory_session_id;
-- Result: 06fe5080-e380-4823-86bf-ce9286a552e2|3
```

## Root Cause Analysis

### Failure Chain
1. Session starts -> Registered in `sdk_sessions` with status "active"
2. Claude Code runs -> JSONL file grows with conversation
3. **Gap:** Observations should be extracted during/after session
4. Session ends (crash, user closes, etc.) -> Status stays "active"
5. No cleanup/recovery -> Session orphaned forever

### Identified Issues

| Issue | Description | Impact |
|-------|-------------|--------|
| **No completion signal** | Sessions never transition to "completed" | Observations never extracted |
| **No crash recovery** | Orphaned sessions stay "active" forever | Lost work |
| **No JSONL fallback** | Raw history exists but isn't indexed | Can't search lost conversations |
| **No reprocessing** | Can't manually trigger observation extraction | Can't recover |

## Impact on RALPH-AGI

1. **Story 3.6 (Memory Query API)** assumes memory is reliable
2. **Epic 06 (Multi-Agent)** discussion was lost, had to be recovered manually
3. **Context loading** at session start will be incomplete
4. **Cross-session learning** impossible if sessions aren't captured

## Proposed Solutions

### Short-term (Workarounds)
- [x] Manual JSONL search when memory search fails
- [ ] Script to identify orphaned sessions
- [ ] Document recovery procedure

### Medium-term (Fixes)
- [x] Add session completion detection (SessionEnd hook reliability) - CM-1 in claude-mem
- [x] Implement orphan session recovery (reprocess from JSONL) - CM-2 in claude-mem
- [x] Add JSONL full-text search as fallback in memory queries - **PR #2 MERGED**

### Completed Work (2026-01-11)

**Phase 1: Claude-mem Upstream Fixes** (in ~/.claude/plugins/marketplaces/thedotmack/)
- CM-1: Session completion detection with 30s idle timeout
- CM-2: Orphan session recovery service
- CM-3: Periodic health check (60s interval)

**Phase 2: RALPH JSONL Fallback** (PR #2 merged to main)
- JSONLBackupStore: Crash-safe append-only backup
- Dual-write: Every MemoryStore.append() writes to both Memvid and JSONL
- Fallback search: If Memvid fails, automatically searches JSONL
- Cross-platform: Works on Unix/Linux/macOS/Windows
- 41 new tests (80 total passing)

### Long-term (Architecture)
- [ ] Real-time observation extraction (not batch)
- [ ] Transaction-safe session lifecycle
- [ ] JSONL -> Observations sync daemon

## Acceptance Criteria

- [ ] 90%+ of sessions have observations extracted (pending verification)
- [x] Orphaned sessions can be reprocessed (CM-2)
- [x] Memory search has JSONL fallback (PR #2)
- [x] Session completion is reliable (CM-1)

## Related

- **Epic 03:** Memory System
- **Story 3.6:** Memory Query API
- **Claude-mem repo:** https://github.com/thedotmack/claude-mem

## Discovery Context

Discovered 2026-01-11 when trying to recover a conversation about multi-agent architectures. The conversation existed in Claude's JSONL history (`e470314c-d75a-4f7e-a8b1-92880721e8af.jsonl`) but wasn't in claude-mem's searchable database.
