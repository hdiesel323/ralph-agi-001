# Memvid Evaluation for RALPH-AGI Memory System

**Date:** 2026-01-10
**Status:** Approved for Sprint 2
**Source:** https://github.com/memvid/memvid

---

## Executive Summary

Memvid is a portable, serverless memory layer for AI agents that packages data, embeddings, search structures, and metadata into a single `.mv2` file. It eliminates the need for complex RAG pipelines or server-based vector databases.

**Recommendation:** Use Memvid as the primary memory backend for RALPH-AGI, replacing the originally planned SQLite + ChromaDB stack.

---

## Key Features

### 1. Single-File Architecture

- Everything in one portable `.mv2` file
- No external database servers required
- Easy backup, transfer, and version control
- Write-ahead logging built-in (1-64MB)

### 2. Append-Only Frames

- Inspired by video encoding
- Immutable "Smart Frames" containing:
  - Content
  - Timestamps
  - Checksums
  - Metadata
- Crash-safe: committed frames cannot corrupt
- Perfect for AFK mode reliability

### 3. Built-in Search Capabilities

| Search Type | Algorithm | Use Case                     |
| ----------- | --------- | ---------------------------- |
| Full-text   | BM25      | Keyword queries              |
| Vector      | HNSW      | Semantic similarity          |
| Temporal    | Native    | "What did I know at time X?" |

### 4. Multi-Modal Support

- Text embeddings
- CLIP visual embeddings
- Audio transcription
- Natural language date parsing

---

## Comparison: Memvid vs. Original Plan

| Requirement        | Original Plan     | With Memvid        |
| ------------------ | ----------------- | ------------------ |
| Structured storage | SQLite            | Built-in           |
| Vector search      | ChromaDB          | Built-in HNSW      |
| Full-text search   | Manual            | Built-in BM25      |
| Crash safety       | Manual WAL        | Append-only frames |
| Temporal queries   | Manual            | Native support     |
| Deployment         | 2+ services       | Single file        |
| Dependencies       | sqlite3, chromadb | memvid             |

**Complexity Reduction:** ~60% fewer components to manage

---

## Architecture Fit

### Short-Term Memory (Session Context)

```python
# Store iteration results as frames
memory.append(
    content=iteration_result,
    metadata={
        "session_id": session.id,
        "iteration": loop.iteration,
        "type": "iteration_result"
    }
)
```

### Medium-Term Memory (Git-Linked)

```python
# Link frames to git commits
memory.append(
    content=task_summary,
    metadata={
        "commit_sha": git.head(),
        "type": "task_complete"
    }
)
```

### Long-Term Memory (Persistent Knowledge)

```python
# Store learnings with temporal context
memory.append(
    content=learning,
    metadata={
        "type": "learning",
        "category": "error_pattern",
        "tags": ["python", "import"]
    }
)

# Query: "What did I learn about imports?"
results = memory.search("import errors", type="learning")
```

---

## Scaling Strategy

### Phase 1: Memvid-Only (Sprint 2-3)

- Single `.mv2` file for all memory tiers
- Suitable for: thousands of frames, single agent
- Performance: sub-millisecond queries

### Phase 2: Hybrid (If Needed)

If we hit scale limits (millions of vectors, multi-agent):

- Keep Memvid for session/short-term memory
- Add Qdrant/Pinecone for massive vector search
- Use Memvid's export capabilities for sync

**Trigger for Phase 2:**

- Query latency > 100ms
- File size > 1GB
- Multi-agent coordination needed

---

## SDK Options

| Language | Package      | Status         |
| -------- | ------------ | -------------- |
| Python   | `memvid`     | Primary choice |
| Rust     | `memvid`     | Available      |
| Node.js  | `memvid`     | Available      |
| CLI      | `memvid-cli` | Available      |

---

## Integration Plan

### Sprint 2 Stories

1. **Story 3.1: Memvid Core Integration** (3 pts)
   - Install and configure memvid
   - Create `MemoryStore` wrapper class
   - Basic CRUD operations

2. **Story 3.2: Short-Term Memory** (2 pts)
   - Session-scoped frame storage
   - Context loading for loop

3. **Story 3.5: Vector Search** (3 pts)
   - Configure embedding model
   - Implement semantic search API

4. **Story 3.6: Query API** (3 pts)
   - Unified search interface
   - Hybrid retrieval (vector + BM25)

### Dependencies

```toml
# pyproject.toml
[project.dependencies]
memvid = "^0.1.0"
sentence-transformers = "^2.2.0"  # For embeddings
```

---

## Risks & Mitigations

| Risk                 | Impact | Mitigation                                |
| -------------------- | ------ | ----------------------------------------- |
| New/young project    | Medium | Monitor GitHub issues, have fallback plan |
| Python SDK maturity  | Low    | Rust core is stable, Python wraps it      |
| Embedding model size | Medium | Use lightweight model (all-MiniLM-L6-v2)  |
| File corruption      | Low    | Append-only design, regular backups       |

---

## Decision

**Approved:** Use Memvid as primary memory backend for RALPH-AGI.

**Rationale:**

1. Dramatically simplifies architecture (1 file vs. 2+ services)
2. Append-only design aligns perfectly with AFK mode reliability needs
3. Built-in temporal queries enable "knowledge evolution" tracking
4. Offline-first matches our single-agent deployment model
5. Active development with good documentation

**Fallback:** If issues arise, can migrate to SQLite + ChromaDB (original plan) since Memvid's frame structure maps cleanly to relational + vector DB.

---

## References

- [Memvid GitHub](https://github.com/memvid/memvid)
- [RALPH-AGI PRD - Memory System](../RALPH-AGI-PRD.md#fr-003)
- [Epic 03 - Memory System](../../_bmad-output/implementation-artifacts/epics/epic-03-memory-system.md)
