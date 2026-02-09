# New LLM assessment

Large Language Models (LLMs) can be powerful but often come with high costs and are closed-source, making deployment and iteration challenging. An open-source, Small Language Model (SLM) is being considered as an alternative for a customer service chatbot in the e-commerce/retail space. As a consulting AI engineer, your task is to take over the initial project, debug and improve the application’s safety guardrails, and evaluate the new LLM’s effectiveness and reliability using the provided codebase and setup.

## Overview

The application provides a customer service chatbot powered by a locally-hosted SLM (SmolLM2 135M) with safety guardrails to prevent:
- Prompt injection attacks
- Policy-violating content (harmful/illegal, personal data requests, off-topic queries)
- Unsafe outputs

## Prerequisites

- Docker and Docker Compose
- Docker Desktop or colima
- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager (or pip)
- At least 8GB RAM available for running Ollama models

## Quick Start

Start the docker deamon:

- Open Docker Desktop

or

```bash
colima start
```

Run the automated setup script to configure everything in one go:

```bash
./setup.sh
```

**Note**: Initial model downloads may take 3-7 minutes depending on your connection.

## Exercise Tasks

### Task 1: Fix Failing Tests (15 minutes)

Run the test suite:
```bash
pytest tests/test_app.py -v
```

### Task 2: Evaluate Model Performance (15 minutes)

Implement the similarity score calculation logic.

Run the evaluation script:
```bash
python evaluation/evaluate.py --sample-size 20
```

### Task 3: Guardrail Hardening (10 minutes)

After fixing the bugs, discuss and optionally implement:

1. **Defense-in-depth strategies**:
   - How would you improve the pre-filtering?
   - What additional output moderation would you add?
   - How would you handle edge cases?

2. **Monitoring and logging**:
   - What metrics would you track?
   - How would you detect new attack patterns?
   - What alerts would you set up?

3. **Trade-offs**:
   - False positives vs false negatives
   - Latency vs thoroughness
   - Explainability vs accuracy

## Configuration

Environment variables (see `app/config.py`):
- `OLLAMA_BASE_URL`: Ollama API endpoint (default: `http://localhost:11434`)
- `LLM_MODEL`: LLM model name (default: `smollm2:135m`)
- `EMBEDDING_MODEL`: Embedding model name (default: `nomic-embed-text`)
- `APP_HOST`: Application host (default: `0.0.0.0`)
- `APP_PORT`: Application port (default: `8000`)
- `PHOENIX_ENDPOINT`: Phoenix observability endpoint (default: `http://localhost:6006`)
- `PHOENIX_ENABLED`: Enable Phoenix tracing (default: `false`)

## Clean Up

Stop all services:
```bash
docker-compose down
```

Remove volumes (delete downloaded models):
```bash
docker-compose down -v
```

Stop docker deamon:
```bash
colima stop
```

## Further Reading

- [Ollama Documentation](https://github.com/ollama/ollama)
- [LangChain Documentation](https://python.langchain.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Prompt Injection Defenses](https://simonwillison.net/2023/Apr/14/worst-that-can-happen/)
- [Arize Phoenix Documentation](https://docs.arize.com/phoenix)