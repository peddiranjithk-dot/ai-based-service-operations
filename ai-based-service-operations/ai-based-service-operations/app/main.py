from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from . import ai
from .db import get_conn, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI-Based Service Operations", version="1.0.0", lifespan=lifespan)


class TicketIn(BaseModel):
    customer: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=3, max_length=5000)


class StatusIn(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"]


@app.get("/")
def health():
    return {"service": "ai-based-service-operations", "status": "ok"}


@app.post("/tickets", status_code=201)
def create_ticket(body: TicketIn):
    a = ai.analyze(body.message)
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO tickets (customer, message, category, priority, sentiment,
               team, summary, suggested_reply, ai_source)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (body.customer, body.message, a["category"], a["priority"], a["sentiment"],
             a["team"], a["summary"], a["suggested_reply"], a["source"]),
        )
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/tickets")
def list_tickets(status: Optional[str] = None, priority: Optional[str] = None,
                 category: Optional[str] = None):
    q, args = "SELECT * FROM tickets WHERE 1=1", []
    for col, val in (("status", status), ("priority", priority), ("category", category)):
        if val:
            q += f" AND {col}=?"
            args.append(val)
    q += """ ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1
             WHEN 'medium' THEN 2 ELSE 3 END, id DESC"""
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(q, args).fetchall()]


@app.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Ticket not found")
    return dict(row)


@app.patch("/tickets/{ticket_id}/status")
def update_status(ticket_id: int, body: StatusIn):
    with get_conn() as conn:
        cur = conn.execute("UPDATE tickets SET status=? WHERE id=?", (body.status, ticket_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Ticket not found")
        row = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    return dict(row)


@app.get("/stats")
def stats():
    with get_conn() as conn:
        def group(col):
            return {r[0]: r[1] for r in conn.execute(
                f"SELECT {col}, COUNT(*) FROM tickets GROUP BY {col}")}
        total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        return {"total": total, "by_status": group("status"), "by_category": group("category"),
                "by_priority": group("priority"), "by_sentiment": group("sentiment")}
