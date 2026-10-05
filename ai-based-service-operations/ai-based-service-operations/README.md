# AI-Based Service Operations

A simple base project that automates service-desk triage. Each incoming request is
analyzed for **category, priority, sentiment**, routed to the right **team**, and given a
**summary and suggested reply**.

- Works offline with a rule-based engine.
- Uses Claude automatically when `ANTHROPIC_API_KEY` is set (falls back to rules on failure).
- FastAPI + SQLite, no other infrastructure needed.

## Run
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)   # optional
uvicorn app.main:app --reload
```
Interactive docs: http://127.0.0.1:8000/docs

## Endpoints
| Method | Path | Purpose |
|---|---|---|
| POST | `/tickets` | Create + AI-triage a ticket |
| GET | `/tickets?status=&priority=&category=` | List (most urgent first) |
| GET | `/tickets/{id}` | Ticket detail |
| PATCH | `/tickets/{id}/status` | open / in_progress / resolved / closed |
| GET | `/stats` | Counts by status, category, priority, sentiment |

## Example
```bash
curl -X POST localhost:8000/tickets -H 'Content-Type: application/json' \
  -d '{"customer":"Asha","message":"URGENT: production site is down!"}'
```

## Test
```bash
pytest -q
```

## Structure
```
app/ai.py     triage logic (LLM + rules)
app/db.py     SQLite helpers
app/main.py   REST API
tests/        API tests
```

## Ideas for extension
Auth, a web dashboard, email/Slack intake, SLA timers, auto-assignment, knowledge-base search.
