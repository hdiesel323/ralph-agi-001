# RALPH-AGI: Developer Guide

**Version:** 1.0  
**Date:** Jan 10, 2026  
**Author:** Manus AI

---

## 1. Getting Started

### 1.1. Prerequisites

- **Python 3.11+** installed
- **Git** installed
- **OpenAI API key** (for GPT-4.1) or **Anthropic API key** (for Claude 4.5)
- **Docker** (optional, for containerized deployment)

### 1.2. Installation

```bash
# Clone the repository
git clone https://github.com/hdiesel323/ralph-agi-001.git
cd ralph-agi-001

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### 1.3. Running Your First Task

```bash
python main.py --prompt "Create a Python function that calculates the Fibonacci sequence"
```

**Expected Output:**

```
[2026-01-10 10:00:00] Starting task...
[2026-01-10 10:00:05] Initializer Agent: Expanding prompt...
[2026-01-10 10:00:10] Initializer Agent: Created feature_list.json with 3 features
[2026-01-10 10:00:15] Coding Agent: Starting feature 1/3...
[2026-01-10 10:01:00] Coding Agent: Feature 1 complete. Committing...
[2026-01-10 10:01:05] Coding Agent: Starting feature 2/3...
...
[2026-01-10 10:05:00] Task complete! All features implemented.
```

---

## 2. Project Structure

```
ralph-agi/
├── main.py                     # Entry point
├── agents/                     # Agent implementations
│   ├── initializer_agent.py
│   ├── coding_agent.py
│   ├── testing_agent.py
│   └── ...
├── memory/                     # Memory system
│   ├── short_term.py
│   ├── medium_term.py
│   └── long_term.py
├── hooks/                      # Hooks system
│   ├── pre_tool_use.py
│   ├── post_tool_use.py
│   └── ...
├── beads/                      # Beads task graph
│   └── task_graph.py
├── coordination/               # Multi-agent coordination
│   ├── shared_db.py
│   └── file_claims.py
├── evaluation/                 # Evaluation pipeline
│   ├── static_analysis.py
│   ├── unit_tests.py
│   └── ...
├── utils/                      # Utility functions
│   ├── git_utils.py
│   ├── llm_utils.py
│   └── ...
├── artifacts/                  # Generated artifacts
│   ├── feature_list.json
│   ├── progress.txt
│   └── init.sh
├── db/                         # Databases
│   ├── ralph_agi.db (SQLite)
│   └── chroma/ (ChromaDB)
├── tests/                      # Unit and integration tests
├── requirements.txt            # Python dependencies
├── .env.example                # Example environment variables
└── README.md                   # Project README
```

---

## 3. Core Concepts

### 3.1. The Ralph Wiggum Loop

The core of RALPH-AGI is a simple `while` loop that iterates until the task is complete:

```python
def ralph_wiggum_loop(prompt):
    feature_list = initializer_agent.expand_prompt(prompt)
    
    while not all_features_complete(feature_list):
        feature = coding_agent.select_next_feature(feature_list)
        coding_agent.implement_feature(feature)
        git_utils.commit(f"Implement {feature['name']}")
        update_progress(feature)
    
    return "Task complete!"
```

**Key Insight:** Persistence wins. The agent keeps iterating until the task is done.

### 3.2. Two-Agent Architecture

RALPH-AGI uses two agents:

1.  **Initializer Agent:** Runs once at the beginning to set up the environment.
2.  **Coding Agent:** Runs in a loop to implement features one by one.

**Why?** This separation of concerns prevents the agent from getting confused about whether it's setting up or implementing.

### 3.3. Structured Artifacts

RALPH-AGI uses three key artifacts:

1.  **`feature_list.json`:** A JSON file that lists all features to be implemented.
2.  **`progress.txt`:** A freeform text file that provides a high-level summary of progress.
3.  **`init.sh`:** A shell script that automates environment setup (e.g., starting servers, running tests).

**Why JSON for the feature list?** The LLM is less likely to inappropriately modify a JSON file compared to a Markdown file.

### 3.4. Git-First Workflow

Every feature is committed to a separate git branch. This provides:

- **State management:** Git is the single source of truth.
- **Rollback capability:** Bad commits can be easily reverted.
- **Audit trail:** Git logs provide a complete history of the agent's work.

---

## 4. Advanced Topics

### 4.1. Adding a New Agent

1.  Create a new file in the `agents/` directory (e.g., `agents/my_agent.py`).
2.  Define a class that inherits from `BaseAgent`:

```python
from agents.base_agent import BaseAgent

class MyAgent(BaseAgent):
    def run(self, input_data):
        # Your agent logic here
        return output_data
```

3.  Register the agent in `main.py`:

```python
from agents.my_agent import MyAgent

agents = {
    "initializer": InitializerAgent(),
    "coder": CodingAgent(),
    "my_agent": MyAgent(),  # Add your agent here
}
```

### 4.2. Customizing the Hooks System

Edit the `hooks.json` file in the project root:

```json
{
  "PreToolUse": [
    {
      "action": "run_script",
      "script": "scripts/my_custom_hook.py"
    }
  ]
}
```

### 4.3. Integrating a New LLM

RALPH-AGI supports multiple LLMs via a unified interface. To add a new LLM:

1.  Create a new file in `utils/llm_utils.py`:

```python
def call_my_llm(prompt, model="my-model"):
    # Your LLM API call here
    return response
```

2.  Update the `LLM_PROVIDER` environment variable in `.env`:

```
LLM_PROVIDER=my_llm
```

---

## 5. Testing

### 5.1. Running Tests

```bash
pytest tests/
```

### 5.2. Writing Tests

Create a new test file in the `tests/` directory:

```python
# tests/test_coding_agent.py

from agents.coding_agent import CodingAgent

def test_select_next_feature():
    agent = CodingAgent()
    feature_list = [
        {"name": "Feature 1", "status": "pending"},
        {"name": "Feature 2", "status": "pending"}
    ]
    next_feature = agent.select_next_feature(feature_list)
    assert next_feature["name"] == "Feature 1"
```

---

## 6. Deployment

### 6.1. Docker Deployment

```bash
# Build the Docker image
docker build -t ralph-agi .

# Run the container
docker run -e OPENAI_API_KEY=sk-... ralph-agi --prompt "Create a Flask app"
```

### 6.2. Cloud Deployment

RALPH-AGI can be deployed to any cloud platform that supports Docker (e.g., AWS ECS, Google Cloud Run, Azure Container Instances).

---

## 7. Troubleshooting

### 7.1. Common Issues

**Issue:** `ModuleNotFoundError: No module named 'anthropic'`  
**Solution:** Make sure you've activated the virtual environment and installed dependencies: `pip install -r requirements.txt`

**Issue:** The agent gets stuck in a loop.  
**Solution:** Check the `progress.txt` file to see what the agent is working on. You may need to manually intervene by editing `feature_list.json` or stopping the agent.

**Issue:** High API costs.  
**Solution:** Implement cost monitoring and use LLM ensembles (mix of Opus, Sonnet, and Haiku).

---

## 8. Contributing

We welcome contributions! Please see `CONTRIBUTING.md` for guidelines.

---

## 9. Support

- **GitHub Issues:** [https://github.com/hdiesel323/ralph-agi-001/issues](https://github.com/hdiesel323/ralph-agi-001/issues)
- **Twitter:** [@hdiesel323](https://twitter.com/hdiesel323)
- **Email:** [support@ralph-agi.com](mailto:support@ralph-agi.com)

---

## 10. License

RALPH-AGI is licensed under the MIT License. See `LICENSE` for details.
