# Moody Campaign Choice Engine

Internal campaign decision engine for Moody Lenses — LLM-powered multi-dimensional evaluation to help marketing teams make data-driven choices between campaign proposals.

## What Is This

Campaign Choice Engine is an **internal tool** that solves a specific problem: when a team has multiple campaign creative proposals, how to quickly and structurally evaluate and rank them.

The engine uses LLM-simulated multi-persona evaluation (Audience Panel + Pairwise comparison), combined with Bradley-Terry ranking and probability aggregation, to produce composite scores and rankings for each proposal. Post-hoc resolution and calibration (Brier Score / Log-Loss) continuously improve evaluation quality.

## What's Implemented

- **Async multi-campaign evaluation**: Submit 2-6 campaign proposals, get async background evaluation and ranking
- **Multi-dimensional scoring**: Audience Panel multi-persona scoring + Pairwise head-to-head comparison
- **Probability aggregation**: Bradley-Terry + Panel average + Objection penalty, three-signal softmax aggregation
- **Post-hoc resolution & calibration**: Calibrate evaluation model against actual outcomes, track Brier Score and Log-Loss
- **Judge weight calibration**: Adjust persona evaluation weights based on historical accuracy
- **Web frontend**: React SPA for submitting proposals, tracking progress, viewing results
- **Single-port production deployment**: Flask serves both frontend and API, one-click Docker start

## What This Is Not

- Not a general prediction platform
- Not a trading platform, no tokens, no blockchain
- Not a social simulation / opinion forecasting tool
- No user authentication (used within internal trust network)
- Results stored on filesystem, not a database

## Quick Start

### Source Code

```bash
# 1. Configure
cp .env.example .env
# Edit .env, set LLM_API_KEY

# 2. Install dependencies
cd backend && pip install -r requirements.txt

# 3. Start
python run.py
# http://localhost:5001
```

### Docker Deployment (Recommended)

```bash
cp .env.example .env
# Edit .env, set LLM_API_KEY
docker compose up -d --build
# http://<server-ip>:5001
```

See [DEPLOY.md](./DEPLOY.md) for detailed deployment instructions.

### Minimal Trial

```bash
# Health check
curl http://localhost:5001/health

# Submit evaluation
curl -X POST http://localhost:5001/api/campaign/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "campaigns": [
      {"name": "Plan A", "core_message": "Natural daily disposable color lenses", "product_line": "colored_lenses"},
      {"name": "Plan B", "core_message": "Silicone hydrogel high-oxygen tech", "product_line": "moodyplus"}
    ]
  }'

# Check status
curl http://localhost:5001/api/campaign/evaluate/status/<task_id>

# Get results
curl http://localhost:5001/api/campaign/result/<set_id>
```

Full API walkthrough: [backend/QUICKSTART.md](./backend/QUICKSTART.md).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `LLM_API_KEY` | Yes | LLM API key |
| `LLM_BASE_URL` | No | OpenAI-compatible endpoint (defaults to OpenAI) |
| `LLM_MODEL_NAME` | No | Model name (defaults to gpt-4o-mini) |
| `SECRET_KEY` | Recommended | Flask session secret |

## Tech Stack

- **Backend**: Python 3.11+ / Flask / Gunicorn
- **Frontend**: React + Vite + TypeScript
- **Deployment**: Docker multi-stage build, single port 5001
- **LLM**: OpenAI-compatible API (Alibaba Bailian / Qwen / OpenAI)

## Project Structure

```
backend/
  app/
    api/campaign.py      # API routes
    services/            # Scoring, calibration, probability aggregation
    models/              # Data models
    utils/               # LLM client, retry, logging
  tests/                 # pytest tests
  run.py                 # Dev startup entry
frontend/                # React SPA
Dockerfile               # Multi-stage build
docker-compose.yml       # Production deployment
```
