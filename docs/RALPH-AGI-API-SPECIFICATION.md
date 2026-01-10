# RALPH-AGI: API Specification

**Version:** 1.0  
**Date:** Jan 10, 2026  
**Author:** Manus AI

---

## 1. Introduction

This document provides a detailed specification for the internal and external APIs used by RALPH-AGI. These APIs are designed to be simple, robust, and extensible.

## 2. Core Agent API

### `POST /api/v1/tasks`

**Description:** Create a new task for RALPH-AGI to execute.

**Request Body:**

```json
{
  "prompt": "Create a new Flask app with a single endpoint that returns 'Hello, World!'",
  "agent_config": {
    "model": "claude-4.5-opus",
    "temperature": 0.2,
    "max_iterations": 100
  }
}
```

**Response Body:**

```json
{
  "task_id": "t_12345",
  "status": "queued",
  "message": "Task successfully queued."
}
```

### `GET /api/v1/tasks/{task_id}`

**Description:** Get the status of a specific task.

**Response Body:**

```json
{
  "task_id": "t_12345",
  "status": "running",
  "progress": {
    "features_completed": 5,
    "features_total": 20,
    "current_feature": "Implement user authentication"
  },
  "logs": [
    "[2026-01-10 10:00:00] Starting task...",
    "[2026-01-10 10:05:00] Completed feature: Create project structure"
  ]
}
```

---

## 3. Memory System API

### `POST /api/v1/memory/search`

**Description:** Search the memory system for relevant information.

**Request Body:**

```json
{
  "query": "How do I fix a 'module not found' error in Python?",
  "top_k": 5
}
```

**Response Body:**

```json
{
  "results": [
    {
      "document": "... (text of the document) ...",
      "score": 0.95,
      "source": "previous_project_logs.txt"
    }
  ]
}
```

### `POST /api/v1/memory/add`

**Description:** Add a new document to the memory system.

**Request Body:**

```json
{
  "document": "When encountering a 'module not found' error, check your virtual environment and requirements.txt file.",
  "source": "manual_entry"
}
```

**Response Body:**

```json
{
  "success": true,
  "message": "Document successfully added to memory."
}
```

---

## 4. Hooks System API

The Hooks System does not have a public API. It is configured via a `hooks.json` file in the project root.

**Example `hooks.json`:**

```json
{
  "PreToolUse": [
    {
      "action": "run_script",
      "script": "scripts/tldr_analysis.py"
    }
  ],
  "PostToolUse": [
    {
      "action": "run_script",
      "script": "scripts/extract_learnings.py"
    }
  ]
}
```

---

## 5. Development Setup

### 5.1. `requirements.txt`

```
fastapi
uvicorn
openai
anthropic
chromadb
sqlalchemy
```

### 5.2. `.env` file

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-...
```
