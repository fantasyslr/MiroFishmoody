# MiroFishmoody Backend Quickstart

## 1. Install dependencies

Recommended with `uv`:

```bash
cd backend
uv sync
```

Or with `pip`:

```bash
cd backend
pip install -r requirements.txt
pip install pytest  # optional, for tests
```

## 2. Configure `.env`

```bash
cd ..
cp .env.example .env
```

Edit `.env` and set at least:

- `LLM_API_KEY`
- `LLM_BASE_URL` if you are not using the default OpenAI endpoint
- `LLM_MODEL_NAME` if needed
- `SECRET_KEY` for a non-default session secret

## 3. Start the backend

With `uv`:

```bash
cd backend
uv run python run.py
```

Or with plain Python:

```bash
cd backend
python run.py
```

Default address: `http://0.0.0.0:5001`

## 4. Health check

```bash
curl http://localhost:5001/health
```

Expected response:

```json
{"service":"Campaign Ranker Engine","status":"ok"}
```

## 5. Authentication note

All `/api/campaign/*` endpoints require a logged-in session.  
Local users are defined in `backend/app/auth.py`; update them before sharing or deploying publicly.

## 6. Minimal backend smoke test

### Login and store the session cookie

```bash
curl -c cookies.txt -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"<username>","password":"<password>"}'
```

### Submit an evaluation

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/campaign/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "campaigns": [
      {"name": "方案A", "core_message": "自然美瞳日抛新体验", "product_line": "colored_lenses"},
      {"name": "方案B", "core_message": "硅水凝胶透氧黑科技", "product_line": "moodyplus"}
    ]
  }'
```

This returns `task_id` and `set_id`.

### Check task progress

```bash
curl -b cookies.txt http://localhost:5001/api/campaign/evaluate/status/<task_id>
```

When `status=completed`, fetch the result:

```bash
curl -b cookies.txt http://localhost:5001/api/campaign/result/<set_id>
```

### Export the result JSON

```bash
curl -b cookies.txt -OJ http://localhost:5001/api/campaign/export/<set_id>
```

### Post-launch resolution

```bash
curl -b cookies.txt -X POST http://localhost:5001/api/campaign/resolve \
  -H "Content-Type: application/json" \
  -d '{"set_id":"<set_id>","winner_campaign_id":"campaign_1","actual_metrics":{"ctr":0.03}}'
```

### Check calibration status

```bash
curl -b cookies.txt http://localhost:5001/api/campaign/calibration
```

## 7. Run tests

With `uv`:

```bash
cd backend
uv run pytest tests -q
```

Or with Python directly:

```bash
cd backend
python -m pytest tests -q
```
